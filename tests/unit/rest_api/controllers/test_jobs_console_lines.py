"""The Console's job lines: one per change of state or step, not per percent."""
import logging
from types import SimpleNamespace

from gemini.rest_api.controllers import jobs
from gemini.rest_api.controllers.utils import _log_buffer


def _job(status="RUNNING", detail=None):
    return SimpleNamespace(id="3f2a9c1b-0000", job_type="RUN_ODM", status=status, progress_detail=detail)


def test_a_new_step_is_a_line(caplog):
    with caplog.at_level(logging.INFO, logger=jobs.logger.name):
        jobs._log_status(_job(detail={"stage": "uploading images"}), "RUNNING", 40, {"stage": "matching"}, None)
    assert caplog.messages == ["job RUN_ODM 3f2a9c1b: running 40% — matching"]


def test_progress_alone_is_not(caplog):
    with caplog.at_level(logging.INFO, logger=jobs.logger.name):
        jobs._log_status(_job(detail={"stage": "matching"}), "RUNNING", 41, {"stage": "matching"}, None)
    assert caplog.messages == []


def test_a_failure_is_an_error_with_its_message(caplog):
    with caplog.at_level(logging.INFO, logger=jobs.logger.name):
        jobs._log_status(_job(), "FAILED", None, None, "S3 NoSuchKey")
    assert caplog.records[0].levelname == "ERROR"
    assert "failed" in caplog.messages[0] and "S3 NoSuchKey" in caplog.messages[0]


def test_info_lines_reach_the_console_buffer(monkeypatch):
    # Other tests may reconfigure logging: put back what the API sets up at import.
    from gemini.rest_api.controllers.utils import _ring_handler
    root = logging.getLogger()
    if _ring_handler not in root.handlers:
        root.addHandler(_ring_handler)
        monkeypatch.setattr(root, "handlers", root.handlers)   # restored after the test
    monkeypatch.setattr(root, "level", logging.INFO)
    job_log = logging.getLogger("gemini.rest_api.controllers.jobs")
    monkeypatch.setattr(job_log, "disabled", False)
    monkeypatch.setattr(job_log, "level", logging.NOTSET)
    before = len(_log_buffer)
    job_log.info("job X: submitted")
    assert len(_log_buffer) == min(before + 1, _log_buffer.maxlen)
    assert _log_buffer[-1]["message"].endswith("job X: submitted")
