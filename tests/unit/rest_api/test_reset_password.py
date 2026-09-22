"""The no-email password reset command."""
from unittest.mock import MagicMock, patch

import pytest

from gemini.rest_api import reset_password as rp

USER = "gemini.api.user.User"


@patch(USER)
def test_sets_given_password_and_reactivates(mock_user_cls, capsys):
    user = MagicMock()
    mock_user_cls.get.return_value = user
    assert rp.main(["admin@example.com", "--password", "correct horse"]) == 0
    user.update.assert_called_once_with(password="correct horse", is_active=True)
    assert "Password reset for admin@example.com." in capsys.readouterr().out


@patch(USER)
def test_generates_and_prints_one_when_omitted(mock_user_cls, capsys):
    user = MagicMock()
    mock_user_cls.get.return_value = user
    assert rp.main(["admin@example.com"]) == 0
    generated = user.update.call_args.kwargs["password"]
    assert len(generated) >= 12
    assert generated in capsys.readouterr().out


@patch(USER)
def test_unknown_user_fails_cleanly(mock_user_cls, capsys):
    mock_user_cls.get.return_value = None
    assert rp.main(["nobody@example.com"]) == 1
    assert "No user with email" in capsys.readouterr().err


@patch(USER)
def test_rejects_short_passwords(mock_user_cls):
    mock_user_cls.get.return_value = MagicMock()
    with pytest.raises(ValueError):
        rp.reset_password("a@b.c", "short")
