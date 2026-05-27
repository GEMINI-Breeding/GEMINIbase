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
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Transport-layer exceptions worth retrying. These cover the
# Connection-reset-by-peer / RemoteDisconnected pattern we see when the worker
# holds an idle keep-alive socket to the REST API and a router or the API
# itself drops it between requests. HTTP 4xx/5xx are NOT in this list — they
# get the existing pass-through behaviour.
_TRANSPORT_RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)
_TRANSPORT_RETRY_BACKOFFS: tuple[float, ...] = (0.5, 1.5, 4.0)


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
        # Disable HTTP keep-alive on worker requests. Uvicorn's default
        # `--timeout-keep-alive` is 5s; workers poll `/api/jobs/claim` at
        # roughly that same cadence, so the server closes the idle socket
        # right as the next poll is about to reuse it — every poll racks up
        # an ECONNRESET / RemoteDisconnected on the first attempt, retries
        # with a fresh socket, and floods the log. A fresh TCP handshake per
        # poll inside the compose network is cheap (~ms) and eliminates the
        # race entirely.
        self._session.headers["Connection"] = "close"
        self._token: str | None = None
        self._lock = threading.Lock()
        # `requests.Session` is documented as not thread-safe for
        # write operations — its underlying urllib3 PoolManager is
        # safe, but the Session's cookie jar / adapter state is not.
        # The amiga worker's upload pool calls report_progress from
        # 16 threads at once; without this lock we'd seen connection
        # pool churn and silent 2-minute gaps in the progress
        # stream. Held only across the actual `Session.request()`
        # call — not across retry backoff — so the lock window is
        # one HTTP round trip, ~50ms typical.
        self._send_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _login(self) -> str:
        url = f"{self._api_base_url}/api/users/login/access-token"
        # `_login` runs under `self._lock` (the token lock); take
        # `_send_lock` too so we don't issue the login POST while
        # another thread is mid-request on the same Session.
        with self._send_lock:
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
        resp = self._send_with_transport_retry(method, url, headers, kwargs)
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
        retry_resp = self._send_with_transport_retry(method, url, headers, kwargs)
        if retry_resp.status_code == 401:
            raise WorkerAuthError(
                "Worker request returned 401 even after refreshing the "
                "bearer token — credentials may have been revoked or the "
                "user disabled."
            )
        return retry_resp

    def _send_with_transport_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        kwargs: dict[str, Any],
    ) -> requests.Response:
        """Send a single HTTP request with bounded retry on transport errors.

        Connection resets, RemoteDisconnected, and short timeouts all surface
        as `requests.exceptions.ConnectionError` / `Timeout` /
        `ChunkedEncodingError`. These are routinely transient inside the
        docker-compose network — the keep-alive socket goes stale and the
        next write returns ECONNRESET. Without retry, terminal status PATCHes
        from workers can be silently lost, leaving jobs stuck in RUNNING.

        Bodies that are not safely rewindable (streaming uploads) get a single
        attempt only; we do not want to half-send a payload twice.
        """
        retryable_body = _is_retryable_body(kwargs)
        last_exc: BaseException | None = None
        for attempt in range(len(_TRANSPORT_RETRY_BACKOFFS) + 1):
            try:
                # See WorkerSession.__init__ — the underlying
                # requests.Session is not safe for concurrent
                # `.request()` calls. Hold the lock only across the
                # actual send (NOT across the backoff sleep below),
                # so retry waits don't block other threads.
                with self._send_lock:
                    return self._session.request(method, url, headers=headers, **kwargs)
            except _TRANSPORT_RETRY_EXCEPTIONS as exc:
                last_exc = exc
                if attempt >= len(_TRANSPORT_RETRY_BACKOFFS) or not retryable_body:
                    break
                delay = _TRANSPORT_RETRY_BACKOFFS[attempt]
                logger.warning(
                    "Worker HTTP %s %s failed on attempt %d/%d (%s); "
                    "retrying in %.1fs",
                    method,
                    url,
                    attempt + 1,
                    len(_TRANSPORT_RETRY_BACKOFFS) + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)
        assert last_exc is not None
        raise last_exc

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
