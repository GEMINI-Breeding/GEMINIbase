"""
RUN_STITCH worker — AgRowStitch-backed ground-level image stitching.

The old FastAPI backend invoked AgRowStitch through a PyInstaller
subprocess channel so the Flask server and the stitching code could
live in the same Tauri sidecar binary. That scaffolding is gone: this
worker calls ``AgRowStitch.run(config_path, cpu_count)`` directly, in
process, and reports progress via the standard BaseWorker protocol.

Inputs arrive as a list of MinIO object paths pointing at the images
to stitch (the caller resolves plot markings into image lists). The
worker downloads them into a temp directory, renders an AgRowStitch
YAML config on the fly, invokes ``AgRowStitch.run``, and uploads the
resulting mosaic PNG(s) back to MinIO.

AgRowStitch itself (github.com/GEMINI-Breeding/AgRowStitch) is not on
PyPI, so the worker image adds it as a nested submodule at
``gemini/workers/stitch/vendor/AgRowStitch/`` and pip-installs its
dependencies (cv2, torch, lightglue, yaml, scipy, numpy, pandas). The
Dockerfile adds the submodule to ``sys.path`` so ``import AgRowStitch``
just works at runtime.
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Set

import yaml

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")


def _get_minio_client():
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _import_agrowstitch():
    """Import AgRowStitch.run, raising a clear error if the vendor dir is missing."""
    try:
        from AgRowStitch import run as agrowstitch_run  # type: ignore
        return agrowstitch_run
    except ImportError as e:
        raise RuntimeError(
            "AgRowStitch is not importable inside the worker. The worker image "
            "must include gemini/workers/stitch/vendor/AgRowStitch/ (submodule) "
            "and its dependencies (lightglue, torch, torchvision, scipy, opencv). "
            "See gemini/workers/stitch/README.md for the one-time submodule setup."
        ) from e


class StitchWorker(BaseWorker):
    """Worker for AgRowStitch-based ground-level stitching."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.RUN_STITCH}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type != JobType.RUN_STITCH.value:
            raise ValueError(f"Unsupported job type: {job_type}")
        return self._run_stitch_job(job_id, parameters)

    def _run_stitch_job(self, job_id: str, parameters: dict) -> dict:
        """Stitch a sequence of images into a mosaic.

        Parameters:
            image_paths: List[str] — MinIO object paths, in stitch order
            output_mosaic_path: str — MinIO object path to upload the mosaic
            config: dict — AgRowStitch YAML knobs. Common keys:
                stitching_direction ("LEFT"|"RIGHT"|"UP"|"DOWN")
                device ("cpu"|"cuda"|"mps"|"multiprocessing")
                mask: [left, right, top, bottom] (px to crop from each border)
                final_resolution: float (0..1 scale factor)
                batch_size, min_inliers, max_reprojection_error, forward_limit, num_cpu
            cpu_count: int, default 1 (AgRowStitch treats 0 as "auto")
        """
        image_paths: List[str] = list(parameters["image_paths"])
        output_mosaic_path: str = parameters["output_mosaic_path"]
        user_config: dict = dict(parameters.get("config") or {})
        # AgRowStitch treats cpu_count=0 as "auto" — preserve that explicit
        # sentinel; only supply a default when the caller omits the key.
        raw_cpu = parameters.get("cpu_count")
        if raw_cpu is None:
            cpu_count = max(1, (multiprocessing.cpu_count() or 1) - 1)
        else:
            cpu_count = int(raw_cpu)

        if len(image_paths) < 2:
            raise ValueError(
                "RUN_STITCH requires at least 2 images in image_paths."
            )

        agrowstitch_run = _import_agrowstitch()

        client = _get_minio_client()
        with tempfile.TemporaryDirectory(prefix="gemi_stitch_") as tmpdir:
            images_dir = Path(tmpdir) / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            self.report_progress(
                job_id,
                5,
                {"stage": "downloading", "total": len(image_paths)},
            )
            for i, remote in enumerate(image_paths):
                local_name = f"{i:06d}_{Path(remote).name}"
                client.fget_object(
                    STORAGE_BUCKET, remote, str(images_dir / local_name)
                )
                if (i + 1) % 25 == 0 or (i + 1) == len(image_paths):
                    self.report_progress(
                        job_id,
                        5 + int(30 * (i + 1) / len(image_paths)),
                        {
                            "stage": "downloading",
                            "downloaded": i + 1,
                            "total": len(image_paths),
                        },
                    )
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

            # Render AgRowStitch config on the fly. Defaults mirror the
            # sensible settings from the old ground.py runtime.
            config = {
                "image_directory": str(images_dir),
                "stitching_direction": user_config.get(
                    "stitching_direction", "RIGHT"
                ),
                "device": user_config.get("device", "cpu"),
                "mask": user_config.get("mask", [0, 0, 0, 0]),
                "final_resolution": user_config.get("final_resolution", 1.0),
                "batch_size": user_config.get("batch_size", 20),
                "min_inliers": user_config.get("min_inliers", 10),
                "max_reprojection_error": user_config.get(
                    "max_reprojection_error", 5.0
                ),
                "forward_limit": user_config.get("forward_limit", 10),
                "num_cpu": user_config.get("num_cpu", cpu_count),
            }
            # Pass any extra knobs the caller supplies straight through.
            for k, v in user_config.items():
                config.setdefault(k, v)

            config_path = Path(tmpdir) / "agrowstitch_config.yaml"
            with open(config_path, "w") as f:
                yaml.safe_dump(config, f)

            self.report_progress(
                job_id, 40, {"stage": "stitching", "config": config}
            )

            # AgRowStitch adds its vendored dir to sys.path at import time;
            # run() reads the config path + writes mosaic files next to
            # `image_directory`. It's a blocking call (minutes to hours).
            agrowstitch_run(str(config_path), cpu_count)

            # Find the produced mosaic. AgRowStitch writes
            # ``full_res_mosaic_temp_plot_*.png`` (optionally with a ``.tif``
            # companion) either alongside ``images_dir`` or inside it; match
            # only those prefixes so we never accidentally upload an input
            # image as the "primary mosaic."
            mosaic_candidates = sorted(
                set(
                    list(images_dir.parent.glob("full_res_mosaic_*.png"))
                    + list(images_dir.parent.glob("full_res_mosaic_*.tif"))
                    + list(images_dir.glob("full_res_mosaic_*.png"))
                    + list(images_dir.glob("full_res_mosaic_*.tif"))
                )
            )
            mosaic_candidates = [p for p in mosaic_candidates if p.exists()]
            if not mosaic_candidates:
                raise RuntimeError(
                    "AgRowStitch did not produce a mosaic file. Check the "
                    "config parameters (direction, mask, batch_size) and "
                    "the image inputs."
                )

            # Upload the first (primary) mosaic; include sidecars as extras.
            primary = mosaic_candidates[0]
            self.report_progress(job_id, 95, {"stage": "uploading"})
            client.fput_object(
                STORAGE_BUCKET,
                output_mosaic_path,
                str(primary),
                content_type="image/png",
            )

            return {
                "output_mosaic_path": output_mosaic_path,
                "image_count": len(image_paths),
                "agrowstitch_config": config,
                "primary_mosaic_size_bytes": primary.stat().st_size,
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    StitchWorker().run()
