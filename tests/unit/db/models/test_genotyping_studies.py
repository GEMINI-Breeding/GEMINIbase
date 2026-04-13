"""Unit tests for GenotypingStudyModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.genotyping_studies import GenotypingStudyModel


class TestGenotypingStudyModelSchema:

    def test_tablename(self):
        assert GenotypingStudyModel.__tablename__ == "genotyping_studies"

    def test_schema_is_gemini(self):
        assert GenotypingStudyModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in GenotypingStudyModel.__table__.columns

    def test_id_is_primary_key(self):
        assert GenotypingStudyModel.__table__.columns["id"].primary_key

    def test_has_study_name_column(self):
        assert "study_name" in GenotypingStudyModel.__table__.columns

    def test_study_name_not_nullable(self):
        assert GenotypingStudyModel.__table__.columns["study_name"].nullable is False

    def test_has_study_info_column(self):
        assert "study_info" in GenotypingStudyModel.__table__.columns

    def test_study_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = GenotypingStudyModel.__table__.columns["study_info"]
        assert isinstance(col.type, JSONB)

    def test_has_created_at_column(self):
        assert "created_at" in GenotypingStudyModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in GenotypingStudyModel.__table__.columns

    def test_gin_index_on_study_info(self):
        index_names = [idx.name for idx in GenotypingStudyModel.__table__.indexes]
        assert "idx_genotyping_studies_info" in index_names

    def test_unique_constraint_on_study_name(self):
        unique_constraints = [
            c for c in GenotypingStudyModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "study_name" in col_names

    def test_column_count(self):
        assert len(GenotypingStudyModel.__table__.columns) == 5
