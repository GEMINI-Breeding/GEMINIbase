"""
ODM processing worker.

Handles orthomosaic generation via NodeODM:
- RUN_ODM: Download drone images from MinIO, submit to NodeODM,
  poll for progress, upload resulting orthophoto back to MinIO.

Requires: NodeODM sidecar service (opendronemap/nodeodm).
"""

import logging
import os
import tempfile
import time
from typing import Set

import requests

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType
from gemini.workers.odm.nodeodm_client import (
    NodeODMClient,
    NodeODMError,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_FAILED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)

logger = logging.getLogger(__name__)

# MinIO connection
STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

# NodeODM polling interval
POLL_INTERVAL = int(os.environ.get("GEMINI_ODM_POLL_INTERVAL", "5"))

# Max consecutive poll failures before failing the job (5s * 60 = 5 min)
MAX_POLL_FAILURES = int(os.environ.get("GEMINI_ODM_MAX_POLL_FAILURES", "60"))

# Image file extensions to include
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Default ODM options for "Default" quality.
# Matches the original Flask backend behavior:
# - No --fast-orthophoto (full quality reconstruction)
# - High resolution (0.25 cm/pixel) for datasets < 500 images
# - DSM generation enabled
DEFAULT_OPTIONS = [
    {"name": "orthophoto-resolution", "value": 0.25},
    {"name": "dem-resolution", "value": 0.25},
    {"name": "dsm", "value": True},
]


def _get_minio_client():
    """Create a MinIO client for file access."""
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _build_image_prefix(params: dict) -> str:
    """Build the MinIO prefix for raw images from job parameters."""
    parts = [
        params.get("year", ""),
        params.get("experiment", ""),
        params.get("location", ""),
        params.get("population", ""),
        params.get("date", ""),
        params.get("platform", ""),
        params.get("sensor", ""),
    ]
    return "/".join(p for p in parts if p) + "/Images/"


def _build_output_prefix(params: dict) -> str:
    """Build the MinIO prefix for processed output from job parameters."""
    parts = [
        "Processed",
        params.get("year", ""),
        params.get("experiment", ""),
        params.get("location", ""),
        params.get("population", ""),
        params.get("date", ""),
        params.get("platform", ""),
        params.get("sensor", ""),
    ]
    return "/".join(p for p in parts if p) + "/"


def _parse_custom_options(custom_options) -> list[dict]:
    """
    Parse custom ODM options from the frontend.

    Accepts either a string of CLI-style args (e.g. "--dem-resolution 0.25 --orthophoto-resolution 0.25")
    or a list of {"name": ..., "value": ...} dicts.
    """
    if isinstance(custom_options, list):
        if all(isinstance(o, dict) for o in custom_options):
            return custom_options
        return []

    if not isinstance(custom_options, str) or not custom_options.strip():
        return DEFAULT_OPTIONS

    options = []
    parts = custom_options.strip().split()
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            name = part.lstrip("-")
            # Check if next part is a value or another flag
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                value = parts[i + 1]
                # Try to parse as number or boolean
                if value.lower() in ("true", "yes"):
                    value = True
                elif value.lower() in ("false", "no"):
                    value = False
                else:
                    try:
                        value = float(value) if "." in value else int(value)
                    except ValueError:
                        pass
                options.append({"name": name, "value": value})
                i += 2
            else:
                # Boolean flag
                options.append({"name": name, "value": True})
                i += 1
        else:
            i += 1

    return options if options else DEFAULT_OPTIONS


