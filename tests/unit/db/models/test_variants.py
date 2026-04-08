"""Unit tests for VariantModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.variants import VariantModel


class TestVariantModelSchema:

    def test_tablename(self):
        assert VariantModel.__tablename__ == "variants"

    def test_schema_is_gemini(self):
        assert VariantModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in VariantModel.__table__.columns

    def test_id_is_primary_key(self):
        assert VariantModel.__table__.columns["id"].primary_key

    def test_has_variant_name_column(self):
        assert "variant_name" in VariantModel.__table__.columns

    def test_variant_name_not_nullable(self):
        assert VariantModel.__table__.columns["variant_name"].nullable is False

    def test_has_chromosome_column(self):
        assert "chromosome" in VariantModel.__table__.columns

    def test_chromosome_not_nullable(self):
        assert VariantModel.__table__.columns["chromosome"].nullable is False

    def test_has_position_column(self):
        assert "position" in VariantModel.__table__.columns

    def test_position_not_nullable(self):
        assert VariantModel.__table__.columns["position"].nullable is False

    def test_has_alleles_column(self):
        assert "alleles" in VariantModel.__table__.columns

    def test_alleles_not_nullable(self):
        assert VariantModel.__table__.columns["alleles"].nullable is False

    def test_has_design_sequence_column(self):
        assert "design_sequence" in VariantModel.__table__.columns

    def test_has_variant_info_column(self):
        assert "variant_info" in VariantModel.__table__.columns

    def test_variant_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = VariantModel.__table__.columns["variant_info"]
        assert isinstance(col.type, JSONB)

    def test_has_created_at_column(self):
        assert "created_at" in VariantModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in VariantModel.__table__.columns

    def test_gin_index_on_variant_info(self):
        index_names = [idx.name for idx in VariantModel.__table__.indexes]
        assert "idx_variants_info" in index_names

    def test_chromosome_index(self):
        index_names = [idx.name for idx in VariantModel.__table__.indexes]
        assert "idx_variants_chromosome" in index_names

    def test_unique_constraint_on_variant_name(self):
        unique_constraints = [
            c for c in VariantModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "variant_name" in col_names

    def test_column_count(self):
        assert len(VariantModel.__table__.columns) == 9
