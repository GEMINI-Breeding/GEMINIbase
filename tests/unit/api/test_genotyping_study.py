"""Tests for the GenotypingStudy API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.genotyping_study import GenotypingStudy


class TestGenotypingStudyModel:

    def test_construct_with_required_fields(self):
        gs = GenotypingStudy(study_name="GBS_Run_1")
        assert gs.study_name == "GBS_Run_1"
        assert gs.id is None
        assert gs.study_info is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        gs = GenotypingStudy(
            id=uid,
            study_name="SNP_Array_2024",
            study_info={"platform": "Illumina", "ref_genome": "B73v5"},
        )
        assert gs.id == uid
        assert gs.study_name == "SNP_Array_2024"
        assert gs.study_info["platform"] == "Illumina"

    def test_id_alias_study_id(self):
        uid = uuid4()
        gs = GenotypingStudy.model_validate({"study_id": str(uid), "study_name": "X"})
        assert str(gs.id) == str(uid)

    def test_study_name_is_required(self):
        with pytest.raises(Exception):
            GenotypingStudy.model_validate({})

    def test_str_representation(self):
        gs = GenotypingStudy(study_name="GBS_Run_1")
        assert "GBS_Run_1" in str(gs)
