"""Unit tests for GenotypeRecordModel schema definition."""

from sqlalchemy import UniqueConstraint
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel


class TestGenotypeRecordModelSchema:

    def test_tablename(self):
        assert GenotypeRecordModel.__tablename__ == "genotype_records"

    def test_schema_is_gemini(self):
        assert GenotypeRecordModel.__table__.schema == "gemini"

    def test_has_id_column(self):
        assert "id" in GenotypeRecordModel.__table__.columns

    def test_id_is_primary_key(self):
        assert GenotypeRecordModel.__table__.columns["id"].primary_key

    def test_has_study_id_column(self):
        assert "study_id" in GenotypeRecordModel.__table__.columns

    def test_has_study_name_column(self):
        assert "study_name" in GenotypeRecordModel.__table__.columns

    def test_has_variant_id_column(self):
        assert "variant_id" in GenotypeRecordModel.__table__.columns

    def test_has_variant_name_column(self):
        assert "variant_name" in GenotypeRecordModel.__table__.columns

    def test_has_chromosome_column(self):
        assert "chromosome" in GenotypeRecordModel.__table__.columns

    def test_has_position_column(self):
        assert "position" in GenotypeRecordModel.__table__.columns

    def test_has_accession_id_column(self):
        assert "accession_id" in GenotypeRecordModel.__table__.columns

    def test_has_accession_name_column(self):
        assert "accession_name" in GenotypeRecordModel.__table__.columns

    def test_has_call_value_column(self):
        assert "call_value" in GenotypeRecordModel.__table__.columns

    def test_has_record_info_column(self):
        assert "record_info" in GenotypeRecordModel.__table__.columns

    def test_record_info_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB
        col = GenotypeRecordModel.__table__.columns["record_info"]
        assert isinstance(col.type, JSONB)

    def test_no_population_columns(self):
        cols = set(GenotypeRecordModel.__table__.columns.keys())
        assert "population_id" not in cols
        assert "population_name" not in cols
        assert "population_accession" not in cols

    def test_no_genotype_columns(self):
        cols = set(GenotypeRecordModel.__table__.columns.keys())
        assert "genotype_id" not in cols
        assert "genotype_name" not in cols

    def test_unique_constraint_exists(self):
        unique_constraints = [
            c for c in GenotypeRecordModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        for uc in unique_constraints:
            if uc.name == "genotype_records_unique":
                col_names = {col.name for col in uc.columns}
                assert col_names == {"study_id", "variant_id", "accession_id"}
                return
        assert False, "genotype_records_unique constraint not found"

    def test_composite_indexes_exist(self):
        index_names = [idx.name for idx in GenotypeRecordModel.__table__.indexes]
        assert "idx_genotype_records_study_variant" in index_names
        assert "idx_genotype_records_study_accession" in index_names
        assert "idx_genotype_records_chromosome" in index_names

    def test_gin_index_on_record_info(self):
        index_names = [idx.name for idx in GenotypeRecordModel.__table__.indexes]
        assert "idx_genotype_records_record_info" in index_names

    def test_column_count(self):
        assert len(GenotypeRecordModel.__table__.columns) == 11
