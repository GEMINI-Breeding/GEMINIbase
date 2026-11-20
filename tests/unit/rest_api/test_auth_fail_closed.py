"""An empty GEMINI_JWT_SECRET must not silently open every endpoint.

Auth is only off when the operator opts out explicitly with
GEMINI_AUTH_DISABLED=true. Otherwise a missing secret is a
misconfiguration and protected routes answer 503 instead of serving data.
"""
from unittest.mock import MagicMock

import pytest
from litestar.exceptions import HTTPException

from gemini.manager import GEMINIManager
from gemini.rest_api import dependencies, guards


def _configure(monkeypatch, module, *, secret: str, disabled: bool) -> None:
    # Write straight into the model's __dict__ so the override works whether
    # or not the field is declared, and is undone after the test.
    monkeypatch.setitem(module._settings.__dict__, "GEMINI_JWT_SECRET", secret)
    monkeypatch.setitem(module._settings.__dict__, "GEMINI_AUTH_DISABLED", disabled)


def _connection(path: str) -> MagicMock:
    conn = MagicMock()
    conn.scope = {"path": path}
    conn.headers = {}
    conn.query_params = {}
    return conn


class TestGuard:
    def test_rejects_when_secret_missing_and_not_opted_out(self, monkeypatch):
        _configure(monkeypatch, guards, secret="", disabled=False)
        with pytest.raises(HTTPException) as exc:
            guards.authenticated_guard(_connection("/api/experiment/all"), MagicMock())
        assert exc.value.status_code == 503

    def test_open_paths_stay_open_when_unconfigured(self, monkeypatch):
        _configure(monkeypatch, guards, secret="", disabled=False)
        assert guards.authenticated_guard(
            _connection("/api/utils/health-check"), MagicMock()
        ) is None

    def test_explicit_opt_out_disables_guard(self, monkeypatch):
        _configure(monkeypatch, guards, secret="", disabled=True)
        assert guards.authenticated_guard(
            _connection("/api/experiment/all"), MagicMock()
        ) is None


class TestSuperuserDependency:
    def test_rejects_when_secret_missing_and_not_opted_out(self, monkeypatch):
        _configure(monkeypatch, dependencies, secret="", disabled=False)
        with pytest.raises(HTTPException) as exc:
            dependencies.provide_superuser(MagicMock())
        assert exc.value.status_code == 503

    def test_explicit_opt_out_returns_none(self, monkeypatch):
        _configure(monkeypatch, dependencies, secret="", disabled=True)
        assert dependencies.provide_superuser(MagicMock()) is None


class TestSaveSettings:
    def test_generates_jwt_secret_when_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_JWT_SECRET", "")
        monkeypatch.setenv("GEMINI_AUTH_DISABLED", "false")
        env_file = tmp_path / ".env"
        GEMINIManager(env_file_path=str(env_file)).save_settings()
        lines = dict(
            line.split("=", 1) for line in env_file.read_text().splitlines() if "=" in line
        )
        assert len(lines.get("GEMINI_JWT_SECRET", "")) >= 32

    def test_keeps_existing_secret(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_JWT_SECRET", "already-set-secret")
        env_file = tmp_path / ".env"
        GEMINIManager(env_file_path=str(env_file)).save_settings()
        assert "GEMINI_JWT_SECRET=already-set-secret\n" in env_file.read_text()

    def test_no_secret_generated_when_opted_out(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_JWT_SECRET", "")
        monkeypatch.setenv("GEMINI_AUTH_DISABLED", "true")
        env_file = tmp_path / ".env"
        GEMINIManager(env_file_path=str(env_file)).save_settings()
        assert "GEMINI_JWT_SECRET=\n" in env_file.read_text()
