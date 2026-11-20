"""Who may delete an upload or result of an experiment."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gemini.rest_api import people

pytestmark = pytest.mark.unit

ADMIN = SimpleNamespace(id="a", is_superuser=True)
ANA = SimpleNamespace(id="u1", is_superuser=False)


def _dataset(*experiment_ids):
    d = MagicMock()
    d.get_associated_experiments.return_value = [SimpleNamespace(id=i) for i in experiment_ids]
    return d


def test_administrators_and_an_app_without_sign_in_may():
    assert people.may_change_dataset(_dataset("e1"), ADMIN)
    assert people.may_change_dataset(_dataset("e1"), None)


@patch("gemini.db.models.associations.UserExperimentModel.search")
def test_people_who_belong_to_one_of_its_experiments_may(search):
    search.side_effect = lambda user_id, experiment_id: [object()] if experiment_id == "e2" else []
    assert people.may_change_dataset(_dataset("e1", "e2"), ANA)
    assert not people.may_change_dataset(_dataset("e1"), ANA)
    assert not people.may_change_dataset(_dataset(), ANA)       # in no experiment: administrators only


def _experiment(visibility="public", id="e1"):
    return SimpleNamespace(id=id, experiment_info={"visibility": visibility})


@patch("gemini.db.models.associations.UserExperimentModel.search", return_value=[])
def test_anyone_joins_a_public_experiment_as_a_member_only(_search):
    assert people.self_link_refusal(_experiment(), ANA, None) is None
    assert people.self_link_refusal(_experiment(), ANA, "member") is None
    assert "owner" in people.self_link_refusal(_experiment(), ANA, "owner")
    assert "private" in people.self_link_refusal(_experiment("private"), ANA, "member")
    assert people.self_link_refusal(_experiment("private"), ADMIN, "owner") is None


@patch("gemini.db.models.associations.UserExperimentModel.search", return_value=[object()])
def test_someone_already_in_it_changes_nothing(_search):
    assert people.self_link_refusal(_experiment("private"), ANA, "owner") is None
