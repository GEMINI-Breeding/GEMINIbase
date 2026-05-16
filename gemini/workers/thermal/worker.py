"""
Thermal extraction worker.

Handles THERMAL_EXTRACT jobs: for each thermal image in a dataset
prefix, write three artifacts to MinIO so the rest of the platform can
treat thermal data the same way it treats RGB:

  - `Raw/.../{sensor}/Images/{basename}.jpg`
        8-bit RGB preview (iron palette by default) — used as the
        sensor's thumbnail and as the input to RUN_ODM.

  - `Raw/.../{sensor}/RawThermal/{basename}.tif`
        16-bit single-channel TIFF carrying the raw signal counts.
        For Boson sources this is just the original file written
        through; for FLIR One Pro JPEGs it's the embedded raw PNG
        decoded and re-saved as TIFF for a single consistent format
        downstream.

  - `Raw/.../{sensor}/RawThermal/{basename}.json`
        Per-file sidecar with calibration constants, palette window
        (vmin/vmax in counts or °C), scene min/max, and the source
        mode. The browser viewer reads this without re-running
        exiftool.

A per-dataset summary lands at
`Raw/.../{sensor}/RawThermal/thermal_dataset.json` so Phase D's
RUN_ODM preflight can read `has_gps` without listing per-file
sidecars.
"""
from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Set

import numpy as np
from PIL import Image

from gemini.workers.base import BaseWorker
from gemini.workers.thermal.calibration import (
    apply_palette,
    percentile_window,
    resolve_linear_mode,
    planck_signal_to_celsius,
)
from gemini.workers.thermal.flir_jpeg import extract_flir_jpeg
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

# Conservative thread pool — thermal extraction is exiftool-bound
# (one subprocess per file for FLIR JPEGs), so spinning more threads
# than CPU cores just queues more subprocesses without speedup.
WORK_POOL_SIZE = int(os.environ.get("GEMINI_THERMAL_POOL_SIZE", "4"))

# Image extensions the worker will pick up. `.fff`/`.seq` are explicitly
# excluded from v1 — see plan "Phase B per-source logic".
INPUT_EXTS = (".jpg", ".jpeg", ".tif", ".tiff")

# The frontend tags this category on the dataset. Boson and One Pro both
# end up here; the calibration mode in job parameters disambiguates.
DATASET_JSON_NAME = "thermal_dataset.json"


def _get_minio_client():
    """Same connection-pool tuning as the amiga worker — see worker.py:44."""
    import urllib3
    from minio import Minio

    pool_size = max(WORK_POOL_SIZE + 4, 12)
    http_client = urllib3.PoolManager(
        num_pools=10,
        maxsize=pool_size,
        block=False,
        retries=urllib3.Retry(
            total=3,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504],
        ),
    )
    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
        http_client=http_client,
    )


def _build_dataset_prefix(parameters: dict) -> str:
    """Reconstruct the dataset prefix from job params.

    Two shapes are supported:

    1. Explicit `dataset_prefix` (preferred): when the caller already
       knows where the files landed in MinIO. The wizard uses this
       because the supplemental-data upload layout is
       `Raw/{date}/{experiment}/{filename}`, not the richer ODM-style
       prefix.

    2. Structured fields `{year, experiment, location, population,
       date, platform, sensor[, dataset_short_id]}` (legacy /
       ODM-style): mirrors the prefix builder in odm/worker.py so
       RUN_ODM and the thermal worker agree on the same prefix when
       uploads come through the richer drone-data path. The optional
       `dataset_short_id` is inserted between `{sensor}` and the
       trailing slash so two uploads at the same scope land in
       distinct subdirectories (sibling `Images/` + `RawThermal/`
       per dataset).

    Always returns a value ending in `/` so MinIO list-by-prefix
    behaves correctly.
    """
    explicit = parameters.get("dataset_prefix")
    if isinstance(explicit, str) and explicit:
        return explicit if explicit.endswith("/") else explicit + "/"
    parts = [
        "Raw",
        parameters.get("year", ""),
        parameters.get("experiment", ""),
        parameters.get("location", ""),
        parameters.get("population", ""),
        parameters.get("date", ""),
        parameters.get("platform", ""),
        parameters.get("sensor", ""),
        parameters.get("dataset_short_id", ""),
    ]
    return "/".join(p for p in parts if p) + "/"


