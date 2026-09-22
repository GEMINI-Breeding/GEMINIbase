"""Worker log lines reach the in-app console via Redis."""
import json
import logging
from unittest.mock import MagicMock

from gemini.workers import log_shipping
from gemini.workers.log_shipping import (
    LOG_KEY,
    MAX_LINES,
    RedisLogHandler,
    read_worker_logs,
    source_for,
)


def _record(msg, level=logging.INFO):
    return logging.LogRecord("gemini.workers.odm", level, __file__, 1, msg, None, None)


def test_pushes_tagged_line_and_caps_the_list():
    client = MagicMock()
    h = RedisLogHandler(lambda: client, "odm")
    h.emit(_record("Uploaded orthophoto"))
    pipe = client.pipeline.return_value
    key, payload = pipe.lpush.call_args.args
    assert key == LOG_KEY
    line = json.loads(payload)
    assert line["source"] == "odm"
    assert line["level"] == "INFO"
    assert "Uploaded orthophoto" in line["message"]
    pipe.ltrim.assert_called_once_with(LOG_KEY, 0, MAX_LINES - 1)


def test_redis_failure_is_swallowed_then_backs_off():
    calls = []

    def factory():
        calls.append(1)
        raise ConnectionError("no redis")

    h = RedisLogHandler(factory, "ml")
    h.emit(_record("a"))  # must not raise
    h.emit(_record("b"))  # within back-off: no new connect attempt
    assert len(calls) == 1


def test_does_not_recurse_when_the_client_logs():
    client = MagicMock()
    h = RedisLogHandler(lambda: client, "geo")

    def noisy_execute():
        h.emit(_record("from inside redis"))

    client.pipeline.return_value.execute.side_effect = noisy_execute
    h.emit(_record("outer"))
    assert client.pipeline.return_value.lpush.call_count == 1


def test_read_returns_oldest_first_and_skips_junk():
    client = MagicMock()
    newest_first = [
        json.dumps({"message": "second", "ts": 2, "source": "ml"}),
        "not json",
        json.dumps({"message": "first", "ts": 1, "source": "odm"}),
    ]
    client.lrange.return_value = newest_first
    assert [l["message"] for l in read_worker_logs(client)] == ["first", "second"]


def test_read_is_empty_when_redis_is_down():
    client = MagicMock()
    client.lrange.side_effect = ConnectionError()
    assert read_worker_logs(client) == []


def test_source_names():
    assert source_for("MlWorker") == "ml"
    assert source_for("OdmWorker") == "odm"
    assert source_for("GeoWorker") == "geo"


def test_install_once():
    root = logging.getLogger()
    before = [h for h in root.handlers if isinstance(h, RedisLogHandler)]
    for h in before:
        root.removeHandler(h)
    try:
        log_shipping.install("ml", MagicMock)
        log_shipping.install("ml", MagicMock)
        assert len([h for h in root.handlers if isinstance(h, RedisLogHandler)]) == 1
    finally:
        for h in [h for h in root.handlers if isinstance(h, RedisLogHandler)]:
            root.removeHandler(h)
        for h in before:
            root.addHandler(h)


def test_api_merges_its_lines_with_workers_by_time():
    from gemini.rest_api.controllers.utils import merge_log_lines

    api = [{"level": "INFO", "message": "GET /api/jobs", "ts": 2}]
    workers = [
        {"level": "INFO", "message": "odm start", "ts": 1, "source": "odm"},
        {"level": "ERROR", "message": "ml failed", "ts": 3, "source": "ml"},
    ]
    merged = merge_log_lines(api, workers)
    assert [(l["source"], l["ts"]) for l in merged] == [("odm", 1), ("api", 2), ("ml", 3)]
    assert merge_log_lines(api, workers, source="ml")[0]["message"] == "ml failed"
    assert [l["ts"] for l in merge_log_lines(api, workers, level="error")] == [3]
    assert [l["ts"] for l in merge_log_lines(api, workers, since=2)] == [2, 3]
    assert [l["ts"] for l in merge_log_lines(api, workers, limit=1)] == [3]
