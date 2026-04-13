"""Unit tests for LineModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.lines import LineModel


class TestLineModelSchema:

    def test_tablename(self):
        assert LineModel.__tablename__ == "lines"

    def test_schema_is_gemini(self):
        assert LineModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in LineModel.__table__.columns

    def test_id_is_primary_key(self):
        assert LineModel.__table__.columns["id"].primary_key

    def test_has_line_name_column(self):
        assert "line_name" in LineModel.__table__.columns

    def test_line_name_not_nullable(self):
        assert LineModel.__table__.columns["line_name"].nullable is False

    def test_has_species_column(self):
        assert "species" in LineModel.__table__.columns

    def test_has_line_info_column(self):
        assert "line_info" in LineModel.__table__.columns

    def test_line_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = LineModel.__table__.columns["line_info"]
        assert isinstance(col.type, JSONB)

    def test_has_timestamps(self):
        assert "created_at" in LineModel.__table__.columns
        assert "updated_at" in LineModel.__table__.columns

    def test_gin_index_on_line_info(self):
        index_names = [idx.name for idx in LineModel.__table__.indexes]
        assert "idx_lines_info" in index_names

    def test_unique_constraint_on_line_name(self):
        unique_constraints = [
            c for c in LineModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "line_name" in col_names

    def test_column_count(self):
        assert len(LineModel.__table__.columns) == 6
