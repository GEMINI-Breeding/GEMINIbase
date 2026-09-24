"""GET /api/<entity>/id/{id}/records streams NDJSON from a DB-backed generator.

- Fetching rows is blocking DB work and must not run on the event loop.
- An error before the first row is an ordinary 500.
- An error mid-stream must break the response, never end it like a
  complete file (Litestar ends a sync-iterator stream quietly on ValueError).
"""
import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

CASES = [
    ("datasets", "dataset", "Dataset"),
    ("sensors", "sensor", "Sensor"),
    ("procedures", "procedure", "Procedure"),
    ("models", "model", "Model"),
    ("scripts", "script", "Script"),
    ("traits", "trait", "Trait"),
]
IDS = [c[0] for c in CASES]


def _record(i):
    record = MagicMock()
    record.model_dump.return_value = {"i": i}
    return record


class _Rows:
    """Iterator standing in for a server-side DB cursor."""

    def __init__(self, n, fail_at=None, error=RuntimeError("db connection lost")):
        self.n, self.fail_at, self.error = n, fail_at, error
        self.i = 0
        self.fetched_on_loop = []

    def __iter__(self):
        return self

    def __next__(self):
        try:
            asyncio.get_running_loop()
            self.fetched_on_loop.append(True)
        except RuntimeError:
            self.fetched_on_loop.append(False)
        if self.i == self.fail_at:
            raise self.error
        if self.i >= self.n:
            raise StopIteration
        self.i += 1
        return _record(self.i)


def _get(test_client, route, module, entity, rows):
    with patch(f"gemini.rest_api.controllers.{module}.{entity}") as cls:
        cls.get_by_id.return_value.search_records.return_value = rows
        return test_client.get(f"/api/{route}/id/abc/records")


@pytest.mark.parametrize("route,module,entity", CASES, ids=IDS)
def test_streams_every_row_off_the_event_loop(route, module, entity, test_client):
    rows = _Rows(1200)
    res = _get(test_client, route, module, entity, rows)
    assert res.status_code == 200
    lines = res.text.splitlines()
    assert [json.loads(line)["i"] for line in lines] == list(range(1, 1201))
    assert rows.fetched_on_loop and not any(rows.fetched_on_loop)


@pytest.mark.parametrize("route,module,entity", CASES, ids=IDS)
def test_error_before_first_row_is_a_500(route, module, entity, test_client):
    res = _get(test_client, route, module, entity, _Rows(10, fail_at=0))
    assert res.status_code == 500
    assert "db connection lost" in res.text


@pytest.mark.parametrize("error", [RuntimeError("db connection lost"), ValueError("bad row")], ids=["RuntimeError", "ValueError"])
@pytest.mark.parametrize("route,module,entity", CASES, ids=IDS)
def test_error_mid_stream_breaks_the_response(route, module, entity, error, test_client):
    with pytest.raises(Exception):
        _get(test_client, route, module, entity, _Rows(10, fail_at=5, error=error))
