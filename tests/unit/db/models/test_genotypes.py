"""Unit tests for GenotypeModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.genotypes import GenotypeModel


class TestGenotypeModelSchema:

    def test_tablename(self):
        assert GenotypeModel.__tablename__ == "genotypes"

    def test_schema_is_gemini(self):
        assert GenotypeModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in GenotypeModel.__table__.columns

    def test_id_is_primary_key(self):
        assert GenotypeModel.__table__.columns["id"].primary_key

    def test_has_genotype_name_column(self):
        assert "genotype_name" in GenotypeModel.__table__.columns

    def test_genotype_name_not_nullable(self):
        assert GenotypeModel.__table__.columns["genotype_name"].nullable is False

    def test_has_genotype_info_column(self):
        assert "genotype_info" in GenotypeModel.__table__.columns

    def test_genotype_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = GenotypeModel.__table__.columns["genotype_info"]
        assert isinstance(col.type, JSONB)

    def test_has_created_at_column(self):
        assert "created_at" in GenotypeModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in GenotypeModel.__table__.columns

    def test_gin_index_on_genotype_info(self):
        index_names = [idx.name for idx in GenotypeModel.__table__.indexes]
        assert "idx_genotypes_info" in index_names

    def test_unique_constraint_on_genotype_name(self):
        unique_constraints = [
            c for c in GenotypeModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "genotype_name" in col_names

    def test_column_count(self):
        assert len(GenotypeModel.__table__.columns) == 5
