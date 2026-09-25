"""ndjson_stream: sync, batched, and fails fast on a broken query."""
import inspect

import pytest
from pydantic import BaseModel

from gemini.rest_api.ndjson import ndjson_stream


class Rec(BaseModel):
    id: int
    note: str | None = None


def test_is_a_sync_generator_of_batched_lines():
    out = ndjson_stream((Rec(id=i) for i in range(5)), batch_size=2)
    # Litestar only moves *sync* iterators off the event loop.
    assert inspect.isgenerator(out)
    chunks = list(out)
    assert chunks == [b'{"id":0}\n{"id":1}\n', b'{"id":2}\n{"id":3}\n', b'{"id":4}\n']


def test_empty_and_none_yield_nothing():
    assert list(ndjson_stream(iter([]))) == []
    assert list(ndjson_stream(None)) == []


def test_query_error_raises_before_streaming():
    def broken():
        raise RuntimeError("server closed the connection")
        yield  # pragma: no cover

    # Raised here, inside the handler's try/except → a 500, not a
    # truncated 200 body.
    with pytest.raises(RuntimeError):
        ndjson_stream(broken())
