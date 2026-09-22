"""
Ship worker log lines to the in-app console.

Each worker runs in its own container, so the REST API's in-memory log
buffer never saw them — the console showed the API alone, and a failed
ODM or ML job left no trace a user could read. Workers already talk to
Redis (the "logger" service); this handler pushes each record onto one
capped list, and ``GET /api/utils/logs`` merges it with the API's own
lines. No Docker socket involved, so it works under a production compose.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, List

LOG_KEY = "gemini:logs:workers"
MAX_LINES = 2000
# After a failed push, stay quiet this long before trying Redis again, so an
# outage (or a unit test with no Redis) doesn't pay a connect per record.
RETRY_AFTER_S = 30.0

_guard = threading.local()


class RedisLogHandler(logging.Handler):
    """Push records to a capped Redis list. Never raises, never recurses."""

    def __init__(self, client_factory: Callable[[], object], source: str):
        super().__init__(level=logging.INFO)
        self._client_factory = client_factory
        self._client = None
        self._down_until = 0.0
        self.source = source

    def emit(self, record: logging.LogRecord) -> None:
        # A log call made while shipping (e.g. from the redis client
        # itself) would otherwise recurse forever.
        if getattr(_guard, "busy", False) or time.monotonic() < self._down_until:
            return
        _guard.busy = True
        try:
            if self._client is None:
                self._client = self._client_factory()
            entry = json.dumps(
                {
                    "level": record.levelname,
                    "message": self.format(record),
                    "ts": record.created,
                    "source": self.source,
                }
            )
            pipe = self._client.pipeline()
            pipe.lpush(LOG_KEY, entry)
            pipe.ltrim(LOG_KEY, 0, MAX_LINES - 1)
            pipe.execute()
        except Exception:
            # Logging must never take a worker down: drop the line, back off,
            # then retry with a fresh client.
            self._client = None
            self._down_until = time.monotonic() + RETRY_AFTER_S
        finally:
            _guard.busy = False


def install(source: str, client_factory: Callable[[], object]) -> None:
    """Attach the handler to the root logger once per process."""
    root = logging.getLogger()
    if any(isinstance(h, RedisLogHandler) for h in root.handlers):
        return
    handler = RedisLogHandler(client_factory, source)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)


def read_worker_logs(client, limit: int = MAX_LINES) -> List[dict]:
    """Newest ``limit`` shipped lines, oldest first. [] if Redis is down."""
    try:
        raw = client.lrange(LOG_KEY, 0, max(limit, 1) - 1)
    except Exception:
        return []
    out: List[dict] = []
    for item in reversed(raw or []):
        try:
            line = json.loads(item)
        except (TypeError, ValueError):
            continue
        if isinstance(line, dict):
            out.append(line)
    return out


def source_for(worker_class_name: str) -> str:
    """``MlWorker`` → ``ml``, ``OdmWorker`` → ``odm``."""
    name = worker_class_name
    if name.lower().endswith("worker"):
        name = name[: -len("worker")]
    return name.lower() or "worker"

