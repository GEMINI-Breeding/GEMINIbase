"""Pydantic/API-class tests for AccessionAlias."""

import pytest
from uuid import uuid4

from gemini.api.accession_alias import AccessionAlias


class TestAccessionAliasConstruction:

    def test_construct_with_required_fields(self):
        a = AccessionAlias(alias="1", accession_id=uuid4())
        assert a.alias == "1"
        assert a.scope == "global"
        assert a.experiment_id is None
        assert a.line_id is None

    def test_construct_experiment_scope(self):
        exp_id = uuid4()
        line_id = uuid4()
        a = AccessionAlias(alias="Check1", line_id=line_id, scope="experiment", experiment_id=exp_id)
        assert a.scope == "experiment"
        assert a.experiment_id == exp_id

    def test_alias_is_required(self):
        with pytest.raises(Exception):
            AccessionAlias.model_validate({})


class TestAccessionAliasCreateValidation:
    """Validation on `create()` short-circuits before hitting the DB."""

    def test_requires_exactly_one_target(self):
        # Both set
        result = AccessionAlias.create(alias="1", accession_id=uuid4(), line_id=uuid4())
        assert result is None
        # Neither set
        result = AccessionAlias.create(alias="1")
        assert result is None

    def test_invalid_scope_rejected(self):
        assert AccessionAlias.create(alias="1", accession_id=uuid4(), scope="bogus") is None

    def test_experiment_scope_requires_experiment_id(self):
        assert AccessionAlias.create(
            alias="1", accession_id=uuid4(), scope="experiment"
        ) is None

    def test_global_scope_rejects_experiment_id(self):
        assert AccessionAlias.create(
            alias="1", accession_id=uuid4(), scope="global", experiment_id=uuid4()
        ) is None