class OdmWorker(BaseWorker):
    """Worker for orthomosaic generation via NodeODM."""

    def __init__(self, worker_id: str = None):
        super().__init__(worker_id)
        self._nodeodm = NodeODMClient()

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.RUN_ODM}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        return self._run_odm(job_id, parameters)

    def _run_odm(self, job_id: str, parameters: dict) -> dict:
        """
        Full ODM orthomosaic generation pipeline.

        1. Download images from MinIO
        2. Submit to NodeODM
        3. Poll for progress
        4. Download result
        5. Upload to MinIO
        6. Save log
        7. Cleanup
        """
        client = _get_minio_client()
        image_prefix = _build_image_prefix(parameters)
        output_prefix = _build_output_prefix(parameters)

        # Parse ODM options
        quality = parameters.get("reconstruction_quality", "Default")
        if quality == "Custom":
            options = _parse_custom_options(parameters.get("custom_options"))
        else:
            options = DEFAULT_OPTIONS

        with tempfile.TemporaryDirectory() as tmpdir:
            images_dir = os.path.join(tmpdir, "images")
            os.makedirs(images_dir)

            # Create initial log file so the frontend doesn't 404 while polling
            self._write_log_to_minio(
                ["Processing started..."], output_prefix, client
            )

            # Phase 1: Download images from MinIO (0-15%)
            self.report_progress(job_id, 2, {"stage": "downloading_images"})
            image_paths = self._download_images(
                client, image_prefix, images_dir, job_id
            )
            if not image_paths:
                raise RuntimeError(
                    f"No images found in MinIO at {STORAGE_BUCKET}/{image_prefix}"
                )
            logger.info(f"Downloaded {len(image_paths)} images for job {job_id}")

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Phase 2: Submit to NodeODM (15-20%)
            self.report_progress(job_id, 16, {
                "stage": "submitting_to_odm",
                "image_count": len(image_paths),
            })
            try:
                task_id = self._nodeodm.create_task(image_paths, options)
            except Exception as e:
                raise RuntimeError(f"Failed to submit task to NodeODM: {e}") from e
            logger.info(f"NodeODM task created: {task_id}")

            self.report_progress(job_id, 20, {
                "stage": "odm_processing",
                "nodeodm_task_id": task_id,
            })

            # Phase 3: Poll for progress (20-85%)
            try:
                self._poll_nodeodm(job_id, task_id, tmpdir, output_prefix, client)
            except _CancelledError:
                self._cancel_and_remove_nodeodm_task(task_id)
                return {"status": "cancelled"}

            if self.is_cancelled(job_id):
                self._cancel_and_remove_nodeodm_task(task_id)
                return {"status": "cancelled"}

            # Phase 4: Download orthophoto result (85-90%)
            # NodeODM's /download/orthophoto.tif convenience URL is unreliable
            # (returns "Invalid asset" even when the ortho exists). Download
            # all.zip and extract the orthophoto from it instead.
            self.report_progress(job_id, 86, {"stage": "downloading_result"})
            ortho_path = os.path.join(tmpdir, "odm_orthophoto.tif")
            zip_path = os.path.join(tmpdir, "all.zip")
            try:
                self._nodeodm.download_result(task_id, "all.zip", zip_path)
            except Exception as e:
                raise RuntimeError(f"Failed to download results from NodeODM: {e}") from e

            # Extract orthophoto from zip
            import zipfile
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    ortho_entry = None
                    for name in zf.namelist():
                        if name.endswith("odm_orthophoto.tif"):
                            ortho_entry = name
                            break
                    if ortho_entry is None:
                        raise RuntimeError(
                            "NodeODM did not produce an orthophoto. "
                            "The images may not have enough overlap or features."
                        )
                    with zf.open(ortho_entry) as src, open(ortho_path, "wb") as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
            except zipfile.BadZipFile:
                raise RuntimeError("NodeODM returned invalid zip file")

            ortho_size = os.path.getsize(ortho_path)
            if ortho_size < 1024:
                raise RuntimeError(
                    f"NodeODM produced an invalid orthophoto ({ortho_size} bytes). "
                    "The images may not have enough overlap or features for reconstruction."
                )
            logger.info(f"Extracted orthophoto: {ortho_size:,} bytes")

            # Phase 5: Upload orthophoto to MinIO (90-95%)
            self.report_progress(job_id, 91, {"stage": "uploading_result"})
            ortho_object_path = f"{output_prefix}odm_orthophoto.tif"
            client.fput_object(
                STORAGE_BUCKET,
                ortho_object_path,
                ortho_path,
                content_type="image/tiff",
            )
            logger.info(f"Uploaded orthophoto to {ortho_object_path}")

            # Phase 6: Save final log to MinIO (95-98%)
            self.report_progress(job_id, 96, {"stage": "saving_log"})
            self._save_log(task_id, output_prefix, client)

            # Phase 7: Submit CREATE_COG job for tile serving (96-98%)
            self.report_progress(job_id, 97, {"stage": "submitting_cog_job"})
            cog_job_id = self._submit_cog_job(ortho_object_path)
            if cog_job_id:
                logger.info(f"Submitted CREATE_COG job {cog_job_id} for {ortho_object_path}")

            # Phase 8: Cleanup NodeODM task (98-100%)
            self.report_progress(job_id, 99, {"stage": "cleanup"})
            self._remove_nodeodm_task(task_id)

            result = {
                "orthophoto_path": ortho_object_path,
                "image_count": len(image_paths),
            }
            if cog_job_id:
                result["cog_job_id"] = cog_job_id
            return result

    def _download_images(
        self, client, prefix: str, dest_dir: str, job_id: str
    ) -> list[str]:
        """Download all image files from MinIO prefix to a local directory."""
        objects = list(client.list_objects(STORAGE_BUCKET, prefix=prefix))
        image_objects = [
            obj
            for obj in objects
            if os.path.splitext(obj.object_name)[1].lower() in IMAGE_EXTENSIONS
        ]

        if not image_objects:
            # Try without "Images/" suffix as some uploads may not use it
            alt_prefix = prefix.rstrip("/").rsplit("/Images", 1)[0] + "/"
            if alt_prefix != prefix:
                objects = list(client.list_objects(STORAGE_BUCKET, prefix=alt_prefix))
                image_objects = [
                    obj
                    for obj in objects
                    if os.path.splitext(obj.object_name)[1].lower() in IMAGE_EXTENSIONS
                ]

        paths = []
        total = len(image_objects)
        for i, obj in enumerate(image_objects):
            if self.is_cancelled(job_id):
                return paths

            filename = os.path.basename(obj.object_name)
            local_path = os.path.join(dest_dir, filename)
            client.fget_object(STORAGE_BUCKET, obj.object_name, local_path)
            paths.append(local_path)

            # Map download progress to 2-15% range
            progress = 2 + (13 * (i + 1) / total)
            if (i + 1) % max(1, total // 10) == 0 or i == total - 1:
                self.report_progress(job_id, progress, {
                    "stage": "downloading_images",
                    "downloaded": i + 1,
                    "total": total,
                })

        return paths

    def _poll_nodeodm(
        self, job_id: str, task_id: str, tmpdir: str, output_prefix: str, client
    ):
        """
        Poll NodeODM for task progress, mapping to 20-85% range.

        Periodically saves log to MinIO so the frontend can display it.
        Raises _CancelledError if the job is cancelled.
        Fails the job after MAX_POLL_FAILURES consecutive poll errors.
        """
        log_line_offset = 0
        log_buffer = []
        last_log_save = time.time()
        log_save_interval = 5  # seconds
        consecutive_failures = 0

        while True:
            if self.is_cancelled(job_id):
                raise _CancelledError()

            try:
                info = self._nodeodm.get_task_info(task_id)
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                logger.warning(
                    f"Failed to get NodeODM task info ({consecutive_failures}/{MAX_POLL_FAILURES}): {e}"
                )
                if consecutive_failures >= MAX_POLL_FAILURES:
                    if log_buffer:
                        self._write_log_to_minio(log_buffer, output_prefix, client)
                    raise RuntimeError(
                        f"NodeODM unreachable after {consecutive_failures} attempts: {e}"
                    ) from e
                time.sleep(POLL_INTERVAL)
                continue

            status_code = info.get("status", {}).get("code", 0)
            odm_progress = info.get("progress", 0)

            # Fetch new log lines (get_task_output returns a list)
            try:
                new_lines = self._nodeodm.get_task_output(task_id, line=log_line_offset)
                if new_lines:
                    log_buffer.extend(new_lines)
                    log_line_offset += len(new_lines)
            except Exception:
                pass

            # Map ODM progress (0-100) to our 20-85 range
            mapped_progress = 20 + (odm_progress / 100.0) * 65

            log_tail = log_buffer[-5:] if log_buffer else []
            self.report_progress(job_id, mapped_progress, {
                "stage": "odm_processing",
                "odm_status_code": status_code,
                "odm_progress": odm_progress,
                "processing_time": info.get("processingTime", 0),
                "log_tail": log_tail,
            })

            # Periodically save log to MinIO
            if time.time() - last_log_save > log_save_interval and log_buffer:
                self._write_log_to_minio(log_buffer, output_prefix, client)
                last_log_save = time.time()

            if status_code == STATUS_COMPLETED:
                break
            elif status_code == STATUS_FAILED:
                error_msg = info.get("status", {}).get("errorMessage", "Unknown ODM error")
                # Save final log before failing
                if log_buffer:
                    self._write_log_to_minio(log_buffer, output_prefix, client)
                raise RuntimeError(f"ODM processing failed: {error_msg}")
            elif status_code == STATUS_CANCELLED:
                raise _CancelledError()

            time.sleep(POLL_INTERVAL)

        # Save final log
        if log_buffer:
            self._write_log_to_minio(log_buffer, output_prefix, client)

    def _save_log(self, task_id: str, output_prefix: str, client):
        """Fetch the complete log from NodeODM and save to MinIO."""
        try:
            log_lines = self._nodeodm.get_task_output(task_id, line=0)
            if log_lines:
                self._write_log_to_minio(log_lines, output_prefix, client)
        except Exception as e:
            logger.warning(f"Failed to save final ODM log: {e}")

    def _write_log_to_minio(self, log_lines: list[str], output_prefix: str, client):
        """Write log lines to MinIO as odm_log.txt."""
        import io

        log_text = "\n".join(log_lines)
        log_bytes = log_text.encode("utf-8")
        log_path = f"{output_prefix}odm_log.txt"
        client.put_object(
            STORAGE_BUCKET,
            log_path,
            io.BytesIO(log_bytes),
            len(log_bytes),
            content_type="text/plain",
        )

    def _cancel_and_remove_nodeodm_task(self, task_id: str):
        """Cancel a running/queued NodeODM task, then remove it."""
        try:
            self._nodeodm.cancel_task(task_id)
        except Exception:
            pass
        self._remove_nodeodm_task(task_id)

    def _submit_cog_job(self, ortho_path: str) -> str:
        """Submit a CREATE_COG job to convert the orthophoto to a tiled pyramid for map display."""
        try:
            resp = requests.post(
                f"{self.api_base_url}/api/jobs/submit",
                json={
                    "job_type": "CREATE_COG",
                    "parameters": {"input_path": ortho_path},
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                return str(resp.json().get("id", ""))
            else:
                logger.warning(f"Failed to submit CREATE_COG job: {resp.status_code} {resp.text}")
                return ""
        except Exception as e:
            logger.warning(f"Failed to submit CREATE_COG job: {e}")
            return ""

    def _remove_nodeodm_task(self, task_id: str):
        """Remove a completed/failed NodeODM task to free resources."""
        try:
            self._nodeodm.remove_task(task_id)
        except Exception:
            pass


class _CancelledError(Exception):
    """Internal signal for job cancellation."""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = OdmWorker()
    worker.run()
