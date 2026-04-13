"""Tests for the Accession API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.accession import Accession


class TestAccessionModel:

    def test_construct_with_required_fields(self):
        acc = Accession(accession_name="PI123456")
        assert acc.accession_name == "PI123456"
        assert acc.id is None
        assert acc.line_id is None
        assert acc.species is None
        assert acc.accession_info is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        lid = uuid4()
        acc = Accession(
            id=uid,
            accession_name="B73-sel1",
            line_id=lid,
            species="Zea mays",
            accession_info={"source": "USDA"},
        )
        assert acc.id == uid
        assert acc.accession_name == "B73-sel1"
        assert acc.line_id == lid
        assert acc.species == "Zea mays"
        assert acc.accession_info == {"source": "USDA"}

    def test_id_alias_accession_id(self):
        uid = uuid4()
        acc = Accession.model_validate({"accession_id": str(uid), "accession_name": "X"})
        assert str(acc.id) == str(uid)

    def test_accession_name_is_required(self):
        with pytest.raises(Exception):
            Accession.model_validate({})

    def test_str_representation(self):
        acc = Accession(accession_name="PI123456")
        assert "PI123456" in str(acc)
