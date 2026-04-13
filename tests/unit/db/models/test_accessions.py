"""Unit tests for AccessionModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.accessions import AccessionModel


class TestAccessionModelSchema:

    def test_tablename(self):
        assert AccessionModel.__tablename__ == "accessions"

    def test_schema_is_gemini(self):
        assert AccessionModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in AccessionModel.__table__.columns

    def test_id_is_primary_key(self):
        assert AccessionModel.__table__.columns["id"].primary_key

    def test_has_accession_name_column(self):
        assert "accession_name" in AccessionModel.__table__.columns

    def test_accession_name_not_nullable(self):
        assert AccessionModel.__table__.columns["accession_name"].nullable is False

    def test_has_line_id_column(self):
        assert "line_id" in AccessionModel.__table__.columns

    def test_line_id_is_nullable(self):
        assert AccessionModel.__table__.columns["line_id"].nullable is True

    def test_line_id_foreign_key(self):
        col = AccessionModel.__table__.columns["line_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "gemini.lines.id" in fk_targets

    def test_has_species_column(self):
        assert "species" in AccessionModel.__table__.columns

    def test_has_accession_info_column(self):
        assert "accession_info" in AccessionModel.__table__.columns

    def test_accession_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = AccessionModel.__table__.columns["accession_info"]
        assert isinstance(col.type, JSONB)

    def test_has_timestamps(self):
        assert "created_at" in AccessionModel.__table__.columns
        assert "updated_at" in AccessionModel.__table__.columns

    def test_gin_index_on_accession_info(self):
        index_names = [idx.name for idx in AccessionModel.__table__.indexes]
        assert "idx_accessions_info" in index_names

    def test_unique_constraint_on_accession_name(self):
        unique_constraints = [
            c for c in AccessionModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "accession_name" in col_names

    def test_column_count(self):
        assert len(AccessionModel.__table__.columns) == 7
