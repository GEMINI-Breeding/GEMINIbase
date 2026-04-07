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

    def create_task(self, image_paths: list[str], options: list[dict] = None) -> str:
        """
        Create a new processing task by uploading images.

        Args:
            image_paths: List of local file paths to upload.
            options: ODM processing options as list of {"name": ..., "value": ...} dicts.

        Returns:
            Task UUID string.
        """
        files = []
        try:
            for path in image_paths:
                filename = os.path.basename(path)
                fh = open(path, "rb")
                files.append(("images", (filename, fh, "image/jpeg")))

            data = {}
            if options:
                data["options"] = json.dumps(options)

            resp = requests.post(
                f"{self.base_url}/task/new",
                files=files,
                data=data,
                timeout=600,  # Large uploads may take a while
            )
        finally:
            for _, (_, fh, _) in files:
                fh.close()

        resp.raise_for_status()
        result = resp.json()
        if "uuid" not in result:
            raise NodeODMError(f"NodeODM did not return a task UUID: {result}")
        return result["uuid"]

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