class ThermalWorker(BaseWorker):
    """Worker for THERMAL_EXTRACT jobs."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.THERMAL_EXTRACT}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.THERMAL_EXTRACT.value:
            return self._thermal_extract_job(job_id, parameters)
        raise ValueError(f"Unsupported job type: {job_type}")

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def _thermal_extract_job(self, job_id: str, parameters: dict) -> dict:
        calibration = parameters.get("thermal_calibration") or {}
        mode = calibration.get("mode")
        if not mode:
            raise ValueError(
                "THERMAL_EXTRACT requires parameters.thermal_calibration.mode"
            )
        experiment_id = parameters.get("experiment_id") or parameters.get("experimentId")
        dataset_id = parameters.get("dataset_id") or parameters.get("datasetId")

        dataset_prefix = _build_dataset_prefix(parameters)
        images_prefix = f"{dataset_prefix}Images/"
        raw_thermal_prefix = f"{dataset_prefix}RawThermal/"

        client = _get_minio_client()
        # The original uploads land directly under the dataset prefix (no
        # `Images/` subdir until *we* write previews there). List the
        # dataset prefix and pick thermal-extensioned objects whose key
        # doesn't already live under our output subprefixes — that lets
        # the job be safely re-run without re-processing its own
        # outputs.
        self.report_progress(job_id, 2, {"stage": "listing"})
        inputs = _list_thermal_inputs(client, dataset_prefix)
        if not inputs:
            return {
                "status": "skipped",
                "message": f"No thermal inputs under {dataset_prefix}",
                "dataset_prefix": dataset_prefix,
            }

        self.report_progress(job_id, 5, {
            "stage": "processing",
            "total_files": len(inputs),
        })

        gps_count = 0
        registered_objects: list[str] = []
        scene_min_c: float | None = None
        scene_max_c: float | None = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            def _process_one(object_name: str) -> dict:
                """Process a single input file. Returns a per-file summary
                dict (or raises). Pure-IO/CPU; no logging beyond debug."""
                if self.is_cancelled(job_id):
                    return {"cancelled": True}
                local_in = tmp / Path(object_name).name
                client.fget_object(STORAGE_BUCKET, object_name, str(local_in))
                ext = local_in.suffix.lower()
                basename = local_in.stem
                # Outputs land at:
                #   images_prefix    + basename + ".jpg"
                #   raw_thermal_prefix + basename + ".tif"
                #   raw_thermal_prefix + basename + ".json"
                rgb_object = f"{images_prefix}{basename}.jpg"
                raw_object = f"{raw_thermal_prefix}{basename}.tif"
                json_object = f"{raw_thermal_prefix}{basename}.json"

                if ext in (".jpg", ".jpeg"):
                    if mode != "flir_one_pro":
                        raise RuntimeError(
                            f"{object_name}: JPEG inputs require "
                            f"thermal_calibration.mode=flir_one_pro "
                            f"(got {mode!r})"
                        )
                    summary = _process_flir_jpeg(
                        client=client,
                        local_in=local_in,
                        original_object=object_name,
                        rgb_object=rgb_object,
                        raw_object=raw_object,
                        json_object=json_object,
                    )
                elif ext in (".tif", ".tiff"):
                    summary = _process_boson_tiff(
                        client=client,
                        local_in=local_in,
                        mode=mode,
                        scale=calibration.get("scale"),
                        offset=calibration.get("offset"),
                        original_object=object_name,
                        rgb_object=rgb_object,
                        raw_object=raw_object,
                        json_object=json_object,
                    )
                else:
                    raise RuntimeError(
                        f"{object_name}: unsupported extension {ext!r}"
                    )
                return summary

            # Bounded parallelism. exiftool subprocesses dominate runtime
            # for FLIR JPEGs; for Boson TIFFs the cost is the PIL decode
            # + palette which is also CPU-bound. WORK_POOL_SIZE=4 keeps
            # us responsive without thrashing.
            done = 0
            with ThreadPoolExecutor(max_workers=WORK_POOL_SIZE) as pool:
                futures = {
                    pool.submit(_process_one, obj): obj for obj in inputs
                }
                last_emit = 0.0
                for fut in as_completed(futures):
                    summary = fut.result()
                    if summary.get("cancelled"):
                        for pending in futures:
                            pending.cancel()
                        return {"status": "cancelled"}
                    done += 1
                    if summary.get("has_gps"):
                        gps_count += 1
                    if summary.get("rgb_object"):
                        registered_objects.append(summary["rgb_object"])
                    if summary.get("raw_object"):
                        registered_objects.append(summary["raw_object"])
                    if summary.get("json_object"):
                        registered_objects.append(summary["json_object"])
                    sm = summary.get("scene_min_c")
                    sx = summary.get("scene_max_c")
                    if sm is not None:
                        scene_min_c = sm if scene_min_c is None else min(scene_min_c, sm)
                    if sx is not None:
                        scene_max_c = sx if scene_max_c is None else max(scene_max_c, sx)
                    now = time.monotonic()
                    if now - last_emit >= 0.5 or done == len(inputs):
                        last_emit = now
                        self.report_progress(job_id, 5 + 85 * done / len(inputs), {
                            "stage": "processing",
                            "done": done,
                            "total_files": len(inputs),
                        })

            # Per-dataset summary so the ODM preflight (Phase D) can read
            # has_gps without listing every per-file sidecar.
            dataset_summary = {
                "mode": mode,
                "scale": calibration.get("scale"),
                "offset": calibration.get("offset"),
                "has_gps": gps_count > 0,
                "gps_count": gps_count,
                "total_files": len(inputs),
                "scene_min_c": scene_min_c,
                "scene_max_c": scene_max_c,
                "radiometric": mode != "boson_agc_nonradiometric",
            }
            summary_object = f"{raw_thermal_prefix}{DATASET_JSON_NAME}"
            _put_json(client, summary_object, dataset_summary)
            registered_objects.append(summary_object)

        # Register every new object as an experiment_files row so the
        # per-dataset delete cascade sweeps them. Mirrors amiga
        # worker.py:467-478.
        if experiment_id and registered_objects:
            self.report_progress(job_id, 95, {
                "stage": "registering",
                "count": len(registered_objects),
            })
            self._register_extracted_files_batch(
                experiment_id=experiment_id,
                dataset_id=dataset_id,
                bucket=STORAGE_BUCKET,
                object_names=registered_objects,
            )

        return {
            "status": "completed",
            "dataset_prefix": dataset_prefix,
            "outputs_written": len(registered_objects),
            "has_gps": gps_count > 0,
        }

    # ------------------------------------------------------------------
    # Helpers shared with the amiga worker (copied verbatim rather than
    # imported because the amiga module also pulls in farm_ng deps that
    # we don't want in this worker's image).
    # ------------------------------------------------------------------

    def _register_extracted_files_batch(
        self,
        experiment_id: str,
        dataset_id: str | None,
        bucket: str,
        object_names: list[str],
    ) -> None:
        if not object_names:
            return
        try:
            self._http.post(
                "/api/files/register_batch",
                json={
                    "experiment_id": experiment_id,
                    "dataset_id": dataset_id,
                    "files": [
                        {"bucket": bucket, "object_name": n}
                        for n in object_names
                    ],
                },
            )
        except Exception as exc:
            logger.warning(
                "register_batch (%d files) for experiment %s failed: %s",
                len(object_names), experiment_id, exc,
            )


# ---------------------------------------------------------------------------
# Module-level helpers (no `self`, easy to unit test).
# ---------------------------------------------------------------------------


def _list_thermal_inputs(client, dataset_prefix: str) -> list[str]:
    """List thermal-extensioned inputs under the dataset prefix.

    Two layouts are accepted because both reach this worker:

    1. Image Data form: files land at `{dataset_prefix}Images/{name}`.
       The form's `directory: [...,"Images"]` config appends the
       segment automatically (see frontend/src/config/dataTypes.ts).
       The worker writes its RGB previews back to that same `Images/`
       directory (idempotent — re-running overwrites) and sidecars
       to a sibling `RawThermal/`.

    2. Direct submissions: files land at `{dataset_prefix}{name}`
       (used by the original Phase B verification + the curl-driven
       contract tests). The worker still writes outputs to
       `Images/` + `RawThermal/` under `dataset_prefix`.

    `_process_*` writers never *overwrite* a sidecar JSON, so it's
    safe to include the `Images/` directory as a candidate input
    source — the worker only treats `.jpg`/`.tif` inputs there, and
    its own JPEG previews share that path. The dedupe-via-sidecar
    contract (the previews and sidecars have matching basenames)
    means a re-run is idempotent.
    """
    out: list[str] = []
    raw_thermal_prefix = f"{dataset_prefix}RawThermal/"
    for obj in client.list_objects(
        STORAGE_BUCKET, prefix=dataset_prefix, recursive=True
    ):
        name = obj.object_name
        if not name or name.endswith("/"):
            continue
        # Skip sidecars produced by prior runs.
        if name.startswith(raw_thermal_prefix):
            continue
        if name.lower().endswith(INPUT_EXTS):
            out.append(name)
    return sorted(out)


def _put_json(client, object_name: str, payload: dict) -> None:
    """Serialize `payload` and PUT it as a small JSON object in MinIO."""
    data = json.dumps(payload, indent=2, default=_json_default).encode("utf-8")
    client.put_object(
        STORAGE_BUCKET,
        object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type="application/json",
    )


def _json_default(value):
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def _process_flir_jpeg(
    *,
    client,
    local_in: Path,
    original_object: str,
    rgb_object: str,
    raw_object: str,
    json_object: str,
) -> dict:
    """FLIR One Pro JPEG → write through as preview, extract raw + Planck."""
    payload = extract_flir_jpeg(str(local_in))
    raw = payload.raw_counts
    temp_c = planck_signal_to_celsius(
        raw, payload.planck, emissivity=payload.emissivity
    )
    vmin, vmax = percentile_window(temp_c)
    # FLIR's own iron-palette JPEG is already a nicer preview than
    # anything we'd render server-side from the raw — keep the original
    # bytes for the Images/ preview.
    client.fput_object(STORAGE_BUCKET, rgb_object, str(local_in), content_type="image/jpeg")
    # Re-encode the raw uint16 as a TIFF so RawThermal/ has a consistent
    # file format regardless of source camera. **Uncompressed** so the
    # browser-side viewer can parse the strip without shipping an LZW
    # decoder — see frontend/src/features/files/lib/thermal.ts. Cost is
    # ~600 KB per FLIR-One-Pro frame instead of ~330 KB, acceptable for
    # an internal inspection tier.
    tif_path = local_in.with_suffix(".raw.tif")
    Image.fromarray(raw, mode="I;16").save(str(tif_path), format="TIFF", compression="raw")
    client.fput_object(STORAGE_BUCKET, raw_object, str(tif_path), content_type="image/tiff")

    sidecar = {
        "source": "flir_one_pro",
        "original": original_object,
        "shape": list(raw.shape),
        "planck": {
            "R1": payload.planck.r1,
            "B": payload.planck.b,
            "F": payload.planck.f,
            "O": payload.planck.o,
            "R2": payload.planck.r2,
        },
        "emissivity": payload.emissivity,
        "scene_min_c": _nan_safe_float(np.nanmin(temp_c)),
        "scene_max_c": _nan_safe_float(np.nanmax(temp_c)),
        "preview_vmin_c": vmin,
        "preview_vmax_c": vmax,
        "radiometric": True,
        "has_gps": payload.has_gps,
    }
    _put_json(client, json_object, sidecar)
    return {
        "rgb_object": rgb_object,
        "raw_object": raw_object,
        "json_object": json_object,
        "has_gps": payload.has_gps,
        "scene_min_c": sidecar["scene_min_c"],
        "scene_max_c": sidecar["scene_max_c"],
    }


def _process_boson_tiff(
    *,
    client,
    local_in: Path,
    mode: str,
    scale: float | None,
    offset: float | None,
    original_object: str,
    rgb_object: str,
    raw_object: str,
    json_object: str,
) -> dict:
    """Boson-class 16-bit TIFF → re-encode uncompressed, render palette preview."""
    arr = np.asarray(Image.open(str(local_in)), dtype=np.uint16)
    # Re-encode as uncompressed TIFF so the browser viewer can parse
    # strips without an LZW decoder (see _process_flir_jpeg for the
    # same rationale). The original bytes may use LZW + Horizontal
    # Differencing predictor; both add complexity we don't want in the
    # frontend bundle. Cost is ~2x storage for this one file.
    raw_local = local_in.with_suffix(".raw.tif")
    Image.fromarray(arr, mode="I;16").save(
        str(raw_local), format="TIFF", compression="raw"
    )
    client.fput_object(STORAGE_BUCKET, raw_object, str(raw_local), content_type="image/tiff")

    sidecar: dict[str, object] = {
        "source": mode,
        "original": original_object,
        "shape": list(arr.shape),
        "radiometric": mode != "boson_agc_nonradiometric",
        # Boson TIFFs carry no per-image GPS. Phase D's preflight uses
        # this to short-circuit RUN_ODM rather than waiting for the
        # ODM worker to bail on "Not enough features".
        "has_gps": False,
    }

    if mode == "boson_agc_nonradiometric":
        vmin, vmax = percentile_window(arr.astype(np.float32))
        rgb = apply_palette(arr.astype(np.float32), vmin=vmin, vmax=vmax)
        sidecar.update({
            "preview_vmin_counts": vmin,
            "preview_vmax_counts": vmax,
            "scene_min_c": None,
            "scene_max_c": None,
        })
    else:
        lin = resolve_linear_mode(mode, scale=scale, offset=offset)
        temp_c = lin.to_celsius(arr)
        vmin, vmax = percentile_window(temp_c)
        rgb = apply_palette(temp_c, vmin=vmin, vmax=vmax)
        sidecar.update({
            "scale": lin.scale,
            "offset": lin.offset,
            "scene_min_c": _nan_safe_float(np.nanmin(temp_c)),
            "scene_max_c": _nan_safe_float(np.nanmax(temp_c)),
            "preview_vmin_c": vmin,
            "preview_vmax_c": vmax,
        })

    # JPEG preview alongside the original.
    preview_path = local_in.with_suffix(".preview.jpg")
    Image.fromarray(rgb).save(str(preview_path), format="JPEG", quality=88)
    client.fput_object(STORAGE_BUCKET, rgb_object, str(preview_path), content_type="image/jpeg")

    _put_json(client, json_object, sidecar)
    return {
        "rgb_object": rgb_object,
        "raw_object": raw_object,
        "json_object": json_object,
        "has_gps": False,
        "scene_min_c": sidecar.get("scene_min_c"),
        "scene_max_c": sidecar.get("scene_max_c"),
    }


def _nan_safe_float(value) -> float | None:
    f = float(value)
    if not np.isfinite(f):
        return None
    return f


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = ThermalWorker()
    worker.run()
