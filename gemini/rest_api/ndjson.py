"""NDJSON streaming for the ``/records`` endpoints.

The record searches are lazy sync generators that hold a DB cursor. They
used to be wrapped in an ``async def`` generator, which Litestar iterates
on the event loop: the query, every row fetch and every JSON encode ran
there, so one large export stalled every other request (the API is a
single process). Litestar moves a *sync* iterator to a worker thread, one
``next()`` per hop, so this module hands it a sync generator that yields
batches of lines.

It also pulls the first record up front, inside the (sync_to_thread)
handler. A failing query then raises there and becomes a 500, instead of
surfacing after the 200 headers went out as a silently truncated body.
"""
from collections.abc import Iterable, Iterator

from litestar.serialization import encode_json

_BATCH = 500
_END = object()


def _line(record) -> bytes:
    return encode_json(record.model_dump(exclude_none=True)) + b"\n"


def ndjson_stream(records: Iterable | None, batch_size: int = _BATCH) -> Iterator[bytes]:
    it = iter(records or ())
    first = next(it, _END)

    def batches() -> Iterator[bytes]:
        if first is _END:
            return
        buf = [_line(first)]
        for record in it:
            buf.append(_line(record))
            if len(buf) >= batch_size:
                yield b"".join(buf)
                buf = []
        yield b"".join(buf)

    return batches()
