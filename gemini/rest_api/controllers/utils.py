"""
Utility endpoints used by the GEMINI-App frontend.

- GET /api/utils/capabilities — which job types have a live worker (from
  when each was last polled for), whether stitching and ODM can run, and
  torch/CPU facts, so the frontend can warn before launching a step whose
  job would only wait in the queue.
- GET /api/utils/logs — recent backend log lines from an in-memory ring
  buffer, consumed by the frontend console tab.
- GET /api/utils/health-check — simple boolean liveness probe.

This controller deliberately does not depend on the full stack (db, redis,
minio), so it responds reliably even when those backends are unhealthy.
"""
from __future__ import annotations

import collections
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Optional

from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers import get

from gemini.api.user import User
from gemini.rest_api.dependencies import require_superuser

# ────────────────────────────────────────────────────────────────────────────
# In-memory log ring buffer — attached to the root logger at import time so
# every log record emitted while the process lives is captured for the UI.
# ────────────────────────────────────────────────────────────────────────────

_LOG_BUFFER_SIZE = 500
_log_buffer: collections.deque = collections.deque(maxlen=_LOG_BUFFER_SIZE)


class _RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _log_buffer.append(
                {
                    "level": record.levelname,
                    "message": self.format(record),
                    "ts": record.created,
                }
            )
        except Exception:
            self.handleError(record)


_ring_handler = _RingBufferHandler()
_ring_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
# Only attach once — import-safe under uvicorn --reload.
_root_logger = logging.getLogger()
if not any(isinstance(h, _RingBufferHandler) for h in _root_logger.handlers):
    _root_logger.addHandler(_ring_handler)


# ────────────────────────────────────────────────────────────────────────────

def merge_log_lines(
    api_lines: List[dict],
    worker_lines: List[dict],
    *,
    limit: Optional[int] = None,
    level: Optional[str] = None,
    since: Optional[float] = None,
    source: Optional[str] = None,
) -> List[dict]:
    """Tag the API's lines, merge with workers' by time, then filter."""
    lines = [{**l, "source": "api"} for l in api_lines] + list(worker_lines)
    lines.sort(key=lambda l: float(l.get("ts", 0)))
    if source:
        lines = [l for l in lines if l.get("source") == source]
    if level:
        wanted = level.upper()
        lines = [l for l in lines if l.get("level") == wanted]
    if since is not None:
        lines = [l for l in lines if float(l.get("ts", 0)) >= since]
    if limit is not None and limit > 0:
        lines = lines[-limit:]
    return lines


def _worker_log_lines() -> List[dict]:
    """Log lines the worker containers shipped to Redis; [] if unreachable."""
    from gemini.rest_api.controllers.jobs import _get_redis_client
    from gemini.workers.log_shipping import read_worker_logs

    client = _get_redis_client()
    return read_worker_logs(client) if client is not None else []


# A job type counts as served if a worker polled for it this recently.
WORKER_LIVE_SECONDS = 60


def _live(job_type: str) -> bool:
    from gemini.rest_api.controllers.jobs import workers_seen

    age = workers_seen().get(job_type)
    return age is not None and age <= WORKER_LIVE_SECONDS


def _agrowstitch_status() -> dict:
    """Whether stitching can run: a stitch worker (whose image carries
    AgRowStitch) is polling for RUN_STITCH. The old check looked for
    AgRowStitch inside the API container, where it never is."""
    return {"available": _live("RUN_STITCH"), "path": None}


def _nodeodm_status() -> dict:
    """Whether orthomosaics can run: an ODM worker is polling for RUN_ODM
    and NodeODM answers."""
    import urllib.request

    url = os.environ.get("GEMINI_NODEODM_URL", "http://geminibase-nodeodm:3000")
    try:
        with urllib.request.urlopen(f"{url}/info", timeout=2) as r:
            reachable = r.status == 200
    except Exception:
        reachable = False
    return {"worker": _live("RUN_ODM"), "nodeodm": reachable}


def _workers_seen_public() -> dict:
    from gemini.rest_api.controllers.jobs import workers_seen

    return workers_seen()


def _torch_status() -> dict:
    """Report torch version and GPU backend availability, gracefully absent."""
    try:
        import torch  # type: ignore
    except ImportError:
        return {"torch_version": None, "cuda_available": False, "mps_available": False}
    return {
        "torch_version": getattr(torch, "__version__", None),
        "cuda_available": bool(getattr(torch.cuda, "is_available", lambda: False)()),
        "mps_available": bool(
            getattr(torch.backends, "mps", None)
            and getattr(torch.backends.mps, "is_available", lambda: False)()
        ),
    }


class UtilsController(Controller):

    dependencies = {
        "superuser": Provide(require_superuser, sync_to_thread=True),
    }

    @get(path="/health-check", sync_to_thread=False)
    def health_check(self) -> bool:
        return True

    @get(path="/capabilities", sync_to_thread=True)
    def capabilities(self) -> dict:
        torch = _torch_status()
        return {
            "agrowstitch": _agrowstitch_status(),
            "odm": _nodeodm_status(),
            "workers": _workers_seen_public(),
            "torch_version": torch["torch_version"],
            "cuda_available": torch["cuda_available"],
            "mps_available": torch["mps_available"],
            "cpu_count": os.cpu_count() or 1,
        }

    @get(path="/logs", sync_to_thread=True)
    def get_logs(
        self,
        superuser: User,
        limit: Optional[int] = None,
        level: Optional[str] = None,
        since: Optional[float] = None,
        source: Optional[str] = None,
    ) -> List[dict]:
        """The API's own log lines plus every worker's (shipped via Redis),
        oldest first, each tagged with ``source`` ("api", "ml", "odm", …)."""
        # Snapshot the buffer so concurrent writes don't skew the response.
        return merge_log_lines(
            list(_log_buffer),
            _worker_log_lines(),
            limit=limit,
            level=level,
            since=since,
            source=source,
        )

