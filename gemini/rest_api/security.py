"""
Password hashing and JWT helpers for per-user authentication.

bcrypt for passwords (directly; passlib is unmaintained) and HS256 JWTs
for access tokens. Framework-agnostic — the Litestar controller and
dependency provider call these helpers directly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from gemini.config.settings import GEMINISettings

_settings = GEMINISettings()

# bcrypt refuses inputs longer than 72 bytes. Matches the behavior the old
# FastAPI backend got from passlib, which silently truncated.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


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
