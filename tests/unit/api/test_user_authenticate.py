"""Tests for gemini.api.user.User.authenticate."""
import logging
from unittest.mock import MagicMock, patch

from gemini.api.user import User
from gemini.rest_api.security import get_password_hash

MODULE = "gemini.api.user"


class TestAuthenticateUnknownUser:
    @patch(f"{MODULE}.verify_password")
    @patch(f"{MODULE}.UserModel")
    def test_still_runs_a_bcrypt_compare(self, model, verify, caplog):
        # The compare against the dummy hash equalizes response time with a
        # wrong password, so "does this email exist?" can't be timed.
        model.get_by_parameters.return_value = None
        verify.return_value = False
        with caplog.at_level(logging.ERROR, logger=MODULE):
            assert User.authenticate("nobody@example.com", "pw") is None
        verify.assert_called_once()
        password, hashed = verify.call_args.args
        assert password == "pw"
        assert isinstance(hashed, str) and hashed.startswith("$2b$12$")
        assert caplog.records == []

    @patch(f"{MODULE}.UserModel")
    def test_dummy_hash_is_a_real_bcrypt_hash(self, model):
        # A malformed hash makes bcrypt fail fast, which defeats the point.
        from gemini.api.user import _DUMMY_HASH
        import bcrypt

        assert bcrypt.checkpw(b"anything", _DUMMY_HASH.encode()) is False


class TestAuthenticateKnownUser:
    @patch(f"{MODULE}.UserModel")
    def test_wrong_password(self, model):
        db = MagicMock(hashed_password=get_password_hash("right"))
        model.get_by_parameters.return_value = db
        assert User.authenticate("a@b.c", "wrong") is None
