"""The orphaned-job reaper must keep running while the REST API is up.

It used to run once at startup, so a worker that crashed later left its
job RUNNING until the next REST-API restart.
"""
import time
from unittest.mock import patch

from gemini.rest_api import app as app_module


def test_reaper_runs_repeatedly(monkeypatch):
    from litestar.testing import TestClient

    monkeypatch.setitem(app_module.settings.__dict__, "GEMINI_JOB_REAPER_INTERVAL_SECONDS", 0.05)
    with patch.object(app_module, "reap_orphaned_jobs", return_value=[]) as reap:
        with TestClient(app=app_module.app):
            deadline = time.monotonic() + 3
            while reap.call_count < 3 and time.monotonic() < deadline:
                time.sleep(0.05)
    assert reap.call_count >= 3


def test_reaper_failure_does_not_stop_later_sweeps(monkeypatch):
    from litestar.testing import TestClient

    monkeypatch.setitem(app_module.settings.__dict__, "GEMINI_JOB_REAPER_INTERVAL_SECONDS", 0.05)
    with patch.object(app_module, "reap_orphaned_jobs", side_effect=RuntimeError("db down")) as reap:
        with TestClient(app=app_module.app):
            deadline = time.monotonic() + 3
            while reap.call_count < 3 and time.monotonic() < deadline:
                time.sleep(0.05)
    assert reap.call_count >= 3



def test_boot_sweep_finishes_before_requests_are_served(monkeypatch):
    """A job inserted after startup must not be swept by the boot pass."""
    from litestar.testing import TestClient

    finished = []

    def slow_sweep(_threshold):
        time.sleep(0.3)
        finished.append(True)
        return []

    monkeypatch.setitem(app_module.settings.__dict__, "GEMINI_JOB_REAPER_INTERVAL_SECONDS", 60)
    with patch.object(app_module, "reap_orphaned_jobs", side_effect=slow_sweep):
        with TestClient(app=app_module.app):
            assert finished == [True]
