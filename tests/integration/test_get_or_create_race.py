"""get_or_create when another writer inserts the row between its lookup
and its insert.

The race is reproduced deterministically: the first lookup is made to miss a
row that already exists, as it would if a concurrent request committed it
right after the lookup. The insert then hits the real unique constraint.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _miss_first_lookup(model, attr):
    real = getattr(model, attr)
    calls = {"n": 0}

    def lookup(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real(**kwargs)

    return lookup


def test_returns_the_row_the_other_writer_created(setup_real_db):
    from gemini.db.models.experiments import ExperimentModel

    existing = ExperimentModel.create(experiment_name="Raced Exp")
    with patch.object(ExperimentModel, "get_by_parameters",
                      side_effect=_miss_first_lookup(ExperimentModel, "get_by_parameters")):
        result = ExperimentModel.get_or_create(experiment_name="Raced Exp")
    assert result is not None
    assert str(result.id) == str(existing.id)


def test_other_integrity_errors_still_raise(setup_real_db):
    from sqlalchemy.exc import IntegrityError
    from gemini.db.models.seasons import SeasonModel

    # No experiment with this id exists: an FK violation, not a lost race.
    with pytest.raises(IntegrityError):
        SeasonModel.get_or_create(
            experiment_id="00000000-0000-0000-0000-000000000000", season_name="2024"
        )
