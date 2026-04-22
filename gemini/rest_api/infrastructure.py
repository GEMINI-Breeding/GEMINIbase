"""Infrastructure health gating for the REST API.

The API layer in ``gemini/api/*`` currently catches all exceptions and returns
``None`` when the underlying operation fails — which means a database outage
surfaces to clients as an opaque 500 with a ``psycopg2.OperationalError``
message in the body. This module provides the two pieces needed to give
clients an actionable 503 instead:

1. ``infrastructure_gate`` — a ``before_request`` hook that short-circuits
   requests with a 503 when the database is known to be unreachable. Results
   are cached for a few seconds so a dead DB doesn't cost every request the
   full connect timeout.
2. ``exception_handlers`` — a fallback mapping that catches SQLAlchemy
   connectivity errors that somehow escape the API/controller layers (e.g. if
   the DB disappears mid-request, after the gate has already passed).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from litestar import Request, Response
from litestar.exceptions import HTTPException
from sqlalchemy import exc as sa_exc

from gemini.db.core.base import db_engine
from gemini.rest_api.models import RESTAPIError


# Paths that must remain reachable even when the DB is down so operators can
# diagnose the outage. The liveness probe and OpenAPI surface should never
# 503, and the API key middleware runs before this hook anyway.
_UNGATED_PATHS = frozenset({"/", "/healthz", "/settings", "/schema"})


@dataclass
class HealthSnapshot:
    healthy: bool
    detail: Optional[str] = None
    checked_at: float = 0.0


class _DatabaseHealth:
    """Caches the last DB probe so every request doesn't hit the network."""

    def __init__(self, ttl_seconds: float = 3.0) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._snapshot: Optional[HealthSnapshot] = None

    def status(self) -> HealthSnapshot:
        now = time.monotonic()
        with self._lock:
            snap = self._snapshot
            if snap is not None and (now - snap.checked_at) < self._ttl:
                return snap

        fresh = self._probe()
        with self._lock:
            # Last writer wins — fine for a liveness signal.
            self._snapshot = fresh
        return fresh

    @staticmethod
    def _probe() -> HealthSnapshot:
        try:
            ok = db_engine.check_health()
        except Exception as e:  # defensive — check_health shouldn't raise
            return HealthSnapshot(
                healthy=False,
                detail=_short_cause(e),
                checked_at=time.monotonic(),
            )
        if ok:
            return HealthSnapshot(healthy=True, checked_at=time.monotonic())
        return HealthSnapshot(
            healthy=False,
            detail="database connection probe failed",
            checked_at=time.monotonic(),
        )


database_health = _DatabaseHealth()


def _short_cause(exc: BaseException) -> str:
    """Pull a one-line human-readable cause out of a SQLAlchemy error."""
    orig = getattr(exc, "orig", None) or exc
    first_line = str(orig).splitlines()[0] if str(orig) else exc.__class__.__name__
    return first_line.strip()


def _database_unavailable_response(detail: Optional[str]) -> Response:
    body = RESTAPIError(
        error="database_unavailable",
        error_description=(
            "The GEMINI database is unreachable. Check that the gemini-db "
            "container is running and accepting connections"
            + (f" (cause: {detail})" if detail else "")
            + "."
        ),
    )
    return Response(content=body, status_code=503)


def infrastructure_gate(request: Request) -> Optional[Response]:
    """``before_request`` hook: return a 503 when the DB is down.

    Returning ``None`` lets the handler run normally. Returning a ``Response``
    short-circuits the request — Litestar will send it directly to the client.
    """
    if request.url.path in _UNGATED_PATHS:
        return None
    status = database_health.status()
    if status.healthy:
        return None
    return _database_unavailable_response(status.detail)


def handle_operational_error(_: Request, exc: Exception) -> Response:
    """Exception handler for DB connectivity errors that escape the gate."""
    # Invalidate the cached health snapshot so the next request re-probes.
    database_health._snapshot = None  # noqa: SLF001
    return _database_unavailable_response(_short_cause(exc))


def _postgres_diag_message(exc: BaseException) -> Optional[str]:
    """Pull the primary message from a psycopg2 diagnostic, if present.

    Trigger ``RAISE EXCEPTION`` statements, CHECK constraints, and other
    user-defined validation errors land here with a clean, human-readable
    message that's far more useful than the generic SQLAlchemy wrapper.
    """
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    diag = getattr(orig, "diag", None)
    if diag is None:
        return None
    msg = getattr(diag, "message_primary", None)
    return msg.strip() if isinstance(msg, str) and msg.strip() else None


def handle_dbapi_error(_: Request, exc: sa_exc.DBAPIError) -> Response:
    """Surface Postgres validation errors (trigger RAISE, CHECK, FK, etc.)
    as a structured 422 with the actual cause, instead of a generic 500.

    Falls back to a terse 500 if we can't extract a specific cause.
    """
    primary = _postgres_diag_message(exc)
    if primary:
        body = RESTAPIError(
            error="database_validation_failed",
            error_description=primary,
        )
        return Response(content=body, status_code=422)
    # Unclassified DB error — don't pretend we know what happened.
    body = RESTAPIError(
        error="database_error",
        error_description=_short_cause(exc),
    )
    return Response(content=body, status_code=500)


def handle_http_exception(_: Request, exc: HTTPException) -> Response:
    """Preserve Litestar's default behavior for its own HTTPException."""
    body = RESTAPIError(error=exc.__class__.__name__, error_description=exc.detail)
    return Response(content=body, status_code=exc.status_code)


exception_handlers = {
    sa_exc.OperationalError: handle_operational_error,
    sa_exc.InterfaceError: handle_operational_error,
    sa_exc.DisconnectionError: handle_operational_error,
    # Catches IntegrityError, DataError, InternalError (trigger RAISE), etc.
    # Must come AFTER the connectivity-error mappings above — Litestar picks
    # the most specific match, so OperationalError still routes to its own
    # handler despite DBAPIError being its parent.
    sa_exc.DBAPIError: handle_dbapi_error,
}
