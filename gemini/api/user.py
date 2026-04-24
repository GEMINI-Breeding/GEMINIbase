"""
User API class wrapping UserModel with the standard GEMINIbase lifecycle
(`exists`, `create`, `get`, `get_by_id`, `get_all`, `search`, `update`,
`delete`, `refresh`) plus per-user auth helpers (`authenticate`).

User↔experiment associations are handled via UserExperimentModel so
higher layers can scope data access by "experiments this user owns."
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import AliasChoices, EmailStr, Field

from gemini.api.base import APIBase
from gemini.api.types import ID
from gemini.db.models.users import UserModel
from gemini.db.models.associations import UserExperimentModel
from gemini.rest_api.security import get_password_hash, verify_password

if TYPE_CHECKING:  # pragma: no cover
    from gemini.api.experiment import Experiment


logger = logging.getLogger(__name__)


class User(APIBase):
    """Represents an application user with authentication credentials."""

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "user_id"))

    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    user_info: Optional[dict] = None
    hashed_password: Optional[str] = Field(default=None, exclude=True, repr=False)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __str__(self) -> str:
        return f"User(email={self.email}, is_superuser={self.is_superuser}, id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()

    # --- CRUD ---

    @classmethod
    def exists(cls, email: str) -> bool:
        try:
            return UserModel.exists(email=email)
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
            return False

    @classmethod
    def create(
        cls,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_active: bool = True,
        is_superuser: bool = False,
        user_info: Optional[dict] = None,
    ) -> Optional["User"]:
        try:
            if UserModel.exists(email=email):
                logger.warning(f"User with email {email} already exists.")
                return None
            db_instance = UserModel.create(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                is_active=is_active,
                is_superuser=is_superuser,
                user_info=user_info,
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    @classmethod
    def get(cls, email: str) -> Optional["User"]:
        try:
            db_instance = UserModel.get_by_parameters(email=email)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error retrieving user: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["User"]:
        try:
            db_instance = UserModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error retrieving user by ID: {e}")
            return None

    @classmethod
    def get_all(
        cls, limit: int = None, offset: int = None
    ) -> Optional[List["User"]]:
        try:
            users = UserModel.all(limit=limit, offset=offset)
            if not users:
                return None
            return [cls.model_validate(u) for u in users]
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return None

    @classmethod
    def search(
        cls,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        user_info: Optional[dict] = None,
    ) -> Optional[List["User"]]:
        try:
            if not any(
                [email, full_name, is_active is not None, is_superuser is not None, user_info]
            ):
                logger.warning("At least one search parameter must be provided.")
                return None
            users = UserModel.search(
                email=email,
                full_name=full_name,
                is_active=is_active,
                is_superuser=is_superuser,
                user_info=user_info,
            )
            if not users:
                return None
            return [cls.model_validate(u) for u in users]
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return None

    def update(
        self,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        user_info: Optional[dict] = None,
        password: Optional[str] = None,
    ) -> Optional["User"]:
        try:
            if not any(
                [
                    email,
                    full_name,
                    is_active is not None,
                    is_superuser is not None,
                    user_info,
                    password,
                ]
            ):
                logger.warning("At least one update parameter must be provided.")
                return None
            db_instance = UserModel.get(self.id)
            if not db_instance:
                logger.warning(f"User {self.id} does not exist.")
                return None
            update_kwargs: dict = {}
            if email is not None:
                update_kwargs["email"] = email
            if full_name is not None:
                update_kwargs["full_name"] = full_name
            if is_active is not None:
                update_kwargs["is_active"] = is_active
            if is_superuser is not None:
                update_kwargs["is_superuser"] = is_superuser
            if user_info is not None:
                update_kwargs["user_info"] = user_info
            if password is not None:
                update_kwargs["hashed_password"] = get_password_hash(password)
            db_instance = UserModel.update(db_instance, **update_kwargs)
            updated = self.model_validate(db_instance)
            self.refresh()
            return updated
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = UserModel.get(self.id)
            if not db_instance:
                return False
            UserModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def refresh(self) -> Optional["User"]:
        try:
            db_instance = UserModel.get(self.id)
            if not db_instance:
                return self
            fresh = self.model_validate(db_instance)
            for key, value in fresh.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            # hashed_password is excluded from model_dump but still needed here
            self.hashed_password = db_instance.hashed_password
            return self
        except Exception as e:
            logger.error(f"Error refreshing user: {e}")
            return None

    # --- Auth ---

    @classmethod
    def authenticate(cls, email: str, password: str) -> Optional["User"]:
        """Return the user if credentials match, else None."""
        try:
            db_instance = UserModel.get_by_parameters(email=email)
            if not db_instance:
                return None
            if not verify_password(password, db_instance.hashed_password):
                return None
            user = cls.model_validate(db_instance)
            user.hashed_password = db_instance.hashed_password
            return user
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    # --- Experiment associations ---

    def associate_experiment(
        self,
        experiment_id: UUID | str,
        role: Optional[str] = None,
        info: Optional[dict] = None,
    ) -> bool:
        try:
            UserExperimentModel.get_or_create(
                user_id=self.id,
                experiment_id=experiment_id,
                role=role,
                info=info or {},
            )
            return True
        except Exception as e:
            logger.error(f"Error associating user with experiment: {e}")
            return False

    def unassociate_experiment(self, experiment_id: UUID | str) -> bool:
        try:
            instance = UserExperimentModel.get_by_parameters(
                user_id=self.id, experiment_id=experiment_id
            )
            if not instance:
                return False
            UserExperimentModel.delete(instance)
            return True
        except Exception as e:
            logger.error(f"Error unassociating user from experiment: {e}")
            return False

    def get_associated_experiments(self) -> Optional[List[UUID]]:
        """Return experiment IDs this user is associated with."""
        try:
            rows = UserExperimentModel.search(user_id=self.id)
            if not rows:
                return []
            return [row.experiment_id for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving user experiments: {e}")
            return None
