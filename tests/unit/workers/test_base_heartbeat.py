"""A worker must keep a long, quiet job visibly alive.

The reaper fails RUNNING jobs whose updated_at is older than its threshold.
Progress reports bump updated_at, but a process() step can run for a long
time without reporting (an ODM or stitch run), so the worker sends
heartbeats for as long as process() is running.
"""
from __future__ import annotations

import threading
import time
from typing import Set
from unittest.mock import MagicMock

import pytest

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType


class _QuietWorker(BaseWorker):
    """Runs for a while without reporting any progress."""

    run_for = 0.4

    @property
    def supported_job_types(self) -> Set[JobType]:
        return set()

    def process(self, job_id, job_type, parameters):
        time.sleep(self.run_for)
        return {}


@pytest.fixture
def worker(monkeypatch):
    http = MagicMock()
    http.patch.return_value = MagicMock(status_code=200)
    http.post.return_value = MagicMock(status_code=200)
    monkeypatch.setattr("gemini.workers.base.session_from_env", lambda **kw: http)
    monkeypatch.setattr("gemini.workers.base.signal.signal", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_WORKER_HEARTBEAT_SECONDS", "0.05")
    return _QuietWorker(worker_id="quiet-1"), http


def _heartbeats(http, job_id):
    return [c for c in http.post.call_args_list if c.args and c.args[0] == f"/api/jobs/{job_id}/heartbeat"]


def test_heartbeats_while_processing(worker):
    w, http = worker
    w._execute_job({"id": "job-1", "job_type": "RUN_ODM", "_claimed": True})
    assert len(_heartbeats(http, "job-1")) >= 2


def test_heartbeats_stop_when_job_finishes(worker):
    w, http = worker
    w._execute_job({"id": "job-1", "job_type": "RUN_ODM", "_claimed": True})
    sent = len(_heartbeats(http, "job-1"))
    time.sleep(0.2)
    assert len(_heartbeats(http, "job-1")) == sent
    assert not [t for t in threading.enumerate() if t.name.startswith("job-heartbeat")]


def test_heartbeat_failure_does_not_fail_the_job(worker):
    w, http = worker
    http.post.side_effect = ConnectionError("api down")
    w._execute_job({"id": "job-1", "job_type": "RUN_ODM", "_claimed": True})
    terminal = http.patch.call_args.kwargs["json"]
    assert terminal["status"] == "COMPLETED"
