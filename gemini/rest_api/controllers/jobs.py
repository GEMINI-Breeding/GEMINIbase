"""
Jobs controller for submitting, monitoring, and cancelling processing jobs.

Provides REST endpoints for job CRUD and a WebSocket endpoint for
real-time progress streaming via Redis pub/sub.
"""
import json
import logging
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
        """List jobs, optionally filtered by status or type."""
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

            return jobs or []
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

            updated = job.update(**update_kwargs)
            if updated is None:
                return Response(
                    content=RESTAPIError(error="Update failed", error_description="Failed to update job"),
                    status_code=500,
                )
            # Publish progress event for WebSocket subscribers
            _publish_job_event(job_id, data.status, {
                "progress": data.progress,
                "progress_detail": data.progress_detail,
            })
            return updated
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to update job status"),
                status_code=500,
            )

    @delete(path="/{job_id:str}", sync_to_thread=True, status_code=200)
    def delete_job(self, job_id: str) -> dict:
        """Delete a job record."""
        try:
            job = Job.get_by_id(id=job_id)
            if job is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=f"Job {job_id} not found"),
                    status_code=404,
                )
            job.delete()
            return {"status": "deleted", "id": job_id}
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

            # Send current status immediately
            job = Job.get_by_id(id=job_id)
            if job is not None:
                await socket.send_json({
                    "status": job.status,
                    "progress": job.progress,
                    "progress_detail": job.progress_detail,
                })
                if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
                    return

            async def listen_redis():
                """Poll Redis for pub/sub messages without blocking the event loop."""
                while True:
                    # Use get_message with a short timeout to yield control
                    # back to the event loop, allowing disconnect detection.
                    message = pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
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
    """Get a Redis client using the GEMINI logger settings."""
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
