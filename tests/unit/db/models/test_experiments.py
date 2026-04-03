"""
Tests for gemini.db.models.experiments.ExperimentModel schema definition.
"""
import pytest
from sqlalchemy.schema import UniqueConstraint, CheckConstraint

from gemini.db.models.experiments import ExperimentModel


class TestExperimentModelSchema:
    """Verify ExperimentModel table metadata and column definitions."""

    def test_tablename(self):
        assert ExperimentModel.__tablename__ == "experiments"

    def test_has_id_column(self):
        assert "id" in ExperimentModel.__table__.columns

    def test_has_experiment_name_column(self):
        assert "experiment_name" in ExperimentModel.__table__.columns

    def test_has_experiment_info_column(self):
        assert "experiment_info" in ExperimentModel.__table__.columns

    def test_has_experiment_start_date_column(self):
        assert "experiment_start_date" in ExperimentModel.__table__.columns

    def test_has_experiment_end_date_column(self):
        assert "experiment_end_date" in ExperimentModel.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in ExperimentModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in ExperimentModel.__table__.columns

    def test_id_is_primary_key(self):
        assert ExperimentModel.__table__.columns["id"].primary_key

    def test_experiment_name_not_nullable(self):
        assert ExperimentModel.__table__.columns["experiment_name"].nullable is False

    def test_unique_constraint_on_experiment_name(self):
        unique_constraints = [
            c
            for c in ExperimentModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert "experiment_name" in col_names

    def test_check_constraints_exist(self):
        check_constraints = [
            c
            for c in ExperimentModel.__table__.constraints
            if isinstance(c, CheckConstraint)
        ]
        assert len(check_constraints) >= 2

    def test_gin_index_on_experiment_info(self):
        index_names = [idx.name for idx in ExperimentModel.__table__.indexes]
        assert "idx_experiments_info" in index_names

    def test_experiment_info_column_type_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB

        col = ExperimentModel.__table__.columns["experiment_info"]
        assert isinstance(col.type, JSONB)

    def test_column_count(self):
        # id, experiment_name, experiment_info, experiment_start_date, experiment_end_date, created_at, updated_at
        assert len(ExperimentModel.__table__.columns) == 7

    def test_schema_is_gemini(self):
        assert ExperimentModel.__table__.schema == "gemini"

    def test_start_date_not_nullable(self):
        assert ExperimentModel.__table__.columns["experiment_start_date"].nullable is False

    def test_end_date_not_nullable(self):
        assert ExperimentModel.__table__.columns["experiment_end_date"].nullable is False
