"""Worker log lines reach the in-app console via Redis."""
import json
import logging
from unittest.mock import MagicMock

from gemini.workers import log_shipping
from gemini.workers.log_shipping import (
    LOG_KEY,
    MAX_LINES,
    SOURCES_KEY,
    RedisLogHandler,
    read_worker_logs,
    source_for,
    source_key,
)


def _record(msg, level=logging.INFO):
    return logging.LogRecord("gemini.workers.odm", level, __file__, 1, msg, None, None)


def test_pushes_tagged_line_and_caps_the_list():
    client = MagicMock()
    h = RedisLogHandler(lambda: client, "odm")
    h.emit(_record("Uploaded orthophoto"))
    pipe = client.pipeline.return_value
    key, payload = pipe.lpush.call_args.args
    assert key == f"{LOG_KEY}:odm"  # its own list
    line = json.loads(payload)
    assert line["source"] == "odm"
    assert line["level"] == "INFO"
    assert "Uploaded orthophoto" in line["message"]
    pipe.ltrim.assert_called_once_with(f"{LOG_KEY}:odm", 0, MAX_LINES - 1)
    pipe.sadd.assert_called_once_with(SOURCES_KEY, "odm")


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


class FakeRedis:
    """lpush/ltrim/sadd/smembers/lrange, like the real thing."""

    def __init__(self):
        self.lists, self.sets = {}, {}

    def pipeline(self):
        return self

    def execute(self):
        pass

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key, start, stop):
        self.lists[key] = self.lists.get(key, [])[start:stop + 1]

    def sadd(self, key, member):
        self.sets.setdefault(key, set()).add(member.encode())

    def smembers(self, key):
        return self.sets.get(key, set())

    def lrange(self, key, start, stop):
        return self.lists.get(key, [])[start:stop + 1]


def test_read_merges_workers_oldest_first_and_skips_junk():
    r = FakeRedis()
    r.lpush(source_key("odm"), json.dumps({"message": "first", "ts": 1, "source": "odm"}))
    r.lpush(source_key("ml"), "not json")
    r.lpush(source_key("ml"), json.dumps({"message": "third", "ts": 3, "source": "ml"}))
    r.sadd(SOURCES_KEY, "odm")
    r.sadd(SOURCES_KEY, "ml")
    # Lines a worker wrote to the old shared list are still shown.
    r.lpush(LOG_KEY, json.dumps({"message": "second", "ts": 2, "source": "geo"}))
    assert [l["message"] for l in read_worker_logs(r)] == ["first", "second", "third"]


def test_a_noisy_worker_does_not_evict_a_quiet_ones_lines():
    r = FakeRedis()
    quiet = RedisLogHandler(lambda: r, "gwas")
    noisy = RedisLogHandler(lambda: r, "stitch")
    quiet.emit(_record("Worker gwas starting"))
    for i in range(MAX_LINES * 3):  # e.g. retries while the API restarts
        noisy.emit(_record(f"retry {i}"))
    lines = read_worker_logs(r)
    assert any("Worker gwas starting" in l["message"] for l in lines)
    assert sum(l["source"] == "stitch" for l in lines) == MAX_LINES


def test_read_is_empty_when_redis_is_down():
    client = MagicMock()
    client.smembers.side_effect = ConnectionError()
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
