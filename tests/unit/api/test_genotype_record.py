"""Tests for the GenotypeRecord API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.genotype_record import GenotypeRecord


class TestGenotypeRecordModel:

    def test_construct_with_defaults(self):
        rec = GenotypeRecord()
        assert rec.id is None
        assert rec.study_id is None
        assert rec.study_name is None
        assert rec.accession_id is None
        assert rec.accession_name is None
        assert rec.call_value is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        sid = uuid4()
        vid = uuid4()
        aid = uuid4()
        rec = GenotypeRecord(
            id=uid,
            study_id=sid,
            study_name="GBS_Run_1",
            variant_id=vid,
            variant_name="2_24641",
            chromosome=2,
            position=24.641,
            accession_id=aid,
            accession_name="B73",
            call_value="TT",
            record_info={"quality": 30},
        )
        assert rec.id == uid
        assert rec.study_name == "GBS_Run_1"
        assert rec.accession_name == "B73"
        assert rec.call_value == "TT"
        assert rec.chromosome == 2

    def test_no_population_fields(self):
        rec = GenotypeRecord()
        assert not hasattr(rec, "population_id")
        assert not hasattr(rec, "population_name")
        assert not hasattr(rec, "population_accession")

    def test_no_genotype_fields(self):
        rec = GenotypeRecord()
        assert not hasattr(rec, "genotype_id")
        assert not hasattr(rec, "genotype_name")

    def test_has_study_fields(self):
        rec = GenotypeRecord(study_id=uuid4(), study_name="X")
        assert rec.study_name == "X"

    def test_str_representation(self):
        rec = GenotypeRecord(
            study_name="GBS", variant_name="1_100",
            accession_name="Mo17", call_value="AA"
        )
        s = str(rec)
        assert "GBS" in s
        assert "Mo17" in s
