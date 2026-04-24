"""
Password hashing and JWT helpers for per-user authentication.

Ports the approach used by the previous FastAPI backend: bcrypt for
password hashing (via passlib) and HS256 JWTs for access tokens. The
module is intentionally framework-agnostic — the Litestar controller
and dependency provider call these helpers directly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from gemini.config.settings import GEMINISettings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = GEMINISettings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return _pwd_context.hash(password)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Sign a JWT with the configured secret. `subject` is stored in the `sub` claim."""
    if not _settings.GEMINI_JWT_SECRET:
        raise RuntimeError(
            "GEMINI_JWT_SECRET is not configured; refusing to mint tokens."
        )
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=_settings.GEMINI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"exp": expire, "sub": str(subject)}
    return jwt.encode(
        payload,
        _settings.GEMINI_JWT_SECRET,
        algorithm=_settings.GEMINI_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode & validate a JWT. Raises jwt.PyJWTError on invalid / expired tokens."""
    if not _settings.GEMINI_JWT_SECRET:
        raise RuntimeError(
            "GEMINI_JWT_SECRET is not configured; refusing to validate tokens."
        )
    return jwt.decode(
        token,
        _settings.GEMINI_JWT_SECRET,
        algorithms=[_settings.GEMINI_JWT_ALGORITHM],
    )
