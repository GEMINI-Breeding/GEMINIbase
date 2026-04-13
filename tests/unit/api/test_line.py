"""Tests for the Line API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.line import Line


class TestLineModel:

    def test_construct_with_required_fields(self):
        line = Line(line_name="B73")
        assert line.line_name == "B73"
        assert line.id is None
        assert line.species is None
        assert line.line_info is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        line = Line(
            id=uid,
            line_name="Mo17",
            species="Zea mays",
            line_info={"pedigree": "unknown"},
        )
        assert line.id == uid
        assert line.line_name == "Mo17"
        assert line.species == "Zea mays"
        assert line.line_info == {"pedigree": "unknown"}

    def test_id_alias_line_id(self):
        uid = uuid4()
        line = Line.model_validate({"line_id": str(uid), "line_name": "W22"})
        assert str(line.id) == str(uid)

    def test_line_name_is_required(self):
        with pytest.raises(Exception):
            Line.model_validate({})

    def test_str_representation(self):
        line = Line(line_name="B73")
        assert "B73" in str(line)

    def test_repr_representation(self):
        line = Line(line_name="B73")
        assert "B73" in repr(line)
