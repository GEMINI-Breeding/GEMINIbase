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
import math
import os
import signal
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Set

import redis

from gemini.workers.auth import session_from_env
from gemini.workers.types import JobType, JobStatus

# Seconds between liveness pings for a running job. Mirrors
# gemini.api.job_reaper.HEARTBEAT_INTERVAL_SECONDS (not imported: workers
# don't carry the DB stack). The API fails a RUNNING job whose pings stop.
HEARTBEAT_INTERVAL_SECONDS = 30

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    """Recursively replace NaN / +-Inf with None inside a JSON-ish tree.

    Worker results (e.g. GWAS summary stats such as genomic-inflation λ)
    can legitimately contain NaN / Inf. The status PATCH goes through
    stdlib json which emits literal ``NaN`` / ``Infinity`` tokens, and
    Litestar's server-side validator rejects those ("Out of range float
    values are not JSON compliant"), leaving the job stuck in RUNNING.
    Coerce at the result boundary so a quirky dataset can't strand a job.
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


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
        # REST-API JWT guard rejects unauthenticated /api/* traffic. With
        # auth disabled (GEMINI_JWT_SECRET unset) it sends no token.
        self._http = session_from_env(api_base_url=self.api_base_url)

        # Ship this worker's log lines to the in-app console (see
        # log_shipping). Best-effort: a Redis outage only loses lines.
        from gemini.workers import log_shipping

        log_shipping.install(
            log_shipping.source_for(self.__class__.__name__),
            lambda: redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True,
                socket_timeout=2,
            ),
        )

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
        # Run the actual job. Any exception here is a *job* failure, not a
        # transport failure — keep this try/except narrowly scoped so we can
        # tell the two apart when reporting status back to the API.
        process_failed = False
        result: dict | None = None
        process_error: Exception | None = None
        stop_heartbeat = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(job_id, stop_heartbeat),
            name=f"heartbeat-{job_id[:8]}",
            daemon=True,
        )
        heartbeat.start()
        try:
            result = self.process(job_id, job_type, parameters)
        except Exception as e:
            process_failed = True
            process_error = e
            logger.error(f"Job {job_id} failed: {e}")
        finally:
            stop_heartbeat.set()

        if process_failed:
            self._report_terminal_status(
                job_id,
                {
                    "status": "FAILED",
                    "error_message": str(process_error),
                    "worker_id": self.worker_id,
                },
                outcome_label="failure",
            )
            return

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
            self._report_terminal_status(
                job_id,
                {
                    "status": "CANCELLED",
                    "result": result,
                    "worker_id": self.worker_id,
                },
                outcome_label="cancellation",
            )
            logger.info(f"Job {job_id} cancelled mid-processing")
            return

        self._report_terminal_status(
            job_id,
            {
                "status": "COMPLETED",
                "progress": 100.0,
                "result": result or {},
                "worker_id": self.worker_id,
            },
            outcome_label="completion",
        )
        logger.info(f"Job {job_id} completed successfully")

    def _heartbeat(self, job_id: str, stop: threading.Event) -> None:
        """Ping the API while `process()` runs, so the reaper knows we're alive.

        Progress PATCHes also count, but many steps (a long NodeODM stage,
        GEMMA, a big download) report nothing for minutes. Failures are
        logged and ignored; the reaper only acts after several missed pings.
        """
        while not stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                self._http.post(f"/api/jobs/{job_id}/heartbeat", timeout=10)
            except Exception as e:
                logger.warning(f"Heartbeat for job {job_id} failed: {e}")

    def _report_terminal_status(
        self,
        job_id: str,
        payload: dict,
        outcome_label: str,
    ) -> None:
        """PATCH a terminal status with an extra retry loop on top of WorkerSession.

        The WorkerSession already retries transport-level errors a few times,
        but the terminal PATCH is special: if it never lands, the DB stays in
        RUNNING and any frontend WebSocket subscriber will hang on the
        previous progress frame indefinitely (Redis pub/sub is ephemeral and
        the WS controller hydrates from the DB on connect). So we burn a
        little extra time here in the rare case the WorkerSession exhausted
        its own retries — losing the terminal write is much worse than a
        delayed worker.
        """
        max_outer_attempts = 3
        # NaN / Inf in the result would make the API reject the PATCH (4xx)
        # on every attempt; sanitize once up front.
        payload = _json_safe(payload)
        for attempt in range(max_outer_attempts):
            try:
                resp = self._http.patch(f"/api/jobs/{job_id}/status", json=payload)
                status_code = getattr(resp, "status_code", None)
                if isinstance(status_code, int) and not 200 <= status_code < 300:
                    # A non-2xx response means the terminal write did NOT
                    # land — treat it like a transport failure and retry.
                    body = ""
                    try:
                        body = (resp.text or "")[:500]
                    except Exception:
                        pass
                    raise RuntimeError(f"HTTP {status_code}: {body}")
                return
            except Exception as e:
                if attempt + 1 >= max_outer_attempts:
                    logger.critical(
                        "Failed to report %s for job %s after %d attempts: %s — "
                        "DB will be left in non-terminal state until manual "
                        "intervention or worker restart",
                        outcome_label,
                        job_id,
                        max_outer_attempts,
                        e,
                    )
                    return
                delay = 2 ** attempt
                logger.warning(
                    "Failed to report %s for job %s on attempt %d/%d (%s); "
                    "retrying in %ds",
                    outcome_label,
                    job_id,
                    attempt + 1,
                    max_outer_attempts,
                    e,
                    delay,
                )
                time.sleep(delay)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self._running = False
