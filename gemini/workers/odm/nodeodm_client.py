"""
Thin synchronous HTTP client for the NodeODM REST API.

NodeODM wraps OpenDroneMap with a task-based REST API for uploading images,
monitoring progress, and downloading results.

API reference: https://github.com/OpenDroneMap/NodeODM/blob/master/docs/index.adoc
"""

import json
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# NodeODM task status codes
STATUS_QUEUED = 10
STATUS_RUNNING = 20
STATUS_FAILED = 30
STATUS_COMPLETED = 40
STATUS_CANCELLED = 50


class NodeODMError(Exception):
    """Raised when a NodeODM API call fails."""


class NodeODMClient:
    """Synchronous client for NodeODM's REST API."""

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = (base_url or os.environ.get(
            "GEMINI_NODEODM_URL", "http://gemini-nodeodm:3000"
        )).rstrip("/")
        self.timeout = timeout

    def info(self) -> dict:
        """Get NodeODM server info (version, task count, etc.)."""
        resp = requests.get(f"{self.base_url}/info", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def create_task(
        self,
        image_paths: list[str],
        options: list[dict] = None,
        extra_files: list[str] | None = None,
    ) -> str:
        """
        Create a new processing task by uploading images.

        Uses NodeODM's chunked-init/upload/commit protocol:
            POST /task/new/init           → returns uuid
            POST /task/new/upload/{uuid}  → one image per request (streaming)
            POST /task/new/commit/{uuid}  → finalises the task

        The single-shot ``POST /task/new`` with all images as one multipart
        body is unusable for any real flight: requests buffers the whole
        body in RAM (337 × 10 MB ≈ 3 GB) before sending, blowing past the
        worker's container memory limit and getting OOM-killed mid-upload.
        Streaming one file per request keeps memory flat regardless of
        flight size.

        Args:
            image_paths: List of local file paths to upload.
            options: ODM processing options as list of {"name": ..., "value": ...} dicts.
            extra_files: Optional list of non-image files (e.g. ``gcp_list.txt``,
                ``geo.txt``) to include in the same NodeODM task. NodeODM
                identifies them by filename, not multipart field, so they go
                through the same ``/task/new/upload`` endpoint.

        Returns:
            Task UUID string.
        """
        # 1. Init: register the task and get its uuid.
        init_data = {}
        if options:
            init_data["options"] = json.dumps(options)
        init_resp = requests.post(
            f"{self.base_url}/task/new/init",
            data=init_data,
            timeout=self.timeout,
        )
        init_resp.raise_for_status()
        init_body = init_resp.json()
        task_uuid = init_body.get("uuid")
        if not task_uuid:
            raise NodeODMError(f"NodeODM /task/new/init returned no uuid: {init_body}")

        # 2. Upload images one at a time. Each request opens a single file
        #    handle and streams it, so peak memory is one image, not all of
        #    them.
        upload_url = f"{self.base_url}/task/new/upload/{task_uuid}"
        for path in image_paths:
            filename = os.path.basename(path)
            with open(path, "rb") as fh:
                up_resp = requests.post(
                    upload_url,
                    files={"images": (filename, fh, "image/jpeg")},
                    timeout=(self.timeout, 600),  # (connect, read)
                )
            try:
                up_resp.raise_for_status()
            except requests.HTTPError as e:
                raise NodeODMError(
                    f"Upload failed for {filename} (task {task_uuid}): "
                    f"{up_resp.status_code} {up_resp.text[:200]}"
                ) from e

        # 2b. Upload GCP sidecars (if any). NodeODM keys on filename, so the
        #     multipart field name stays "images" while the content type
        #     reflects the sidecar's actual mime.
        for path in extra_files or []:
            filename = os.path.basename(path)
            with open(path, "rb") as fh:
                up_resp = requests.post(
                    upload_url,
                    files={"images": (filename, fh, "text/plain")},
                    timeout=(self.timeout, 600),
                )
            try:
                up_resp.raise_for_status()
            except requests.HTTPError as e:
                raise NodeODMError(
                    f"Upload failed for sidecar {filename} (task {task_uuid}): "
                    f"{up_resp.status_code} {up_resp.text[:200]}"
                ) from e

        # 3. Commit: tell NodeODM the task is complete and ready to process.
        commit_resp = requests.post(
            f"{self.base_url}/task/new/commit/{task_uuid}",
            timeout=self.timeout,
        )
        commit_resp.raise_for_status()
        commit_body = commit_resp.json()
        # /commit returns the same uuid; double-check.
        committed_uuid = commit_body.get("uuid", task_uuid)
        if committed_uuid != task_uuid:
            raise NodeODMError(
                f"NodeODM /task/new/commit returned uuid {committed_uuid} "
                f"but init returned {task_uuid}"
            )
        return task_uuid

    def get_task_info(self, task_id: str) -> dict:
        """
        Get task status and progress.

        Returns dict with keys: uuid, status (dict with code), progress (0-100),
        processingTime, imagesCount, options, etc.
        """
        resp = requests.get(
            f"{self.base_url}/task/{task_id}/info",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_task_output(self, task_id: str, line: int = 0) -> list[str]:
        """
        Get processing log output starting from the given line number.

        Returns a list of log line strings (matching NodeODM's JSON array response).
        """
        resp = requests.get(
            f"{self.base_url}/task/{task_id}/output",
            params={"line": line},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list):
            return result
        return [str(result)]

    def download_result(self, task_id: str, asset: str, dest_path: str):
        """
        Download a task result asset (e.g. 'orthophoto.tif', 'all.zip').

        Streams to dest_path to handle large files.
        """
        with requests.get(
            f"{self.base_url}/task/{task_id}/download/{asset}",
            stream=True,
            timeout=(self.timeout, 600),  # (connect, read) — orthophotos can be large
        ) as resp:
            resp.raise_for_status()

            os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

    def cancel_task(self, task_id: str) -> dict:
        """Cancel a running or queued task."""
        resp = requests.post(
            f"{self.base_url}/task/cancel",
            json={"uuid": task_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def remove_task(self, task_id: str) -> dict:
        """Remove a task and free its resources."""
        resp = requests.post(
            f"{self.base_url}/task/remove",
            json={"uuid": task_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def is_healthy(self) -> bool:
        """Check if NodeODM is reachable and responding."""
        try:
            info = self.info()
            return "version" in info
        except Exception:
            return False
