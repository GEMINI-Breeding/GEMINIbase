"""BaseWorker pings /heartbeat while a job runs, and stops when it ends.

The API's reaper fails a RUNNING job whose pings stop, so a job whose
worker was killed doesn't stay RUNNING forever.
"""
from __future__ import annotations

import time
from typing import Set
from unittest.mock import MagicMock

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType


class _SlowWorker(BaseWorker):
    @property
    def supported_job_types(self) -> Set[JobType]:
        return set()

    def process(self, job_id, job_type, parameters):
        time.sleep(0.2)
        return {}


def _worker(monkeypatch) -> _SlowWorker:
    fake_http = MagicMock()
    fake_http.patch.return_value.status_code = 200
    monkeypatch.setattr("gemini.workers.base.session_from_env", lambda **kw: fake_http)
    monkeypatch.setattr("gemini.workers.base.signal.signal", lambda *a, **kw: None)
    monkeypatch.setattr("gemini.workers.base.HEARTBEAT_INTERVAL_SECONDS", 0.02)
    return _SlowWorker(worker_id="test-worker")


def _heartbeats(worker) -> int:
    return sum(
        1
        for c in worker._http.post.call_args_list
        if c.args and c.args[0] == "/api/jobs/job-1/heartbeat"
    )


def test_heartbeats_while_running_and_stops_after(monkeypatch):
    worker = _worker(monkeypatch)
    worker._execute_job({"id": "job-1", "job_type": "X", "_claimed": True})
    during = _heartbeats(worker)
    assert during >= 3
    time.sleep(0.1)
    assert _heartbeats(worker) == during  # thread stopped with the job


def test_heartbeat_errors_do_not_fail_the_job(monkeypatch):
    worker = _worker(monkeypatch)
    worker._http.post.side_effect = ConnectionError("api down")
    worker._execute_job({"id": "job-1", "job_type": "X", "_claimed": True})
    final = worker._http.patch.call_args.kwargs["json"]
    assert final["status"] == "COMPLETED"
