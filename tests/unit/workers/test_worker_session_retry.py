"""
Unit tests for ``WorkerSession._send_with_transport_retry``.

Workers were occasionally losing terminal-status PATCHes to ECONNRESET when
their idle keep-alive sockets to the REST API were dropped between requests.
The fix adds a bounded transport-layer retry around ``requests.Session.request``
for ``ConnectionError`` / ``Timeout`` / ``ChunkedEncodingError``. These tests
pin the contract:

  * Success on the first try doesn't sleep / retry.
  * One transient error is recovered transparently.
  * Exhausted retries re-raise the *last* transport exception.
  * Non-rewindable bodies (file-like ``data=`` / ``files=``) get a single
    attempt — we never silently re-send half a streamed payload.
  * Non-retryable exceptions (e.g. plain ``RuntimeError``) propagate unchanged.

These are pure-function tests against ``WorkerSession`` with the underlying
``requests.Session`` mocked — no live HTTP, no network, no sleep > 0 because
``time.sleep`` is patched for speed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from gemini.workers.auth import (
    _TRANSPORT_RETRY_BACKOFFS,
    WorkerSession,
)


def _make_session() -> WorkerSession:
    """Build a WorkerSession with stub credentials and a pre-cached token.

    Pre-caching ``_token`` short-circuits ``_login()`` so each test can focus
    on the retry helper without mocking the auth round-trip.
    """
    s = WorkerSession(
        api_base_url="http://api.test",
        email="worker@test",
        password="x",
    )
    s._token = "cached-token"  # avoid _login() in tests
    return s


def _ok_response(status: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    return resp


def test_success_on_first_attempt_does_not_retry():
    """Happy path: one inner request call, no sleep, response returned."""
    s = _make_session()
    s._session = MagicMock()
    s._session.request.return_value = _ok_response(200)

    with patch("gemini.workers.auth.time.sleep") as sleep:
        out = s._send_with_transport_retry(
            "GET", "http://api.test/api/jobs/1", {"Authorization": "Bearer x"}, {}
        )

    assert out.status_code == 200
    assert s._session.request.call_count == 1
    sleep.assert_not_called()


def test_recovers_after_one_transient_error():
    """First call raises ConnectionError, second succeeds — we should sleep
    once with the first backoff and return the second response."""
    s = _make_session()
    s._session = MagicMock()
    s._session.request.side_effect = [
        requests.exceptions.ConnectionError("ECONNRESET"),
        _ok_response(200),
    ]

    with patch("gemini.workers.auth.time.sleep") as sleep:
        out = s._send_with_transport_retry(
            "PATCH", "http://api.test/api/jobs/1/status", {}, {"json": {"status": "COMPLETED"}}
        )

    assert out.status_code == 200
    assert s._session.request.call_count == 2
    sleep.assert_called_once_with(_TRANSPORT_RETRY_BACKOFFS[0])


def test_exhausted_retries_raises_last_exception():
    """Every attempt raises a retryable error — the last exception propagates
    and we slept for every defined backoff in order."""
    s = _make_session()
    s._session = MagicMock()
    errs = [
        requests.exceptions.ConnectionError("first"),
        requests.exceptions.Timeout("second"),
        requests.exceptions.ChunkedEncodingError("third"),
        requests.exceptions.ConnectionError("final"),
    ]
    # Sanity: the helper makes (len(backoffs) + 1) attempts total.
    assert len(errs) == len(_TRANSPORT_RETRY_BACKOFFS) + 1
    s._session.request.side_effect = errs

    with patch("gemini.workers.auth.time.sleep") as sleep:
        with pytest.raises(requests.exceptions.ConnectionError, match="final"):
            s._send_with_transport_retry(
                "POST", "http://api.test/api/jobs/1/progress", {}, {"json": {"progress": 50}}
            )

    assert s._session.request.call_count == len(errs)
    # Each retry-sleep must use the configured backoff in order.
    assert [c.args[0] for c in sleep.call_args_list] == list(_TRANSPORT_RETRY_BACKOFFS)


def test_non_rewindable_body_skips_retry():
    """A file-like ``data=`` body is not safely repeatable, so the helper
    must give up after the first transport error rather than re-send."""
    s = _make_session()
    s._session = MagicMock()
    s._session.request.side_effect = requests.exceptions.ConnectionError("oops")

    streaming_body = iter([b"chunk1", b"chunk2"])  # generator → non-rewindable

    with patch("gemini.workers.auth.time.sleep") as sleep:
        with pytest.raises(requests.exceptions.ConnectionError):
            s._send_with_transport_retry(
                "POST", "http://api.test/upload", {}, {"data": streaming_body}
            )

    assert s._session.request.call_count == 1
    sleep.assert_not_called()


def test_non_retryable_exception_propagates_immediately():
    """A plain ``RuntimeError`` is outside the retry whitelist — the helper
    must let it through untouched without sleeping or retrying."""
    s = _make_session()
    s._session = MagicMock()
    s._session.request.side_effect = RuntimeError("not a transport error")

    with patch("gemini.workers.auth.time.sleep") as sleep:
        with pytest.raises(RuntimeError, match="not a transport error"):
            s._send_with_transport_retry("GET", "http://api.test/x", {}, {})

    assert s._session.request.call_count == 1
    sleep.assert_not_called()
