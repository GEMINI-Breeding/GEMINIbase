"""
Jobs controller for submitting, monitoring, and cancelling processing jobs.

Provides REST endpoints for job CRUD and a WebSocket endpoint for
real-time progress streaming via Redis pub/sub.
"""
import json
import logging
from datetime import datetime
from typing import Annotated, List, Optional

from litestar import Response, WebSocket
from litestar.handlers import get, post, patch, delete, websocket
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.job import Job
from gemini.rest_api.models import (
    JobSubmitInput,
    JobClaimInput,
    JobOutput,
    JobStatusUpdate,
    RESTAPIError,
)

logger = logging.getLogger(__name__)


def _sweep_gwas_artifacts(job_id: str) -> int:
    """Remove every MinIO object under ``gwas/{job_id}/``.

    Called by delete_job for RUN_GWAS rows. Resolves the storage
    endpoint through `GEMINIManager.get_component_settings(STORAGE)`
    — the same path the files controller uses — so the right
    hostname (`geminibase-storage`) is picked up from the active
    deployment's settings even when the env var isn't propagated
    into this container. Returns the number of objects removed; logs
    and swallows per-object errors so a single permissions hiccup
    doesn't strand the rest of the sweep (the delete-the-row half of
    the operation is the user's primary intent — they can chase
    stragglers from MinIO admin if needed).
    """
    try:
        from minio import Minio
        from gemini.manager import GEMINIManager, GEMINIComponentType
    except ImportError as exc:
        logger.warning(
            "GWAS artifact sweep dependencies unavailable: %s", exc,
        )
        return 0

    try:
        settings = GEMINIManager().get_component_settings(
            GEMINIComponentType.STORAGE,
        )
        host = settings["GEMINI_STORAGE_HOSTNAME"]
        port = settings["GEMINI_STORAGE_PORT"]
        access_key = settings["GEMINI_STORAGE_ACCESS_KEY"]
        secret_key = settings["GEMINI_STORAGE_SECRET_KEY"]
        bucket = settings["GEMINI_STORAGE_BUCKET_NAME"]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not load storage settings for GWAS sweep: %s", exc,
        )
        return 0

    prefix = f"gwas/{job_id}/"
    try:
        client = Minio(
            f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        removed = 0
        for obj in objects:
            try:
                client.remove_object(bucket, obj.object_name)
                removed += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to remove %s/%s during GWAS cleanup: %s",
                    bucket, obj.object_name, exc,
                )
        return removed
    except Exception as exc:  # noqa: BLE001
        logger.warning("GWAS artifact sweep failed for %s: %s", job_id, exc)
        return 0

# Valid job types that workers can process
VALID_JOB_TYPES = {
    "TRAIN_MODEL",
    "LOCATE_PLANTS",
    "EXTRACT_TRAITS",
    "RUN_STITCH",
    "RUN_ODM",
    "SPLIT_ORTHOMOSAIC",
    "PROCESS_DRONE_TIFF",
    "TIF_TO_PNG",
    "CREATE_COG",
    "EXTRACT_BINARY",
    "RUN_GWAS",
    "THERMAL_EXTRACT",
}


