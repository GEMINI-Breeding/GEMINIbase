"""POST /api/users/signup: off by default; when on, accounts start inactive."""
from unittest.mock import MagicMock, patch

from gemini.api.user import User
from gemini.rest_api.controllers import users, utils

SIGNUP = "/api/users/signup"
BODY = {"email": "new@example.com", "password": "pw-123456", "full_name": "New"}


def _created(**overrides):
    user = MagicMock()
    user.model_dump.return_value = {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": BODY["email"],
        "full_name": BODY["full_name"],
        "is_active": False,
        "is_superuser": False,
        "user_info": None,
        **overrides,
    }
    return user


def test_signup_is_disabled_by_default(test_client):
    assert users._settings.GEMINI_SIGNUP_ENABLED is False
    with patch.object(User, "create") as create:
        resp = test_client.post(SIGNUP, json=BODY)
    assert resp.status_code == 403
    assert resp.json()["error"] == "Signup disabled"
    create.assert_not_called()


def test_enabled_signup_creates_an_inactive_non_superuser(test_client):
    with patch.object(users._settings, "GEMINI_SIGNUP_ENABLED", True), \
         patch.object(User, "exists", return_value=False), \
         patch.object(User, "create", return_value=_created()) as create:
        resp = test_client.post(SIGNUP, json=BODY)
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_active"] is False
    kwargs = create.call_args.kwargs
    assert kwargs["is_active"] is False
    assert kwargs["is_superuser"] is False


def test_enabled_signup_rejects_a_taken_email(test_client):
    with patch.object(users._settings, "GEMINI_SIGNUP_ENABLED", True), \
         patch.object(User, "exists", return_value=True), \
         patch.object(User, "create") as create:
        resp = test_client.post(SIGNUP, json=BODY)
    assert resp.status_code == 400
    create.assert_not_called()


def test_unapproved_account_cannot_log_in(test_client):
    pending = MagicMock(is_active=False)
    with patch.object(users._settings, "GEMINI_JWT_SECRET", "s3cret"), \
         patch.object(User, "authenticate", return_value=pending):
        resp = test_client.post(
            "/api/users/login/access-token",
            json={"email": BODY["email"], "password": BODY["password"]},
        )
    assert resp.status_code == 400
    assert "approval" in resp.json()["error_description"]


def test_capabilities_reports_whether_signup_is_enabled():
    with patch.object(utils, "_torch_status",
                      return_value={"torch_version": None, "cuda_available": False,
                                    "mps_available": False}), \
         patch.object(utils, "_agrowstitch_status", return_value={}), \
         patch.object(utils, "_nodeodm_status", return_value={}), \
         patch.object(utils, "_workers_seen_public", return_value={}):
        controller = utils.UtilsController.__new__(utils.UtilsController)
        assert controller.capabilities.fn(controller)["signup_enabled"] is False
        with patch.object(utils._settings, "GEMINI_SIGNUP_ENABLED", True):
            assert controller.capabilities.fn(controller)["signup_enabled"] is True
