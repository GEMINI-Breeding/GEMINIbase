"""
farm-ng Amiga OAK binary extraction worker.

Handles EXTRACT_BINARY jobs: downloads Amiga .bin event files from MinIO,
runs the farm_ng-based extraction pipeline (RGB images, disparity maps,
GPS metadata), and uploads results back to MinIO.
"""
import logging
import os
import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Set

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

# MinIO PUTs for the output tree are I/O-bound and the dominant cost of
# the job — a typical .bin decodes to hundreds of small JPEGs + NPYs.
UPLOAD_POOL_SIZE = 8
CLEANUP_POOL_SIZE = 4


def _get_minio_client():
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _extract_timestamp(filename: str) -> str:
    """Extract timestamp from Amiga binary filename for sorting."""
    match = re.match(r"(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}_\d+)", filename)
    return match.group(1) if match else filename


class AmigaWorker(BaseWorker):
    """Worker for farm-ng Amiga OAK binary extraction."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.EXTRACT_BINARY}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.EXTRACT_BINARY.value:
            return self._extract_binary_job(job_id, parameters)
        raise ValueError(f"Unsupported job type: {job_type}")

    def _extract_binary_job(self, job_id: str, parameters: dict) -> dict:
        """
        Extract Amiga .bin files into RGB images, disparity maps, and GPS metadata.

        Parameters (from job submission):
            files: list of filenames (e.g. ["2024_01_15_12_30_45_001.bin", ...])
            localDirPath: MinIO object prefix where files were uploaded
                          (e.g. "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/Amiga")
        """
        file_list = parameters.get("files", [])
        dir_path = parameters.get("localDirPath", "")

        if not file_list or not dir_path:
            raise ValueError("Missing required parameters: 'files' and 'localDirPath'")

        # Filter to .bin files only and sort by timestamp
        bin_files = sorted(
            [f for f in file_list if f.endswith(".bin")],
            key=_extract_timestamp,
        )

        if not bin_files:
            return {"status": "skipped", "message": "No .bin files to extract"}

        client = _get_minio_client()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Step 1: Download .bin files from MinIO
            self.report_progress(job_id, 5, {"stage": "downloading", "total_files": len(bin_files)})
            local_bin_paths = []
            for i, filename in enumerate(bin_files):
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

                object_name = f"{dir_path}/{filename}"
                local_path = str(input_dir / filename)
                logger.info(f"Downloading {object_name} from MinIO")
                client.fget_object(STORAGE_BUCKET, object_name, local_path)
                local_bin_paths.append(local_path)

                dl_progress = 5 + (25 * (i + 1) / len(bin_files))
                self.report_progress(job_id, dl_progress, {
                    "stage": "downloading",
                    "file": filename,
                    "downloaded": i + 1,
                    "total_files": len(bin_files),
                })

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Step 2: Run extraction
            self.report_progress(job_id, 30, {"stage": "extracting"})
            try:
                from gemini.workers.amiga.bin_to_images import extract_binary
                extract_binary(local_bin_paths, output_dir)
            except Exception as e:
                raise RuntimeError(f"Binary extraction failed: {e}") from e

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Step 3: Upload results back to MinIO (parallel — this is the
            # dominant cost of the job, hundreds of small files per .bin).
            self.report_progress(job_id, 70, {"stage": "uploading"})

            # The output directory has structure:
            #   RGB/
            #     Metadata/ (CSVs)
            #     Images/{camera}/ (JPEGs)
            #   Disparity/{camera}/ (NPY)
            #   progress.txt, report.txt
            files_to_upload = []
            for root, _dirs, filenames in os.walk(str(output_dir)):
                for fname in filenames:
                    if fname == "progress.txt":
                        continue  # Skip progress file — not needed in storage
                    local_file = os.path.join(root, fname)
                    relative = os.path.relpath(local_file, str(output_dir))
                    parent_dir = str(Path(dir_path).parent)
                    object_name = f"{parent_dir}/{relative}"
                    files_to_upload.append((local_file, object_name))

            total = len(files_to_upload)
            counter_lock = threading.Lock()
            counter = {"n": 0}

            def _upload_one(item):
                local_file, object_name = item
                client.fput_object(STORAGE_BUCKET, object_name, local_file)
                with counter_lock:
                    counter["n"] += 1
                    done = counter["n"]
                upload_progress = 70 + (25 * done / max(total, 1))
                self.report_progress(job_id, upload_progress, {
                    "stage": "uploading",
                    "uploaded": done,
                    "total_files": total,
                })

            with ThreadPoolExecutor(max_workers=UPLOAD_POOL_SIZE) as pool:
                futures = [pool.submit(_upload_one, item) for item in files_to_upload]
                try:
                    for fut in as_completed(futures):
                        if self.is_cancelled(job_id):
                            for pending in futures:
                                pending.cancel()
                            return {"status": "cancelled"}
                        fut.result()  # re-raise any per-task exception
                except Exception:
                    for pending in futures:
                        pending.cancel()
                    raise

            uploaded_count = counter["n"]

            # Step 4: Clean up — delete original .bin files from MinIO.
            self.report_progress(job_id, 95, {"stage": "cleanup"})

            def _remove_one(filename):
                object_name = f"{dir_path}/{filename}"
                try:
                    client.remove_object(STORAGE_BUCKET, object_name)
                except Exception as e:
                    logger.warning(f"Failed to delete {object_name}: {e}")

            with ThreadPoolExecutor(max_workers=CLEANUP_POOL_SIZE) as pool:
                for _ in pool.map(_remove_one, bin_files):
                    pass

        return {
            "status": "completed",
            "extracted_files": uploaded_count,
            "bin_files_processed": len(bin_files),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = AmigaWorker()
    worker.run()