class JobController(Controller):

    @post(path="/submit", sync_to_thread=True)
    def submit_job(self, data: Annotated[JobSubmitInput, Body]) -> JobOutput:
        """Submit a new processing job to the queue."""
        try:
            if data.job_type not in VALID_JOB_TYPES:
                return Response(
                    content=RESTAPIError(
                        error="Invalid job type",
                        error_description=f"Job type must be one of: {', '.join(sorted(VALID_JOB_TYPES))}",
                    ),
                    status_code=400,
                )
            job = Job.create(
                job_type=data.job_type,
                parameters=data.parameters,
                experiment_id=data.experiment_id,
            )
            if job is None:
                return Response(
                    content=RESTAPIError(
                        error="Job creation failed",
                        error_description="Failed to create job record",
                    ),
                    status_code=500,
                )
            # Publish job to Redis so workers can pick it up
            _publish_job_event(str(job.id), "SUBMITTED", {"job_type": data.job_type})
            return job
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to submit job"),
                status_code=500,
            )

    @post(path="/claim", sync_to_thread=True)
    def claim_job(self, data: Annotated[JobClaimInput, Body]) -> JobOutput:
        """
        Atomically claim the oldest PENDING job of the given type.

        Uses SELECT ... FOR UPDATE SKIP LOCKED to guarantee that only one
        worker can claim a given job, even when multiple workers poll
        simultaneously. Returns the claimed job (now RUNNING) or 404 if
        no PENDING jobs of this type exist.
        """
        try:
            if data.job_type not in VALID_JOB_TYPES:
                return Response(
                    content=RESTAPIError(
                        error="Invalid job type",
                        error_description=f"Job type must be one of: {', '.join(sorted(VALID_JOB_TYPES))}",
                    ),
                    status_code=400,
                )
            job = Job.claim(job_type=data.job_type, worker_id=data.worker_id)
            if job is None:
                return Response(
                    content=RESTAPIError(
                        error="No jobs available",
                        error_description=f"No PENDING jobs of type {data.job_type}",
                    ),
                    status_code=404,
                )
            _publish_job_event(str(job.id), "RUNNING", {"worker_id": data.worker_id})
            return job
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to claim job"),
                status_code=500,
            )

    @get(path="/{job_id:str}", sync_to_thread=True)
    def get_job(self, job_id: str) -> JobOutput:
        """Get job status by ID."""
        try:
            job = Job.get_by_id(id=job_id)
            if job is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=f"Job {job_id} not found"),
                    status_code=404,
                )
            return job
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get job"),
                status_code=500,
            )

    @get(path="/all", sync_to_thread=True)
    def get_all_jobs(self, limit: int = 100, offset: int = 0,
                     status: Optional[str] = None,
                     job_type: Optional[str] = None) -> List[JobOutput]:
        """List jobs, optionally filtered by status or type.

        Returns newest-first by `created_at` so consumers (frontend
        Recent-jobs table, status pollers) get the most relevant rows
        without each having to re-sort. The underlying `Job.search` /
        `Job.get_all` come back in insertion order, which surfaces stale
        CANCELLED rows above the running job — confusing.
        """
        try:
            search_kwargs = {}
            if status:
                search_kwargs["status"] = status
            if job_type:
                search_kwargs["job_type"] = job_type

            if search_kwargs:
                jobs = Job.search(**search_kwargs)
            else:
                jobs = Job.get_all(limit=limit, offset=offset)

            jobs = jobs or []
            jobs.sort(
                key=lambda j: getattr(j, "created_at", None) or datetime.min,
                reverse=True,
            )
            return jobs
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to list jobs"),
                status_code=500,
            )

    @post(path="/{job_id:str}/cancel", sync_to_thread=True)
    def cancel_job(self, job_id: str) -> JobOutput:
        """Cancel a pending or running job."""
        try:
            job = Job.get_by_id(id=job_id)
            if job is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=f"Job {job_id} not found"),
                    status_code=404,
                )
            updated = job.cancel()
            if updated is None:
                return Response(
                    content=RESTAPIError(
                        error="Cannot cancel",
                        error_description=f"Job is in status {job.status} and cannot be cancelled",
                    ),
                    status_code=409,
                )
            _publish_job_event(job_id, "CANCELLED", {})
            return updated
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to cancel job"),
                status_code=500,
            )

    @patch(path="/{job_id:str}/status", sync_to_thread=True)
    def update_job_status(self, job_id: str,
                          data: Annotated[JobStatusUpdate, Body]) -> JobOutput:
        """Update job status (used by workers to report progress/completion)."""
        try:
            job = Job.get_by_id(id=job_id)
            if job is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=f"Job {job_id} not found"),
                    status_code=404,
                )
            # Refuse to transition out of a terminal state. Without this guard,
            # a worker that finishes its `process()` after the user has already
            # cancelled the job overwrites the CANCELLED status with COMPLETED
            # and progress=100, making it look like the cancellation never
            # happened.
            terminal_states = ("COMPLETED", "FAILED", "CANCELLED")
            if (
                job.status in terminal_states
                and data.status != job.status
            ):
                logger.info(
                    f"Refusing status transition {job.status} → {data.status} "
                    f"for job {job_id} (job is already terminal)"
                )
                return job
            update_kwargs = {"status": data.status}
            if data.worker_id is not None:
                update_kwargs["worker_id"] = data.worker_id
            if data.progress is not None:
                update_kwargs["progress"] = data.progress
            if data.progress_detail is not None:
                update_kwargs["progress_detail"] = data.progress_detail
            if data.result is not None:
                update_kwargs["result"] = data.result
            if data.error_message is not None:
                update_kwargs["error_message"] = data.error_message
            # Stamp completed_at when the job lands in a terminal state.
            # Workers PATCH status=COMPLETED/FAILED/CANCELLED but don't supply
            # completed_at themselves; without this the column stays NULL and
            # downstream consumers that read completion time get incorrect
            # data. Job.complete()/fail()/cancel() already do this for direct
            # in-process callers; mirror that behavior here.
            if data.status in terminal_states and job.completed_at is None:
                update_kwargs["completed_at"] = datetime.now()

            updated = job.update(**update_kwargs)
            if updated is None:
                return Response(
                    content=RESTAPIError(error="Update failed", error_description="Failed to update job"),
                    status_code=500,
                )
            # Publish progress event for WebSocket subscribers. error_message
            # rides along on terminal-FAILED frames so the UI can surface the
            # actual worker exception (e.g. "S3 NoSuchKey ...") instead of just
            # the last-seen stage label.
            _publish_job_event(job_id, data.status, {
                "progress": data.progress,
                "progress_detail": data.progress_detail,
                "error_message": data.error_message,
            })
            return updated
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to update job status"),
                status_code=500,
            )

    @delete(path="/{job_id:str}", sync_to_thread=True, status_code=200)
    def delete_job(self, job_id: str) -> dict:
        """Delete a job record and any side-effect artifacts.

        For RUN_GWAS specifically the worker writes ~12 files into
        MinIO under ``gwas/{job_id}/`` (manhattan/qq/kinship PNGs,
        run.assoc.txt, kin.cXX.txt, qc.{bed,bim,fam,log},
        pca.eigenvec, covar.txt, result.json, etc). Without sweeping
        those, deleting the job row would leave dangling objects the
        user can't see or recover. We list-and-remove the whole
        prefix; failures here are logged but don't block the row
        delete — better to leak a few files than refuse the user's
        cleanup. Other job types don't currently park anything in
        MinIO under a deterministic prefix, so they need no sweep.
        """
        try:
            job = Job.get_by_id(id=job_id)
            if job is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=f"Job {job_id} not found"),
                    status_code=404,
                )

            objects_removed = 0
            if str(job.job_type) == "RUN_GWAS":
                objects_removed = _sweep_gwas_artifacts(job_id)

            job.delete()
            return {
                "status": "deleted",
                "id": job_id,
                "minio_objects_removed": objects_removed,
            }
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to delete job"),
                status_code=500,
            )

    @websocket(path="/{job_id:str}/progress")
    async def job_progress_ws(self, socket: WebSocket, job_id: str) -> None:
        """
        WebSocket endpoint for real-time job progress.

        Subscribes to Redis pub/sub channel `job:{job_id}:progress` and
        forwards messages to the connected client. The connection closes
        when the job reaches a terminal state (COMPLETED, FAILED, CANCELLED)
        or when the client disconnects.

        Uses non-blocking polling with asyncio to avoid blocking the event
        loop on synchronous Redis operations, and monitors the WebSocket
        receive channel to detect client disconnects promptly.
        """
        import asyncio

        await socket.accept()
        pubsub = None
        try:
            redis_client = _get_redis_client()
            if redis_client is None:
                await socket.send_json({"error": "Redis unavailable"})
                await socket.close()
                return

            pubsub = redis_client.pubsub()
            channel = f"job:{job_id}:progress"
            pubsub.subscribe(channel)

            # Send current status immediately. Late subscribers (e.g. user
            # opens a job page after a FAILED job already finished) need the
            # error_message in this snapshot — the redis pub/sub will not
            # replay past events.
            job = Job.get_by_id(id=job_id)
            if job is not None:
                await socket.send_json({
                    "status": job.status,
                    "progress": job.progress,
                    "progress_detail": job.progress_detail,
                    "error_message": job.error_message,
                })
                if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
                    return

            async def listen_redis():
                """Poll Redis for pub/sub messages without blocking the event loop."""
                while True:
                    # redis-py's pubsub.get_message is synchronous; calling it
                    # directly inside an async coroutine blocks the event loop
                    # for `timeout` seconds. With N open WebSockets that's N
                    # parallel blockers and any sync_to_thread HTTP handler
                    # (e.g. PATCH /jobs/{id}/status) starves. Push it to a
                    # thread so the loop stays responsive.
                    message = await asyncio.to_thread(
                        pubsub.get_message,
                        ignore_subscribe_messages=True, timeout=1.0,
                    )
                    if message is not None and message["type"] == "message":
                        data = json.loads(message["data"])
                        await socket.send_json(data)
                        if data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                            return
                    # Yield to the event loop between polls
                    await asyncio.sleep(0.1)

            async def listen_client():
                """Wait for client disconnect."""
                try:
                    while True:
                        await socket.receive_data(mode="text")
                except Exception:
                    # Any exception means the client disconnected
                    return

            redis_task = asyncio.create_task(listen_redis())
            client_task = asyncio.create_task(listen_client())

            done, pending = await asyncio.wait(
                [redis_task, client_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        except Exception as e:
            logger.error(f"WebSocket error for job {job_id}: {e}")
        finally:
            if pubsub is not None:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass
            try:
                await socket.close()
            except Exception:
                pass


def _get_redis_client():
    """Get a Redis client using the GEMINIbase logger settings."""
    try:
        import redis
        from gemini.config.settings import GEMINISettings
        settings = GEMINISettings()
        return redis.Redis(
            host=settings.GEMINI_LOGGER_HOSTNAME,
            port=settings.GEMINI_LOGGER_PORT,
            password=settings.GEMINI_LOGGER_PASSWORD,
            decode_responses=True,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def _publish_job_event(job_id: str, status: str, data: dict):
    """Publish a job event to Redis pub/sub for WebSocket subscribers."""
    try:
        client = _get_redis_client()
        if client is None:
            return
        message = json.dumps({"status": status, **data})
        client.publish(f"job:{job_id}:progress", message)
        client.close()
    except Exception as e:
        logger.error(f"Failed to publish job event: {e}")
