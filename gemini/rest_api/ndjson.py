"""NDJSON streaming of record generators for the REST API.

The record generators read a server-side DB cursor, so each step is
blocking I/O. Handing Litestar a *sync* iterator makes it advance the
iterator in a worker thread instead of on the event loop; rows are sent in
batches so that's one thread hop per batch, not per row.
"""
from typing import Iterable, Iterator

from litestar.response import Stream
from litestar.serialization import encode_json
from pydantic import BaseModel

RECORDS_PER_CHUNK = 500

_NO_RECORDS = object()


class RecordStreamError(RuntimeError):
    """A record generator failed after the response had started."""


def ndjson_stream(records: Iterable[BaseModel]) -> Stream:
    """Stream ``records`` as NDJSON.

    The first record is fetched before the response starts, so a query that
    fails outright raises here and the caller can answer with a 500.
    """
    iterator = iter(records)
    first = next(iterator, _NO_RECORDS)
    return Stream(_ndjson_chunks(first, iterator), media_type="application/ndjson")


def _encode(record: BaseModel) -> bytes:
    return encode_json(record.model_dump(exclude_none=True)) + b"\n"


def _ndjson_chunks(first, iterator: Iterator[BaseModel]) -> Iterator[bytes]:
    if first is _NO_RECORDS:
        return
    chunk = [_encode(first)]
    try:
        for record in iterator:
            chunk.append(_encode(record))
            if len(chunk) >= RECORDS_PER_CHUNK:
                yield b"".join(chunk)
                chunk = []
    except Exception as e:
        # Re-raise as a non-ValueError: Litestar's sync-iterator wrapper
        # treats ValueError as the end of the stream, which would turn a
        # failed query into a truncated response that looks complete.
        raise RecordStreamError(f"Record stream failed: {e}") from e
    if chunk:
        yield b"".join(chunk)
