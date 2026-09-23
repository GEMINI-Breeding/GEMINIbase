"""
RUN_STITCH worker — per-plot AgRowStitch stitching + georeferencing of a
ground (Amiga) track. Ported from GEMINI-App main's ground.run_stitching /
run_georeferencing.

Parameters
----------
images_prefix     MinIO prefix holding the track's top-camera frames
                  (…/RGB/Images/top/)
msgs_synced_path  MinIO path of the track's msgs_synced.csv
plots             [{plot_id, start_image, end_image, direction}] — the
                  Plot Marking step's output; direction is up/down/left/right
output_prefix     MinIO prefix for this stitch version (…/AgRowStitch_v{N}/)
settings          pipeline knobs: forward_limit, max_reprojection_error,
                  batch_size, min_inliers, crop_rules (or legacy mask_*)
custom_options    raw AgRowStitch options (dict, or YAML text), applied last
device            "cpu" | "gpu" | "multiprocessing"; num_cpu (0 = auto)

Writes under output_prefix
--------------------------
full_res_mosaic_temp_plot_{id}.png   each stitched plot (main's names)
georeferenced_plot_{id}_utm.tif      each plot laid along its GPS track
combined_mosaic_utm.tif / combined_mosaic.tif (WGS84)
plot_borders.csv                     the markings used, with GPS
stitch_manifest.json                 settings, per-plot outcome, footprints

A plot that fails is recorded and skipped, as in main; the job fails if
no plot stitches, so an empty result never reports success.

AgRowStitch runs in a child process per plot: cancellation can kill it,
and a native crash (OpenCV has segfaulted here before) fails one plot
instead of taking the worker down.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import List, Set

import pandas as pd
import yaml

from gemini.workers.base import BaseWorker
from gemini.workers.stitch import plan
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

AGROWSTITCH_DIR = Path(os.environ.get("AGROWSTITCH_DIR", "/opt/AgRowStitch"))

INT_KEYS = {"forward_limit", "batch_size", "min_inliers", "crop_size", "points_per_image"}
FLOAT_KEYS = {"max_reprojection_error", "seam_resolution", "keypoint_prop", "low_resolution",
              "straightening_threshold"}


def _get_minio_client():
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _agrowstitch_defaults() -> dict:
    cfg = AGROWSTITCH_DIR / "config.yaml"
    if not cfg.exists():
        raise RuntimeError(
            f"AgRowStitch is not installed in this worker image ({cfg} missing). "
            "Rebuild geminibase-worker-stitch."
        )
    with open(cfg) as f:
        return yaml.safe_load(f) or {}


def _coerce(config: dict) -> dict:
    """AgRowStitch type-checks with isinstance; JSON can turn 4 into 4.0."""
    out = dict(config)
    for k in INT_KEYS & out.keys():
        out[k] = int(out[k])
    for k in FLOAT_KEYS & out.keys():
        out[k] = float(out[k])
    if "mask" in out:
        out["mask"] = [int(v) for v in out["mask"]]
    return out


def _resolve_device(device: str) -> str:
    if device == "multiprocessing":
        return "multiprocessing"
    if device == "gpu":
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
    return "cpu"


class StitchCancelled(Exception):
    pass


class StitchWorker(BaseWorker):
    """Worker for AgRowStitch-based ground-level stitching."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.RUN_STITCH}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type != JobType.RUN_STITCH.value:
            raise ValueError(f"Unsupported job type: {job_type}")
        try:
            return self._run_stitch_job(job_id, parameters)
        except StitchCancelled:
            return {"status": "cancelled"}

    # ── helpers ────────────────────────────────────────────────────────

    def _stage(self, job_id: str, pct: float, stage: str, **extra) -> None:
        logger.info("[%s] %s", job_id[:8], stage)
        self.report_progress(job_id, pct, {"stage": stage, **extra})

    def _run_agrowstitch(
        self, job_id: str, config_path: Path, cpu_count: int, label: str
    ) -> None:
        """AgRowStitch.run in a child process, polling for cancellation."""
        cmd = [
            sys.executable, "-c",
            "import sys; from AgRowStitch import run; "
            "run(sys.argv[1], int(sys.argv[2]))",
            str(config_path), str(cpu_count),
        ]
        tail: List[str] = []
        # Niced: AgRowStitch takes every core it can, and at normal priority
        # it starved the REST API (the worker's own status calls timed out).
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True, preexec_fn=lambda: os.nice(10),
        )

        def pump() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    logger.info("[AgRowStitch %s] %s", label, line)
                    tail.append(line)
                    del tail[:-15]

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        last_check = time.monotonic()
        while proc.poll() is None:
            if time.monotonic() - last_check > 3:
                last_check = time.monotonic()
                if self.is_cancelled(job_id):
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise StitchCancelled()
            time.sleep(0.3)
        reader.join(timeout=5)
        if proc.returncode != 0:
            code = proc.returncode
            if code < 0:
                try:
                    what = f"crashed with {signal.Signals(-code).name}"
                except ValueError:
                    what = f"crashed with signal {-code}"
            else:
                what = f"exited with code {code}"
            detail = "\n".join(tail[-8:]) or "(no output)"
            raise RuntimeError(f"AgRowStitch {what}:\n{detail}")

    # ── job ────────────────────────────────────────────────────────────

    def _run_stitch_job(self, job_id: str, p: dict) -> dict:
        from gemini.workers.amiga.headings import add_direction_columns
        from gemini.workers.stitch import georef

        images_prefix = p["images_prefix"].rstrip("/") + "/"
        output_prefix = p["output_prefix"].rstrip("/") + "/"
        plots: List[dict] = list(p.get("plots") or [])
        settings: dict = dict(p.get("settings") or {})
        custom = p.get("custom_options") or {}
        if isinstance(custom, str):  # the pipeline setting is YAML text
            try:
                custom = yaml.safe_load(custom) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"Custom AgRowStitch options aren't valid YAML: {exc}")
        if not isinstance(custom, dict):
            raise ValueError("Custom AgRowStitch options must be key: value pairs")
        if not plots:
            raise ValueError("No plots to stitch. Mark plots in the Plot Marking step first.")

        device = _resolve_device(str(p.get("device") or "cpu"))
        num_cpu = int(p.get("num_cpu") or 0)
        cpu_count = num_cpu if num_cpu > 0 else max(1, (multiprocessing.cpu_count() or 1) - 1)

        client = _get_minio_client()
        self._stage(job_id, 2, "Reading GPS track")
        resp = client.get_object(STORAGE_BUCKET, p["msgs_synced_path"])
        try:
            msgs = pd.read_csv(io.BytesIO(resp.read()), on_bad_lines="skip")
        finally:
            resp.close()
            resp.release_conn()
        msgs.columns = msgs.columns.str.strip()
        if "direction" not in msgs.columns:
            add_direction_columns(msgs)
        names = plan.basenames(msgs)

        base_config, dropped = plan.build_base_config(_agrowstitch_defaults(), settings, custom)
        if dropped:
            logger.warning("Ignoring options AgRowStitch doesn't accept: %s", dropped)
        base_config["device"] = device

        succeeded: List[str] = []
        failed: dict = {}
        per_plot: dict = {}
        utm_tifs: List[Path] = []
        border_rows: List[dict] = []
        n = len(plots)

        with tempfile.TemporaryDirectory(prefix="gemi_stitch_") as tmp:
            tmpdir = Path(tmp)
            for i, plot in enumerate(plots):
                pid = str(plot.get("plot_id", i + 1))
                start, end = plot.get("start_image") or "", plot.get("end_image") or ""
                ui_dir = str(plot.get("direction") or "down")
                base_pct = 5 + 85 * i / n
                self._stage(job_id, base_pct, f"Stitching plot {pid} ({i + 1}/{n})")
                try:
                    rows = plan.plot_rows(msgs, names, start, end)
                    frames = list(dict.fromkeys(b for b in names.loc[rows.index] if b))
                    heading = plan.dominant_heading(rows)
                    border_rows.append({
                        "plot_id": pid, "start_image": start, "end_image": end,
                        "start_lat": rows["lat"].iloc[0] if "lat" in rows else "",
                        "start_lon": rows["lon"].iloc[0] if "lon" in rows else "",
                        "end_lat": rows["lat"].iloc[-1] if "lat" in rows else "",
                        "end_lon": rows["lon"].iloc[-1] if "lon" in rows else "",
                        "direction": ui_dir, "heading": heading, "frames": len(frames),
                    })
                    if len(frames) < 2:
                        raise ValueError(f"only {len(frames)} frame(s) between start and end")

                    outer = tmpdir / f"plot_{pid}"
                    img_dir = outer / "images"
                    img_dir.mkdir(parents=True)
                    for name in frames:
                        client.fget_object(STORAGE_BUCKET, images_prefix + name, str(img_dir / name))

                    config = dict(base_config)
                    config["image_directory"] = str(img_dir)
                    config["stitching_direction"] = plan.DIRECTION_MAP.get(ui_dir.lower(), "DOWN")
                    mask = plan.choose_crop_mask(settings.get("crop_rules"), ui_dir, heading)
                    if mask is not None:
                        config["mask"] = mask
                    config_path = outer / "config.yaml"
                    with open(config_path, "w") as f:
                        yaml.safe_dump(_coerce(config), f)

                    self._run_agrowstitch(job_id, config_path, cpu_count, pid)

                    found = sorted((outer / "final_mosaics").glob("full_res_mosaic*.png"))
                    if not found:
                        raise RuntimeError("AgRowStitch finished but wrote no mosaic")
                    png_name = f"full_res_mosaic_temp_plot_{pid}.png"
                    client.fput_object(STORAGE_BUCKET, output_prefix + png_name, str(found[0]),
                                       content_type="image/png")
                    info = {"frames": len(frames), "mask": config.get("mask"),
                            "stitching_direction": config["stitching_direction"],
                            "mosaic": output_prefix + png_name}

                    tif = outer / f"georeferenced_plot_{pid}_utm.tif"
                    if georef.georeference_plot(found[0], rows, tif):
                        client.fput_object(STORAGE_BUCKET, output_prefix + tif.name, str(tif),
                                           content_type="image/tiff")
                        utm_tifs.append(tif)
                        info["footprint"] = georef.footprint_wgs84(tif)
                        info["georeferenced"] = output_prefix + tif.name
                    else:
                        info["georeferenced"] = None
                    per_plot[pid] = info
                    succeeded.append(pid)
                except StitchCancelled:
                    raise
                except Exception as exc:
                    msg = str(exc)[:600]
                    logger.warning("Plot %s failed: %s", pid, msg)
                    failed[pid] = msg
                if self.is_cancelled(job_id):
                    raise StitchCancelled()

            if not succeeded:
                first = next(iter(failed.items()))
                raise RuntimeError(
                    f"No plot could be stitched ({len(failed)} failed). "
                    f"Plot {first[0]}: {first[1]}"
                )

            combined = None
            if utm_tifs:
                self._stage(job_id, 92, "Combining plot mosaics")
                out_utm = tmpdir / "combined_mosaic_utm.tif"
                out_wgs = tmpdir / "combined_mosaic.tif"
                if georef.combine_utm_tiffs(utm_tifs, out_utm, out_wgs):
                    for f in (out_utm, out_wgs):
                        client.fput_object(STORAGE_BUCKET, output_prefix + f.name, str(f),
                                           content_type="image/tiff")
                    combined = output_prefix + out_wgs.name

            self._stage(job_id, 97, "Saving results")
            out = io.StringIO()
            fields = ["plot_id", "start_image", "end_image", "start_lat", "start_lon",
                      "end_lat", "end_lon", "direction", "heading", "frames"]
            w = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(border_rows)
            data = out.getvalue().encode()
            client.put_object(STORAGE_BUCKET, output_prefix + "plot_borders.csv",
                              io.BytesIO(data), len(data), content_type="text/csv")

            stored_config = {k: v for k, v in base_config.items() if k != "image_directory"}
            manifest = {
                "plots": per_plot,
                "succeeded_plots": succeeded,
                "failed_plots": failed,
                "plot_count": n,
                "combined_mosaic": combined,
                "config": stored_config,
                "ignored_options": dropped,
                "source": {"images_prefix": images_prefix,
                           "msgs_synced_path": p["msgs_synced_path"]},
            }
            body = json.dumps(manifest, indent=2, default=str).encode()
            client.put_object(STORAGE_BUCKET, output_prefix + "stitch_manifest.json",
                              io.BytesIO(body), len(body), content_type="application/json")

        summary = f"Stitched {len(succeeded)}/{n} plot(s)"
        if failed:
            summary += f"; failed: {', '.join(failed)}"
        return {
            "output_prefix": output_prefix,
            "succeeded_plots": succeeded,
            "failed_plots": failed,
            "combined_mosaic": combined,
            "summary": summary,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    StitchWorker().run()
