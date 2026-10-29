"""Who is behind the data: the user each experiment belongs to (and others
linked to it), whether it is shown to everyone, and the sign-in without a
password a lab can turn on for a test setup.

Experiments are public unless their owner marks them private
(``experiment_info.visibility = "private"``). Private hides an experiment
from other people's experiment lists; it is not access control on the data
underneath (files, jobs, records), which stays readable through the API.
"""
from __future__ import annotations

import logging
import secrets
from typing import Any, Optional

from gemini.config.settings import GEMINISettings

logger = logging.getLogger(__name__)
_settings = GEMINISettings()

GUEST_EMAIL = "guest@gemi.local"
VISIBILITY = ("public", "private")


def passwordless_enabled() -> bool:
    """Accounts without a password, and the guest sign-in (a lab's test setup)."""
    return bool(getattr(_settings, "GEMINI_PASSWORDLESS_LOGIN", False))


def is_passwordless(user: Any) -> bool:
    info = getattr(user, "user_info", None) or {}
    return bool(isinstance(info, dict) and info.get("passwordless"))


def random_password() -> str:
    """The stored password of an account that signs in without one: never told to anyone."""
    return secrets.token_urlsafe(32)


def guest_user():
    """The shared guest account (made on first use): signed in without a password, no admin rights."""
    from gemini.api.user import User

    user = User.get(email=GUEST_EMAIL)
    if user is None:
        user = User.create(email=GUEST_EMAIL, password=random_password(), full_name="Guest",
                           is_active=True, is_superuser=False, user_info={"passwordless": True, "guest": True})
    return user


def people_by_experiment() -> dict[str, list[dict]]:
    """{experiment id: [{user_id, email, full_name, role}]}, owners first."""
    from gemini.db.models.associations import UserExperimentModel
    from gemini.db.models.users import UserModel

    users = {str(u.id): u for u in UserModel.search()}
    out: dict[str, list[dict]] = {}
    for row in UserExperimentModel.search():
        u = users.get(str(row.user_id))
        if u is None:
            continue
        out.setdefault(str(row.experiment_id), []).append(
            {"user_id": str(u.id), "email": u.email, "full_name": u.full_name, "role": row.role or "member"})
    for rows in out.values():
        rows.sort(key=lambda r: (r["role"] != "owner", r["email"]))
    return out


def visibility_of(experiment: Any) -> str:
    info = getattr(experiment, "experiment_info", None) or {}
    v = info.get("visibility") if isinstance(info, dict) else None
    return v if v in VISIBILITY else "public"


def visible_to(experiments: list, user: Optional[Any]) -> list:
    """The experiments a person's lists show: public ones, and private ones they belong to.
    Administrators and an app without sign-in see all."""
    if user is None or getattr(user, "is_superuser", False):
        return experiments
    private = [e for e in experiments if visibility_of(e) == "private"]
    if not private:
        return experiments
    from gemini.db.models.associations import UserExperimentModel

    mine = {str(r.experiment_id) for r in UserExperimentModel.search(user_id=str(user.id))}
    return [e for e in experiments if visibility_of(e) != "private" or str(e.id) in mine]


def is_owner(experiment_id: str, user: Any) -> bool:
    if user is None or getattr(user, "is_superuser", False):
        return True
    from gemini.db.models.associations import UserExperimentModel

    rows = UserExperimentModel.search(user_id=str(user.id), experiment_id=str(experiment_id))
    return any((r.role or "") == "owner" for r in rows)


ROLES = ("member", "owner")


def self_link_refusal(experiment: Any, user: Any, role: Optional[str]) -> Optional[str]:
    """Why a person may not link themselves to an experiment, or None when they may.
    Joining a public experiment as a member is open to everyone; being made owner, or
    joining a private experiment, takes its owner or an administrator."""
    if user is None or getattr(user, "is_superuser", False):
        return None
    if belongs_to(str(experiment.id), user):
        return None                                # already in it: nothing changes
    if (role or "member") != "member":
        return "Only the experiment's owner (or an administrator) can make someone its owner."
    if visibility_of(experiment) == "private":
        return "This experiment is private: its owner (or an administrator) adds people to it."
    return None


def belongs_to(experiment_id: str, user: Any) -> bool:
    """Whether a person works on an experiment (any role). Administrators and an app
    without sign-in: always."""
    if user is None or getattr(user, "is_superuser", False):
        return True
    from gemini.db.models.associations import UserExperimentModel

    return bool(UserExperimentModel.search(user_id=str(user.id), experiment_id=str(experiment_id)))


def may_change_dataset(dataset: Any, user: Any) -> bool:
    """Whether a person may delete an upload or result: they belong to one of the
    experiments it is part of (an administrator, or an app without sign-in: always)."""
    if user is None or getattr(user, "is_superuser", False):
        return True
    experiments = dataset.get_associated_experiments() or []
    return any(belongs_to(str(e.id), user) for e in experiments)


def claim(experiment_id: str, user: Any, role: str = "owner") -> None:
    """Link a person to an experiment (its creator as owner); best effort."""
    if user is None:
        return
    try:
        user.associate_experiment(experiment_id=experiment_id, role=role)
    except Exception:
        logger.exception("could not link %s to experiment %s", getattr(user, "email", "?"), experiment_id)
