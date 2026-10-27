"""Sign-in without a password (a lab's test setup): off by default; when on,
accounts made without a password sign in with their email, and a guest
account is offered."""
from unittest.mock import MagicMock, patch

from gemini.api.user import User
from gemini.rest_api import people
from gemini.rest_api.controllers import users

LOGIN = "/api/users/login/access-token"


def _user(**kw):
    u = MagicMock(is_active=True, id="00000000-0000-0000-0000-0000000000a1", email="ana@lab.org",
                  user_info={"passwordless": True}, is_superuser=False)
    for k, v in kw.items():
        setattr(u, k, v)
    return u


def test_off_by_default(test_client):
    assert people.passwordless_enabled() is False
    assert test_client.get("/api/users/login/options").json() == {"passwordless": False, "guest": False}
    assert test_client.post("/api/users/login/guest").status_code == 403
    with patch.object(users._settings, "GEMINI_JWT_SECRET", "s3cret"), \
         patch.object(User, "authenticate", return_value=None), \
         patch.object(User, "get", return_value=_user()):
        assert test_client.post(LOGIN, json={"email": "ana@lab.org", "password": ""}).status_code == 400


def test_passwordless_account_signs_in_with_its_email(test_client):
    with patch.object(people._settings, "GEMINI_PASSWORDLESS_LOGIN", True), \
         patch.object(users._settings, "GEMINI_JWT_SECRET", "s3cret"), \
         patch.object(User, "authenticate", return_value=None), \
         patch.object(User, "get", return_value=_user()), \
         patch.object(users, "create_access_token", return_value="tok"):
        resp = test_client.post(LOGIN, json={"email": "ana@lab.org"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["access_token"]


def test_an_account_with_a_password_still_needs_it(test_client):
    with patch.object(people._settings, "GEMINI_PASSWORDLESS_LOGIN", True), \
         patch.object(users._settings, "GEMINI_JWT_SECRET", "s3cret"), \
         patch.object(User, "authenticate", return_value=None), \
         patch.object(User, "get", return_value=_user(user_info={})):
        assert test_client.post(LOGIN, json={"email": "ana@lab.org", "password": ""}).status_code == 400


def test_guest_sign_in(test_client):
    with patch.object(people._settings, "GEMINI_PASSWORDLESS_LOGIN", True), \
         patch.object(users._settings, "GEMINI_JWT_SECRET", "s3cret"), \
         patch.object(people, "guest_user", return_value=_user(email=people.GUEST_EMAIL)), \
         patch.object(users, "create_access_token", return_value="tok"):
        assert test_client.get("/api/users/login/options").json()["guest"] is True
        resp = test_client.post("/api/users/login/guest")
    assert resp.status_code == 201, resp.text


def test_guest_account_is_made_once_without_admin_rights():
    with patch.object(User, "get", return_value=None), \
         patch.object(User, "create", return_value=_user()) as create:
        people.guest_user()
    kw = create.call_args.kwargs
    assert kw["email"] == people.GUEST_EMAIL and kw["is_superuser"] is False
    assert kw["user_info"]["passwordless"] is True and len(kw["password"]) > 20


def test_visible_to_hides_others_private_experiments():
    pub = MagicMock(id="e1", experiment_info={})
    priv = MagicMock(id="e2", experiment_info={"visibility": "private"})
    mine = MagicMock(id="e3", experiment_info={"visibility": "private"})
    viewer = MagicMock(id="u1", is_superuser=False)
    row = MagicMock(experiment_id="e3")
    with patch("gemini.db.models.associations.UserExperimentModel.search", return_value=[row]):
        assert [e.id for e in people.visible_to([pub, priv, mine], viewer)] == ["e1", "e3"]
    assert len(people.visible_to([pub, priv, mine], MagicMock(is_superuser=True))) == 3
    assert len(people.visible_to([pub, priv, mine], None)) == 3
