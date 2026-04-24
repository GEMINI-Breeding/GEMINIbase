"""
Guards that enforce per-user authentication across controller routers.

Unlike the existing ``APIKeyAuthMiddleware`` (a shared-secret admission
gate), this guard validates a bearer token against ``GEMINI_JWT_SECRET``
and confirms the referenced user is active. It activates only when the
JWT secret is configured — when it's empty the guard is a no-op and the
stack behaves exactly as it did before auth was introduced.

A small whitelist of paths is always open, so fresh clients can log in
or check health without a token.
"""
from __future__ import annotations

import jwt
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.handlers.base import BaseRouteHandler

from gemini.api.user import User
from gemini.config.settings import GEMINISettings
from gemini.rest_api.security import decode_access_token

_settings = GEMINISettings()

# Paths that must stay open for unauthenticated callers. Everything else
# under /api/* requires a bearer token once GEMINI_JWT_SECRET is set.
_OPEN_PATHS = {
    "/api/users/login/access-token",
    "/api/users/signup",
    "/api/utils/health-check",
    "/api/utils/capabilities",
    "/api/utils/docker-check",
}


def _extract_bearer_token(connection: ASGIConnection) -> str | None:
    header = connection.headers.get("authorization") or connection.headers.get(
        "Authorization"
    )
    if header:
        parts = header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    # Fallback: `?token=...` query parameter. WebSocket clients in the
    # browser cannot set custom request headers, so the only place they
    # can pass the JWT is on the URL. We accept the same claim here; the
    # signature check downstream prevents random strings from passing.
    qs_token = connection.query_params.get("token")
    if isinstance(qs_token, str) and qs_token:
        return qs_token
    return None


def authenticated_guard(
    connection: ASGIConnection, _handler: BaseRouteHandler
) -> None:
    """Require a valid bearer token when auth is enabled."""
    if not _settings.GEMINI_JWT_SECRET:
        return
    path = connection.scope.get("path", "")
    if path in _OPEN_PATHS:
        return

    token = _extract_bearer_token(connection)
    if not token:
        raise NotAuthorizedException(detail="Missing bearer token.")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise NotAuthorizedException(detail="Token expired.")
    except jwt.PyJWTError:
        raise NotAuthorizedException(detail="Invalid token.")

    subject = payload.get("sub")
    if not subject:
        raise NotAuthorizedException(detail="Token missing subject.")

    user = User.get_by_id(subject)
    if user is None:
        raise NotFoundException(detail="User not found.")
    if not user.is_active:
        raise NotAuthorizedException(detail="Inactive user.")
