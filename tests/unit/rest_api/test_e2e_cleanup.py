"""DELETE /api/e2e_cleanup — prefix must be matched literally."""
from unittest.mock import MagicMock, patch

import pytest
from litestar.exceptions import HTTPException

from gemini.rest_api.controllers.e2e_cleanup import _like_prefix

MOD = "gemini.rest_api.controllers.e2e_cleanup"


class TestLikePrefix:
    def test_plain_prefix(self):
        assert _like_prefix("E2E-foo-123") == "E2E-foo-123%"

    def test_wildcards_are_escaped(self):
        assert _like_prefix("%%%%") == "\\%\\%\\%\\%%"
        assert _like_prefix("E2E_x") == "E2E\\_x%"

    def test_backslash_is_escaped(self):
        assert _like_prefix("a\\b_") == "a\\\\b\\_%"


def test_wildcard_prefix_matches_literally(test_client, monkeypatch):
    monkeypatch.setenv("GEMINI_E2E_CLEANUP_ENABLED", "1")
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    session.execute.return_value.rowcount = 0
    engine = MagicMock()
    engine.get_session.return_value.__enter__.return_value = session
    with patch(f"{MOD}.db_engine", engine):
        res = test_client.delete("/api/e2e_cleanup", params={"prefix": "%%%%"})
    assert res.status_code == 200, res.text
    sql = [str(c.args[0].compile()) for c in session.execute.call_args_list]
    params = [c.args[0].compile().params for c in session.execute.call_args_list[:4]]
    # Every ORM LIKE carries the ESCAPE clause and the escaped pattern.
    for stmt in sql[:4]:
        assert "ESCAPE" in stmt
    for p in params:
        assert "\\%\\%\\%\\%%" in p.values()
    # Raw-SQL workspace sweep too.
    raw = session.execute.call_args_list[4]
    assert "ESCAPE" in str(raw.args[0])
    assert raw.args[1] == {"p": "\\%\\%\\%\\%%"}


def test_superuser_gate_is_noop_when_auth_disabled():
    from gemini.rest_api import dependencies

    assert dependencies.provide_superuser(MagicMock()) is None


def test_superuser_gate_enforced_when_auth_enabled(monkeypatch):
    from gemini.rest_api import dependencies

    monkeypatch.setattr(dependencies._settings, "GEMINI_JWT_SECRET", "s3cret")
    user = MagicMock(is_superuser=False)
    with patch.object(dependencies, "require_current_user", return_value=user):
        with pytest.raises(HTTPException) as exc:
            dependencies.provide_superuser(MagicMock())
    assert exc.value.status_code == 403
    user.is_superuser = True
    with patch.object(dependencies, "require_current_user", return_value=user):
        assert dependencies.provide_superuser(MagicMock()) is user
