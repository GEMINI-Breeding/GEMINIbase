"""
Worker → REST-API authentication.

The REST API enforces a JWT bearer-token guard on every /api/* path
outside a tiny open whitelist (login, signup, health-check, etc.).
Workers run inside the docker network and have no human user to
attribute their requests to, so they sign in at startup as the
bootstrap superuser using credentials provided via env, cache the
token, and refresh it on 401.

The same `WorkerSession` is used by every BaseWorker subclass — it's a
thin wrapper around `requests.Session` that injects an `Authorization:
Bearer …` header and re-authenticates transparently when the token
expires or is rejected.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

import requests

logger = logging.getLogger(__name__)


class WorkerAuthError(RuntimeError):
    """Raised when worker credentials are missing or rejected."""


def _is_retryable_body(kwargs: dict[str, Any]) -> bool:
    """Return True iff `kwargs` describes a body we can safely re-send.

    `requests` reads file-like `data=` / `files=` arguments as a stream, so
    sending the same kwargs twice transmits an empty body the second time.
    JSON / form-dict / bytes / str payloads, plus the no-body case, are all
    safe to repeat.
    """
    data = kwargs.get("data")
    if data is not None and not isinstance(data, (bytes, str, dict, list, tuple)):
        return False
    files = kwargs.get("files")
    if files:
        return False
    return True


class WorkerSession:
    """
    Thread-safe bearer-token HTTP session for workers.

    On the first request (or after a 401) it logs in via the REST API's
    `/api/users/login/access-token` endpoint using the env-provided
    superuser credentials. The token is cached and reused until the next
    401, at which point it's refreshed and the original request is
    retried exactly once.
    """

    def __init__(
        self,
        api_base_url: str,
        email: str,
        password: str,
        timeout: float = 10.0,
    ) -> None:
        if not email or not password:
            raise WorkerAuthError(
                "Worker login credentials are missing. Set "
                "GEMINI_FIRST_SUPERUSER_EMAIL and "
                "GEMINI_FIRST_SUPERUSER_PASSWORD on the worker container."
            )
        self._api_base_url = api_base_url.rstrip("/")
        self._email = email
        self._password = password
        self._timeout = timeout
        self._session = requests.Session()
        self._token: str | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _login(self) -> str:
        url = f"{self._api_base_url}/api/users/login/access-token"
        resp = self._session.post(
            url,
            json={"email": self._email, "password": self._password},
            timeout=self._timeout,
        )
        if resp.status_code >= 400:
            # The REST API returns RESTAPIError {error, error_description}
            # on failure. Pull the structured description rather than
            # dumping arbitrary response text — keeps any unexpected echo
            # of the submitted credentials out of worker logs.
            description = ""
            try:
                description = resp.json().get("error_description", "") or ""
            except ValueError:
                pass
            raise WorkerAuthError(
                f"Worker login failed ({resp.status_code}): {description or '<no detail>'}"
            )
        token = resp.json().get("access_token")
        if not token:
            raise WorkerAuthError("Worker login response missing access_token.")
        return token

    def _ensure_token(self) -> str:
        with self._lock:
            if self._token is None:
                self._token = self._login()
                logger.info("Worker authenticated as %s.", self._email)
            return self._token

    def _refresh_token(self, stale_token: str) -> str:
        """Re-login only if `self._token` still matches `stale_token`.

        Multiple threads hitting a 401 simultaneously would otherwise each
        force a fresh login. Double-check inside the lock so the second
        and later threads adopt the token the first one already minted.
        """
        with self._lock:
            if self._token is not None and self._token != stale_token:
                return self._token
            self._token = self._login()
            logger.info("Worker token refreshed for %s.", self._email)
            return self._token

    # ------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Send an authenticated request. Refreshes the token on 401 and retries once.

        Two failure modes worth knowing about:

        1. **Non-rewindable bodies on retry.** If the caller passes a streaming
           body (`data=<file-like>`, `files={"f": <file>}`), the first request
           consumes the iterator. We reject the retry instead of silently
           re-sending an empty body, since `requests` won't seek a generic
           file-like for us. JSON / form / bytes / str bodies are safe to
           retry.

        2. **Persistent 401.** If the refresh succeeds but the second request
           also returns 401 (e.g. the worker's user got disabled mid-job),
           we raise `WorkerAuthError` instead of returning the 401. Several
           callsites in BaseWorker treat non-2xx as "log a warning and keep
           polling," which would otherwise turn a permanently-401'd worker
           into a silent no-op poll loop with no alarm.
        """
        url = path if path.startswith("http") else f"{self._api_base_url}{path}"
        kwargs.setdefault("timeout", self._timeout)

        headers = dict(kwargs.pop("headers", {}) or {})
        token = self._ensure_token()
        headers["Authorization"] = f"Bearer {token}"
        resp = self._session.request(method, url, headers=headers, **kwargs)
        if resp.status_code != 401:
            return resp

        # Refuse retry for body shapes we can't safely rewind. Today no
        # worker callsite sends streaming bodies; this guard exists so the
        # day someone adds a chunked upload through WorkerSession they get
        # a clear error instead of a silent half-send.
        if not _is_retryable_body(kwargs):
            raise WorkerAuthError(
                "Worker request returned 401 but the body is not safely "
                "retryable (streaming/file-like). Refusing to re-send."
            )

        # One-shot refresh-and-retry on 401 (token expired or revoked).
        headers["Authorization"] = f"Bearer {self._refresh_token(token)}"
        retry_resp = self._session.request(method, url, headers=headers, **kwargs)
        if retry_resp.status_code == 401:
            raise WorkerAuthError(
                "Worker request returned 401 even after refreshing the "
                "bearer token — credentials may have been revoked or the "
                "user disabled."
            )
        return retry_resp

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, **kwargs)


def session_from_env(api_base_url: str | None = None) -> WorkerSession:
    """Build a WorkerSession from the standard worker env vars."""
    base = api_base_url or os.environ.get(
        "GEMINI_REST_API_URL", "http://geminibase-rest-api:7777"
    )
    email = os.environ.get("GEMINI_FIRST_SUPERUSER_EMAIL", "")
    password = os.environ.get("GEMINI_FIRST_SUPERUSER_PASSWORD", "")
    return WorkerSession(api_base_url=base, email=email, password=password)
