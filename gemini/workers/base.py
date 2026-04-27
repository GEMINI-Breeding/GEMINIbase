"""
Base worker class for GEMINIbase processing workers.

Workers run as separate Docker containers. Each worker:
1. Polls the REST API for PENDING jobs matching its supported types
2. Claims a job by setting status to RUNNING
3. Executes the processing task
4. Reports progress via the REST API (which publishes to Redis pub/sub)
5. Marks the job COMPLETED or FAILED

Workers communicate with the framework exclusively through the REST API
and access files through MinIO (S3-compatible) storage.
"""
import json
import logging
import os
import signal
import time
from abc import ABC, abstractmethod
from typing import Set

import redis

from gemini.workers.auth import session_from_env
from gemini.workers.types import JobType, JobStatus

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Base class for all GEMINIbase processing workers.

    Subclasses must implement:
        - supported_job_types: set of JobType values this worker handles
        - process(job_id, job_type, parameters): execute the processing task
    """

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"{self.__class__.__name__}-{os.getpid()}"
        self.api_base_url = os.environ.get("GEMINI_REST_API_URL", "http://gemini-rest-api:7777")
        self.redis_host = os.environ.get("GEMINI_LOGGER_HOSTNAME", "gemini-logger")
        self.redis_port = int(os.environ.get("GEMINI_LOGGER_PORT", "6379"))
        self.redis_password = os.environ.get("GEMINI_LOGGER_PASSWORD", "gemini")
        self.poll_interval = int(os.environ.get("GEMINI_WORKER_POLL_INTERVAL", "5"))
        self._running = True
        self._redis_client = None
        # Authenticated HTTP session for REST-API calls. The WorkerSession
        # signs in with GEMINI_FIRST_SUPERUSER_EMAIL/PASSWORD, caches the
        # bearer token, and refreshes on 401 — required because the
        # REST-API JWT guard rejects unauthenticated /api/* traffic.
        self._http = session_from_env(api_base_url=self.api_base_url)

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    @property
    @abstractmethod
    def supported_job_types(self) -> Set[JobType]:
        """Set of job types this worker can process."""
        ...

    @abstractmethod
    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        """
        Execute the processing task.

        Args:
            job_id: UUID of the job.
            job_type: Type of job (e.g. TRAIN_MODEL).
            parameters: Job parameters from the submission.

        Returns:
            dict: Result data to store on the job.

        Raises:
            Exception: If processing fails, the exception message is stored
                       as the job's error_message.
        """
        ...

    def run(self):
        """Main worker loop: poll for jobs, process them."""
        logger.info(f"Worker {self.worker_id} starting, handling: {[jt.value for jt in self.supported_job_types]}")
        while self._running:
            try:
                job = self._poll_for_job()
                if job is not None:
                    self._execute_job(job)
                else:
                    time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(self.poll_interval)
        logger.info(f"Worker {self.worker_id} shutting down")

    def report_progress(self, job_id: str, progress: float, detail: dict = None):
        """Report job progress to the REST API and Redis pub/sub."""
        try:
            payload = {
                "status": "RUNNING",
                "progress": progress,
                "worker_id": self.worker_id,
            }
            if detail is not None:
                payload["progress_detail"] = detail

            self._http.patch(
                f"/api/jobs/{job_id}/status",
                json=payload,
            )
        except Exception as e:
            logger.warning(f"Failed to report progress for {job_id}: {e}")

    def is_cancelled(self, job_id: str) -> bool:
        """Check if the job has been cancelled."""
        try:
            resp = self._http.get(f"/api/jobs/{job_id}", timeout=5)
            if resp.status_code == 200:
                return resp.json().get("status") == "CANCELLED"
        except Exception:
            pass
        return False

    def _poll_for_job(self):
        """
        Try to atomically claim the oldest PENDING job via /api/jobs/claim.
        Falls back to the legacy GET+PATCH pattern if the claim endpoint
        is not available (e.g., older REST API image).

        Returns the claimed job dict (already in RUNNING status) or None.
        """
        for job_type in self.supported_job_types:
            try:
                # Try atomic claim first (prevents race conditions)
                resp = self._http.post(
                    "/api/jobs/claim",
                    json={"job_type": job_type.value, "worker_id": self.worker_id},
                )
                if resp.status_code in (200, 201):
                    job = resp.json()
                    job["_claimed"] = True
                    return job
                if resp.status_code == 404:
                    continue  # No pending jobs of this type
                if resp.status_code == 405:
                    # Claim endpoint not available — fall back to legacy
                    return self._poll_for_job_legacy()
            except Exception as e:
                logger.warning(f"Claim error for {job_type.value}: {e}")
        return None

    def _poll_for_job_legacy(self):
        """Legacy polling: GET pending jobs then claim via PATCH (race-prone)."""
        for job_type in self.supported_job_types:
            try:
                resp = self._http.get(
                    "/api/jobs/all",
                    params={"status": "PENDING", "job_type": job_type.value},
                )
                if resp.status_code == 200:
                    jobs = resp.json()
                    if jobs and len(jobs) > 0:
                        return jobs[0]
            except Exception as e:
                logger.warning(f"Poll error for {job_type.value}: {e}")
        return None

    def _execute_job(self, job: dict):
        """Claim (if needed) and execute a job."""
        job_id = str(job["id"])
        job_type = job["job_type"]
        parameters = job.get("parameters") or {}

        # If not already claimed via atomic endpoint, claim via PATCH
        if not job.get("_claimed"):
            try:
                resp = self._http.patch(
                    f"/api/jobs/{job_id}/status",
                    json={"status": "RUNNING", "worker_id": self.worker_id},
                )
                if resp.status_code != 200:
                    logger.warning(f"Failed to claim job {job_id}: {resp.status_code}")
                    return
            except Exception as e:
                logger.error(f"Failed to claim job {job_id}: {e}")
                return

        logger.info(f"Processing job {job_id} ({job_type})")
        try:
            result = self.process(job_id, job_type, parameters)
            # Workers signal cancellation by returning {"status": "cancelled"}
            # (the only way to bail out of `process()` without raising). Without
            # this branch, the base loop would PATCH the job to COMPLETED with
            # progress=100, which is misleading and breaks any downstream code
            # that branches on job.status.
            cancelled = (
                isinstance(result, dict)
                and str(result.get("status", "")).lower() == "cancelled"
            )
            if cancelled:
                self._http.patch(
                    f"/api/jobs/{job_id}/status",
                    json={
                        "status": "CANCELLED",
                        "result": result,
                        "worker_id": self.worker_id,
                    },
                )
                logger.info(f"Job {job_id} cancelled mid-processing")
            else:
                self._http.patch(
                    f"/api/jobs/{job_id}/status",
                    json={
                        "status": "COMPLETED",
                        "progress": 100.0,
                        "result": result or {},
                        "worker_id": self.worker_id,
                    },
                )
                logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            try:
                self._http.patch(
                    f"/api/jobs/{job_id}/status",
                    json={
                        "status": "FAILED",
                        "error_message": str(e),
                        "worker_id": self.worker_id,
                    },
                )
            except Exception:
                logger.error(f"Failed to report failure for job {job_id}")

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self._running = False
