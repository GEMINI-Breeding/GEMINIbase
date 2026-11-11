"""Saved keys never travel in a user record (only via /users/me/credentials)."""
from gemini.rest_api.models import UserOutput


def test_user_output_hides_credentials():
    out = UserOutput.model_validate(
        {"email": "a@b.c", "user_info": {"theme": "dark", "credentials": {"hf_token": "hf_x"}}}
    )
    assert out.user_info == {"theme": "dark"}


def test_user_output_without_credentials_is_unchanged():
    out = UserOutput.model_validate({"email": "a@b.c", "user_info": {"theme": "dark"}})
    assert out.user_info == {"theme": "dark"}
