"""
Unit tests for ``WorkerSession`` auth-mode handling.

With REST-API auth disabled (``GEMINI_JWT_SECRET`` empty, the documented
default) workers must still run:

  * Empty credentials → unauthenticated mode (no Authorization header),
    no crash at construction.
  * Credentials set but login answers 503 "Auth disabled" → switch to
    unauthenticated mode instead of failing every request.
  * With auth on, the 401 → refresh → retry-once behaviour is unchanged.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from gemini.workers.auth import WorkerAuthError, WorkerSession


def _resp(status: int, body: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = body or {}
    return resp


def _session(email: str = "worker@test", password: str = "x") -> WorkerSession:
    s = WorkerSession(api_base_url="http://api.test", email=email, password=password)
    s._session = MagicMock()
    return s


def _respond(s: WorkerSession, *responses: MagicMock) -> list[dict]:
    """Queue responses for ``Session.request`` (the last one repeats).

    Returns a list that receives a snapshot of the headers sent on each
    call — WorkerSession reuses and mutates one headers dict across the
    401 retry, so the mock's own call_args would only show the final state.
    """
    sent: list[dict] = []
    queue = list(responses)

    def _request(method, url, headers=None, **kwargs):
        sent.append(dict(headers or {}))
        return queue.pop(0) if len(queue) > 1 else queue[0]

    s._session.request.side_effect = _request
    return sent


def test_empty_credentials_do_not_raise_and_send_no_auth_header():
    s = _session(email="", password="")
    sent = _respond(s, _resp(200))

    resp = s.get("/api/jobs/1")

    assert resp.status_code == 200
    s._session.post.assert_not_called()  # never attempted a login
    assert "Authorization" not in sent[-1]


def test_empty_credentials_401_raises_clear_error():
    s = _session(email="", password="")
    sent = _respond(s, _resp(401))

    with pytest.raises(WorkerAuthError, match="credentials are missing"):
        s.get("/api/jobs/1")


def test_login_503_switches_to_unauthenticated_mode():
    s = _session()
    s._session.post.return_value = _resp(
        503, {"error": "Auth disabled", "error_description": "GEMINI_JWT_SECRET is unset"}
    )
    sent = _respond(s, _resp(200))

    assert s.get("/api/jobs/1").status_code == 200
    assert s.get("/api/jobs/2").status_code == 200

    # Logged in only once; subsequent requests don't retry the login.
    assert s._session.post.call_count == 1
    assert "Authorization" not in sent[0]
    assert "Authorization" not in sent[1]


def test_login_success_sends_bearer_token():
    s = _session()
    s._session.post.return_value = _resp(200, {"access_token": "tok-1"})
    sent = _respond(s, _resp(200))

    s.get("/api/jobs/1")

    assert sent[-1]["Authorization"] == "Bearer tok-1"


def test_401_refreshes_token_and_retries_once():
    s = _session()
    s._session.post.side_effect = [
        _resp(200, {"access_token": "tok-old"}),
        _resp(200, {"access_token": "tok-new"}),
    ]
    sent = _respond(s, _resp(401), _resp(200))

    resp = s.get("/api/jobs/1")

    assert resp.status_code == 200
    assert s._session.post.call_count == 2
    assert sent[0]["Authorization"] == "Bearer tok-old"
    assert sent[1]["Authorization"] == "Bearer tok-new"


def test_persistent_401_after_refresh_raises():
    s = _session()
    s._session.post.return_value = _resp(200, {"access_token": "tok"})
    sent = _respond(s, _resp(401))

    with pytest.raises(WorkerAuthError):
        s.get("/api/jobs/1")


def test_unauthenticated_after_503_reauthenticates_on_401():
    """If auth gets enabled server-side after we went unauthenticated,
    a 401 triggers a fresh login and the request is retried with a token."""
    s = _session()
    s._session.post.side_effect = [
        _resp(503, {"error": "Auth disabled"}),
        _resp(200, {"access_token": "tok"}),
    ]
    sent = _respond(s, _resp(401), _resp(200))

    assert s.get("/api/jobs/1").status_code == 200
    assert "Authorization" not in sent[0]
    assert sent[1]["Authorization"] == "Bearer tok"


def test_login_other_error_still_raises():
    s = _session()
    s._session.post.return_value = _resp(400, {"error_description": "Incorrect email or password."})

    with pytest.raises(WorkerAuthError, match="400"):
        s.get("/api/jobs/1")
