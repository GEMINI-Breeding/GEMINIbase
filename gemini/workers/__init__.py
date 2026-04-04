"""
GEMINI processing workers.

Workers poll the job queue via the REST API, execute processing tasks,
and report progress back via the REST API (which publishes to Redis
pub/sub for WebSocket subscribers).
"""
from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

__all__ = ["BaseWorker", "JobType"]
