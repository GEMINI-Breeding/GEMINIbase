"""
Unit tests for ``BaseWorker._report_terminal_status``.

This is the *outer* retry loop that sits on top of ``WorkerSession`` for the
terminal PATCH only (COMPLETED / FAILED / CANCELLED). The reason for its
existence is in the docstring on ``_report_terminal_status``: if the terminal
PATCH never lands, the DB stays in ``RUNNING`` and any frontend WS subscriber
hangs on the previous progress frame indefinitely.

Pinned contract:

  * First-attempt success → exactly one PATCH, no sleep.
  * Recoverable failure on first attempt → second attempt succeeds and
    we slept once.
  * Exhausted retries → swallowed (no exception bubbles up to the worker
    poll loop) but logged at CRITICAL so it's still visible in monitoring.

These tests construct a minimal subclass of ``BaseWorker`` so we can call
the helper without booting the full poll loop, and stub the HTTP session
so the test runs entirely in-process.
"""
from __future__ import annotations

import logging
from typing import Set
from unittest.mock import MagicMock, patch

import pytest

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType


class _StubWorker(BaseWorker):
    """Minimal concrete BaseWorker — supports nothing, processes nothing."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return set()

    def process(self, job_id, job_type, parameters):  # pragma: no cover
        return {}


@pytest.fixture
def stub_worker(monkeypatch):
    """Build a _StubWorker with no docker/redis side-effects.

    ``BaseWorker.__init__`` calls ``session_from_env`` which would try to
    log into the REST API. Patch that to a MagicMock so we can intercept
    PATCH calls in-test.
    """
    fake_http = MagicMock()
    monkeypatch.setattr(
        "gemini.workers.base.session_from_env",
        lambda **kwargs: fake_http,
    )
    # Signal handlers complain when set off the main thread under pytest-xdist.
    monkeypatch.setattr("gemini.workers.base.signal.signal", lambda *a, **kw: None)

    w = _StubWorker(worker_id="stub-1")
    return w, fake_http


def test_first_attempt_success_no_retry(stub_worker):
    w, http = stub_worker
    http.patch.return_value = MagicMock(status_code=200)

    with patch("gemini.workers.base.time.sleep") as sleep:
        w._report_terminal_status(
            "job-1",
            {"status": "COMPLETED", "progress": 100.0, "result": {}, "worker_id": "stub-1"},
            outcome_label="completion",
        )

    assert http.patch.call_count == 1
    args, kwargs = http.patch.call_args
    assert args[0] == "/api/jobs/job-1/status"
    assert kwargs["json"]["status"] == "COMPLETED"
    sleep.assert_not_called()


def test_recovers_after_one_transport_failure(stub_worker):
    """First PATCH raises (e.g. WorkerSession finally exhausted *its* retries),
    second succeeds. We must sleep once with backoff and end successfully."""
    w, http = stub_worker
    http.patch.side_effect = [
        ConnectionError("ECONNRESET on terminal PATCH"),
        MagicMock(status_code=200),
    ]

    with patch("gemini.workers.base.time.sleep") as sleep:
        w._report_terminal_status(
            "job-2",
            {"status": "FAILED", "error_message": "boom", "worker_id": "stub-1"},
            outcome_label="failure",
        )

    assert http.patch.call_count == 2
    # Outer-loop backoff is exponential: 2**0 = 1s after the first failure.
    sleep.assert_called_once_with(1)


def test_exhausted_retries_swallows_exception_and_logs_critical(stub_worker, caplog):
    """If every attempt fails, the helper must NOT raise — the worker poll
    loop would otherwise crash on a job whose work is already done. Instead,
    log at CRITICAL so the stuck-RUNNING state is visible to monitoring."""
    w, http = stub_worker
    http.patch.side_effect = ConnectionError("network gone")

    with patch("gemini.workers.base.time.sleep") as sleep, \
         caplog.at_level(logging.CRITICAL, logger="gemini.workers.base"):
        # Must not raise.
        w._report_terminal_status(
            "job-3",
            {"status": "COMPLETED", "progress": 100.0, "result": {}, "worker_id": "stub-1"},
            outcome_label="completion",
        )

    # Three outer attempts, two retry-sleeps (after attempts 1 and 2; none
    # after the final attempt).
    assert http.patch.call_count == 3
    assert [c.args[0] for c in sleep.call_args_list] == [1, 2]

    # Critical log is the *only* signal a human gets that the DB is stuck
    # in non-terminal state — assert it contains both the job id and the
    # outcome label so log-greps actually find it.
    critical = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert critical, "Expected a CRITICAL log record on retry exhaustion"
    msg = critical[0].getMessage()
    assert "job-3" in msg
    assert "completion" in msg
