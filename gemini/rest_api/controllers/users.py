"""
Users / auth controller.

Provides:
- /login/access-token         POST  — exchange email+password for a JWT
- /login/test-token           POST  — return the caller identified by the token
- /signup                     POST  — self-registration (off unless GEMINI_SIGNUP_ENABLED;
                                      accounts start inactive until a superuser approves)
- /me                         GET   — get current user
- /me                         PATCH — update current user
- /me/password                PATCH — change own password
- /me/experiments             GET   — list experiment ids associated with current user
- /me/experiments             POST  — associate an experiment with the current user
- /me/experiments/{id}        DELETE — remove an experiment association from current user
- /all                        GET   — list all users (superuser only)
- /                           GET   — search users (superuser only)
- /                           POST  — create a user (superuser only)
- /id/{user_id}               GET   — get a user by id (self or superuser)
- /id/{user_id}               PATCH — update a user (superuser only)
- /id/{user_id}               DELETE — delete a user (superuser only)
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated, List, Optional

from litestar import Response
from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers import delete, get, patch, post
from litestar.params import Body

from gemini.api.user import User
from gemini.config.settings import GEMINISettings
from gemini.rest_api.dependencies import (
    require_current_user,
    require_superuser,
)
from gemini.rest_api.models import (
    JSONB,
    LoginInput,
    MessageOutput,
    RESTAPIError,
    Token,
    UpdatePassword,
    UserExperimentInput,
    UserInput,
    UserOutput,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
    str_to_dict,
)
from gemini.rest_api.security import create_access_token, verify_password

logger = logging.getLogger(__name__)
_settings = GEMINISettings()


from gemini.rest_api import people  # noqa: E402

class UsersController(Controller):

    dependencies = {
        "current_user": Provide(require_current_user, sync_to_thread=True),
        "superuser": Provide(require_superuser, sync_to_thread=True),
    }

    # --------------------------------------------------------------
    # Login / token issuance
    # --------------------------------------------------------------

    @post(path="/login/access-token", sync_to_thread=True)
    def login_access_token(self, data: Annotated[LoginInput, Body]) -> Token:
        """OAuth2-style password grant: email+password → JWT."""
        try:
            if not _settings.GEMINI_JWT_SECRET:
                error = RESTAPIError(
                    error="Auth disabled",
                    error_description="GEMINI_JWT_SECRET is unset; per-user auth is disabled.",
                )
                return Response(content=error, status_code=503)
            user = User.authenticate(email=data.email, password=data.password)
            if user is None and people.passwordless_enabled() and not data.password:
                # An account made without a password (a lab's test setup): its email is enough.
                candidate = User.get(email=data.email.strip())
                user = candidate if candidate is not None and people.is_passwordless(candidate) else None
            if user is None:
                error = RESTAPIError(
                    error="Invalid credentials",
                    error_description="Incorrect email or password.",
                )
                return Response(content=error, status_code=400)
            if not user.is_active:
                error = RESTAPIError(
                    error="Inactive user",
                    error_description="This account is inactive or awaiting administrator approval.",
                )
                return Response(content=error, status_code=400)
            expires = timedelta(minutes=_settings.GEMINI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(subject=user.id, expires_delta=expires)
            return Token(access_token=token)
        except Exception:
            logger.exception("Login failed with unexpected error")
            error = RESTAPIError(
                error="Login failed",
                error_description="An internal error occurred during login.",
            )
            return Response(content=error, status_code=500)

    @get(path="/login/options", sync_to_thread=True)
    def login_options(self) -> dict:
        """What the sign-in page offers (no sign-in needed to ask)."""
        on = people.passwordless_enabled()
        return {"passwordless": on, "guest": on}

    @post(path="/login/guest", sync_to_thread=True)
    def login_guest(self) -> Token:
        """Sign in to the shared guest account (only with GEMINI_PASSWORDLESS_LOGIN)."""
        if not people.passwordless_enabled() or not _settings.GEMINI_JWT_SECRET:
            error = RESTAPIError(error="Guest sign-in disabled",
                                 error_description="Ask an administrator for an account.")
            return Response(content=error, status_code=403)
        user = people.guest_user()
        if user is None or not user.is_active:
            error = RESTAPIError(error="Guest sign-in failed", error_description="The guest account is unavailable.")
            return Response(content=error, status_code=500)
        expires = timedelta(minutes=_settings.GEMINI_JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        return Token(access_token=create_access_token(subject=user.id, expires_delta=expires))

    @get(path="/people", sync_to_thread=True)
    def list_people(self, current_user: User) -> list[dict]:
        """Everyone with an account and the experiments they are linked to (any signed-in user)."""
        from gemini.db.models.associations import UserExperimentModel
        from gemini.db.models.users import UserModel

        links: dict[str, list[dict]] = {}
        for row in UserExperimentModel.search():
            links.setdefault(str(row.user_id), []).append(
                {"experiment_id": str(row.experiment_id), "role": row.role or "member"})
        return [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "is_superuser": bool(u.is_superuser),
                 "is_active": bool(u.is_active), "passwordless": people.is_passwordless(u),
                 "guest": u.email == people.GUEST_EMAIL, "experiments": links.get(str(u.id), [])}
                for u in sorted(UserModel.search(), key=lambda u: u.email)]

    @post(path="/login/test-token", sync_to_thread=True)
    def test_token(self, current_user: User) -> UserOutput:
        return UserOutput.model_validate(current_user.model_dump())

    # --------------------------------------------------------------
    # Self-service (authenticated user)
    # --------------------------------------------------------------

    @get(path="/me", sync_to_thread=True)
    def read_me(self, current_user: User) -> UserOutput:
        return UserOutput.model_validate(current_user.model_dump())

    @patch(path="/me", sync_to_thread=True)
    def update_me(
        self,
        current_user: User,
        data: Annotated[UserUpdateMe, Body],
    ) -> UserOutput:
        try:
            user_info = (
                str_to_dict(data.user_info) if data.user_info is not None else None
            )
            updated = current_user.update(
                email=data.email,
                full_name=data.full_name,
                user_info=user_info,
            )
            if updated is None:
                error = RESTAPIError(
                    error="User not updated",
                    error_description="No update parameters provided, or update failed.",
                )
                return Response(content=error, status_code=400)
            return UserOutput.model_validate(updated.model_dump())
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the current user.",
            )
            return Response(content=error, status_code=500)

    @patch(path="/me/password", sync_to_thread=True)
    def update_me_password(
        self,
        current_user: User,
        data: Annotated[UpdatePassword, Body],
    ) -> MessageOutput:
        try:
            if not verify_password(data.current_password, current_user.hashed_password):
                error = RESTAPIError(
                    error="Incorrect password",
                    error_description="The current password is incorrect.",
                )
                return Response(content=error, status_code=400)
            if data.current_password == data.new_password:
                error = RESTAPIError(
                    error="Password unchanged",
                    error_description="New password cannot be the same as the current one.",
                )
                return Response(content=error, status_code=400)
            updated = current_user.update(password=data.new_password)
            if updated is None:
                error = RESTAPIError(
                    error="Password not updated",
                    error_description="The password could not be updated.",
                )
                return Response(content=error, status_code=500)
            return MessageOutput(message="Password updated successfully.")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the password.",
            )
            return Response(content=error, status_code=500)

    @get(path="/me/experiments", sync_to_thread=True)
    def list_my_experiments(self, current_user: User) -> List[str]:
        experiments = current_user.get_associated_experiments()
        return [str(e) for e in (experiments or [])]

    @post(path="/me/experiments", sync_to_thread=True)
    def associate_my_experiment(
        self,
        current_user: User,
        data: Annotated[UserExperimentInput, Body],
    ) -> MessageOutput:
        try:
            from gemini.api.experiment import Experiment

            experiment = Experiment.get_by_id(id=data.experiment_id)
            if experiment is None:
                return Response(content=RESTAPIError(error="Experiment not found",
                                                     error_description="No experiment with that ID."),
                                status_code=404)
            if people.belongs_to(str(experiment.id), current_user) and not current_user.is_superuser:
                return MessageOutput(message="Already associated.")
            refusal = people.self_link_refusal(experiment, current_user, data.role)
            if refusal:
                return Response(content=RESTAPIError(error="Not allowed", error_description=refusal),
                                status_code=403)
            info = str_to_dict(data.info) if data.info is not None else None
            ok = current_user.associate_experiment(
                experiment_id=data.experiment_id,
                role=data.role if current_user.is_superuser else (data.role or "member"),
                info=info,
            )
            if not ok:
                error = RESTAPIError(
                    error="Association failed",
                    error_description="Could not associate the experiment with the current user.",
                )
                return Response(content=error, status_code=500)
            return MessageOutput(message="Experiment associated.")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while associating the experiment.",
            )
            return Response(content=error, status_code=500)

    @post(path="/id/{user_id:str}/experiments", sync_to_thread=True)
    def associate_user_experiment(
        self,
        current_user: User,
        user_id: str,
        data: Annotated[UserExperimentInput, Body],
    ) -> MessageOutput:
        """Add someone to an experiment (member, or owner): its owner or an administrator."""
        role = data.role or "member"
        if role not in people.ROLES:
            return Response(content=RESTAPIError(error="Bad role", error_description="member or owner"),
                            status_code=400)
        if not people.is_owner(data.experiment_id, current_user):
            return Response(content=RESTAPIError(
                error="Not the owner",
                error_description="Only the experiment's owner (or an administrator) adds people to it."),
                status_code=403)
        person = User.get_by_id(id=user_id)
        if person is None:
            return Response(content=RESTAPIError(error="User not found", error_description="No such account."),
                            status_code=404)
        if not person.associate_experiment(experiment_id=data.experiment_id, role=role):
            return Response(content=RESTAPIError(error="Association failed",
                                                 error_description="Could not add the person to the experiment."),
                            status_code=500)
        return MessageOutput(message=f"Added as {role}.")

    @delete(path="/me/experiments/{experiment_id:str}", sync_to_thread=True, status_code=200)
    def unassociate_my_experiment(
        self, current_user: User, experiment_id: str
    ) -> MessageOutput:
        ok = current_user.unassociate_experiment(experiment_id=experiment_id)
        if not ok:
            return MessageOutput(message="Association did not exist.")
        return MessageOutput(message="Experiment unassociated.")

    # --------------------------------------------------------------
    # Self-registration (no auth required)
    # --------------------------------------------------------------

    @post(path="/signup", sync_to_thread=True)
    def signup(self, data: Annotated[UserRegister, Body]) -> UserOutput:
        # Off by default: an open signup would hand every authenticated
        # permission to anyone who can reach the API. When enabled, the new
        # account is inactive until a superuser sets is_active=true.
        if not _settings.GEMINI_SIGNUP_ENABLED:
            error = RESTAPIError(
                error="Signup disabled",
                error_description="Self-registration is disabled. Ask an administrator for an account.",
            )
            return Response(content=error, status_code=403)
        try:
            if User.exists(email=data.email):
                error = RESTAPIError(
                    error="Email taken",
                    error_description="A user with this email already exists.",
                )
                return Response(content=error, status_code=400)
            user = User.create(
                email=data.email,
                password=data.password,
                full_name=data.full_name,
                is_active=False,
                is_superuser=False,
            )
            if user is None:
                error = RESTAPIError(
                    error="User not created",
                    error_description="The user could not be created.",
                )
                return Response(content=error, status_code=500)
            return UserOutput.model_validate(user.model_dump())
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred during signup.",
            )
            return Response(content=error, status_code=500)

    # --------------------------------------------------------------
    # Admin endpoints (superuser only)
    # --------------------------------------------------------------

    @get(path="/all", sync_to_thread=True)
    def get_all_users(
        self, superuser: User, limit: int = 100, offset: int = 0
    ) -> List[UserOutput]:
        try:
            users = User.get_all(limit=limit, offset=offset) or []
            return [UserOutput.model_validate(u.model_dump()) for u in users]
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all users.",
            )
            return Response(content=error, status_code=500)

    @get(sync_to_thread=True)
    def search_users(
        self,
        superuser: User,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        user_info: Optional[JSONB] = None,
    ) -> List[UserOutput]:
        try:
            if user_info is not None:
                user_info = str_to_dict(user_info)
            users = User.search(
                email=email,
                full_name=full_name,
                is_active=is_active,
                is_superuser=is_superuser,
                user_info=user_info,
            ) or []
            return [UserOutput.model_validate(u.model_dump()) for u in users]
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while searching users.",
            )
            return Response(content=error, status_code=500)

    @post(sync_to_thread=True)
    def create_user(
        self,
        superuser: User,
        data: Annotated[UserInput, Body],
    ) -> UserOutput:
        try:
            user_info = (
                str_to_dict(data.user_info) if data.user_info is not None else None
            )
            password = data.password
            if not password:
                if not people.passwordless_enabled():
                    error = RESTAPIError(error="Password needed",
                                         error_description="Accounts without a password are turned off "
                                                           "(GEMINI_PASSWORDLESS_LOGIN).")
                    return Response(content=error, status_code=400)
                password = people.random_password()
                user_info = {**(user_info or {}), "passwordless": True}
            user = User.create(
                email=data.email.strip(),
                password=password,
                full_name=data.full_name,
                is_active=data.is_active if data.is_active is not None else True,
                is_superuser=data.is_superuser if data.is_superuser is not None else False,
                user_info=user_info,
            )
            if user is None:
                error = RESTAPIError(
                    error="User not created",
                    error_description="The user could not be created (email may be taken).",
                )
                return Response(content=error, status_code=400)
            return UserOutput.model_validate(user.model_dump())
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the user.",
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{user_id:str}", sync_to_thread=True)
    def get_user_by_id(
        self, current_user: User, user_id: str
    ) -> UserOutput:
        try:
            user = User.get_by_id(id=user_id)
            if user is None:
                error = RESTAPIError(
                    error="User not found",
                    error_description="The user with the given ID was not found.",
                )
                return Response(content=error, status_code=404)
            if str(current_user.id) != str(user.id) and not current_user.is_superuser:
                error = RESTAPIError(
                    error="Forbidden",
                    error_description="The user doesn't have enough privileges.",
                )
                return Response(content=error, status_code=403)
            return UserOutput.model_validate(user.model_dump())
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the user.",
            )
            return Response(content=error, status_code=500)

    @patch(path="/id/{user_id:str}", sync_to_thread=True)
    def update_user(
        self,
        superuser: User,
        user_id: str,
        data: Annotated[UserUpdate, Body],
    ) -> UserOutput:
        try:
            user = User.get_by_id(id=user_id)
            if user is None:
                error = RESTAPIError(
                    error="User not found",
                    error_description="The user with the given ID was not found.",
                )
                return Response(content=error, status_code=404)
            # Guard against a superuser locking themselves (or the system) out:
            # block the caller from removing their own superuser role or
            # deactivating their own account.
            if str(user.id) == str(superuser.id):
                if data.is_superuser is False:
                    error = RESTAPIError(
                        error="Self-demotion blocked",
                        error_description="A superuser cannot remove their own superuser role.",
                    )
                    return Response(content=error, status_code=403)
                if data.is_active is False:
                    error = RESTAPIError(
                        error="Self-deactivate blocked",
                        error_description="A superuser cannot deactivate their own account.",
                    )
                    return Response(content=error, status_code=403)
            user_info = (
                str_to_dict(data.user_info) if data.user_info is not None else None
            )
            updated = user.update(
                email=data.email,
                full_name=data.full_name,
                is_active=data.is_active,
                is_superuser=data.is_superuser,
                user_info=user_info,
                password=data.password,
            )
            if updated is None:
                error = RESTAPIError(
                    error="User not updated",
                    error_description="No update parameters provided, or update failed.",
                )
                return Response(content=error, status_code=400)
            return UserOutput.model_validate(updated.model_dump())
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the user.",
            )
            return Response(content=error, status_code=500)

    @delete(path="/id/{user_id:str}", sync_to_thread=True)
    def delete_user(self, superuser: User, user_id: str) -> None:
        try:
            user = User.get_by_id(id=user_id)
            if user is None:
                return None
            if str(user.id) == str(superuser.id):
                # Block self-deletion — matches old backend semantics.
                from litestar.exceptions import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail="Super users are not allowed to delete themselves.",
                )
            user.delete()
            return None
        except Exception:
            raise
