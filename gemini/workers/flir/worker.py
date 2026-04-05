"""
FLIR binary extraction worker.

Handles EXTRACT_BINARY jobs: downloads Amiga .bin event files from MinIO,
runs the farm_ng-based extraction pipeline (RGB images, disparity maps,
GPS metadata), and uploads results back to MinIO.

The extraction logic is reused from the Flask backend's bin_to_images module,
which is mounted into the Docker image at /app/bin_to_images/.
"""
import logging
import os
import re
import tempfile
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


class FlirWorker(BaseWorker):
    """Worker for FLIR/Amiga binary extraction."""

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
                from gemini.workers.flir.bin_to_images import extract_binary
                extract_binary(local_bin_paths, output_dir)
            except Exception as e:
                raise RuntimeError(f"Binary extraction failed: {e}") from e

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Step 3: Upload results back to MinIO
            self.report_progress(job_id, 70, {"stage": "uploading"})

            # The output directory has structure:
            #   RGB/
            #     Metadata/ (CSVs)
            #     Images/{camera}/ (JPEGs)
            #   Disparity/{camera}/ (NPY)
            #   progress.txt, report.txt
            uploaded_count = 0
            files_to_upload = []
            for root, _dirs, filenames in os.walk(str(output_dir)):
                for fname in filenames:
                    if fname == "progress.txt":
                        continue  # Skip progress file — not needed in storage
                    local_file = os.path.join(root, fname)
                    # Build the MinIO object path relative to the upload dir_path
                    relative = os.path.relpath(local_file, str(output_dir))
                    # Place output alongside the input files' parent directory
                    # dir_path is e.g. "2024/Exp1/.../Amiga" — output goes as sibling dirs
                    parent_dir = str(Path(dir_path).parent)
                    object_name = f"{parent_dir}/{relative}"
                    files_to_upload.append((local_file, object_name))

            for i, (local_file, object_name) in enumerate(files_to_upload):
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

                client.fput_object(STORAGE_BUCKET, object_name, local_file)
                uploaded_count += 1

                upload_progress = 70 + (25 * (i + 1) / max(len(files_to_upload), 1))
                self.report_progress(job_id, upload_progress, {
                    "stage": "uploading",
                    "uploaded": uploaded_count,
                    "total_files": len(files_to_upload),
                })

            # Step 4: Clean up — delete original .bin files from MinIO
            self.report_progress(job_id, 95, {"stage": "cleanup"})
            for filename in bin_files:
                object_name = f"{dir_path}/{filename}"
                try:
                    client.remove_object(STORAGE_BUCKET, object_name)
                except Exception as e:
                    logger.warning(f"Failed to delete {object_name}: {e}")

        return {
            "status": "completed",
            "extracted_files": uploaded_count,
            "bin_files_processed": len(bin_files),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = FlirWorker()
    worker.run()
