"""
Shared Litestar dependencies for the GEMINIbase REST API.

`provide_current_user` resolves the requesting user from the Authorization
bearer token; handlers that list it as a dependency receive the `User` API
instance. When `GEMINI_JWT_SECRET` is empty (auth disabled), the dependency
returns `None` so handlers can decide whether to require a user or not.
"""
from __future__ import annotations

from typing import Optional

import jwt
from litestar.connection import Request
from litestar.exceptions import HTTPException

from gemini.api.user import User
from gemini.config.settings import GEMINISettings
from gemini.rest_api.security import decode_access_token

_settings = GEMINISettings()


def _extract_bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def provide_current_user(request: Request) -> Optional[User]:
    """Resolve the current user from the bearer token, or None if auth is disabled.

    Raises 401 when auth is enabled but the token is missing/invalid/expired, or
    the user is inactive. Raises 404 if the token is well-formed but the user
    was deleted.
    """
    if not _settings.GEMINI_JWT_SECRET:
        return None

    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Token missing subject.")

    user = User.get_by_id(subject)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user.")
    return user


def require_current_user(request: Request) -> User:
    """Same as `provide_current_user`, but raises 503 if auth is disabled."""
    user = provide_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=503,
            detail="Per-user auth is disabled (GEMINI_JWT_SECRET is unset).",
        )
    return user


def require_superuser(request: Request) -> User:
    user = require_current_user(request)
    if not user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges."
        )
    return user
