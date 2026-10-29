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
