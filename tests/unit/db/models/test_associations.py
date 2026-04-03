"""
Tests for gemini.db.models.associations — association (join) table definitions.

Verifies table names, foreign keys, and unique constraints for a representative
sample of the association models.
"""
import pytest
from sqlalchemy.schema import UniqueConstraint, ForeignKeyConstraint
from sqlalchemy import ForeignKey

from gemini.db.models.associations import (
    DataTypeFormatModel,
    ExperimentSiteModel,
    ExperimentSensorModel,
    ExperimentTraitModel,
    ExperimentCultivarModel,
    ExperimentDatasetModel,
    PlotCultivarModel,
    TraitSensorModel,
    SensorPlatformSensorModel,
    SensorDatasetModel,
    TraitDatasetModel,
    ModelDatasetModel,
    ScriptDatasetModel,
    ProcedureDatasetModel,
    ExperimentSensorPlatformModel,
    ExperimentModelModel,
    ExperimentProcedureModel,
    ExperimentScriptModel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_fk_target_tables(model):
    """Return the set of target table references (e.g. 'gemini.experiments.id') from foreign keys."""
    targets = set()
    for col in model.__table__.columns:
        for fk in col.foreign_keys:
            targets.add(fk.target_fullname)
    return targets


def _has_unique_constraint(model, *col_names):
    """Check that the model has a unique constraint covering exactly col_names."""
    for c in model.__table__.constraints:
        if isinstance(c, UniqueConstraint):
            constraint_cols = {col.name for col in c.columns}
            if set(col_names).issubset(constraint_cols):
                return True
    return False


# ===========================================================================
# DataTypeFormatModel
# ===========================================================================


class TestDataTypeFormatModel:

    def test_tablename(self):
        assert DataTypeFormatModel.__tablename__ == "data_type_formats"

    def test_has_data_type_id(self):
        assert "data_type_id" in DataTypeFormatModel.__table__.columns

    def test_has_data_format_id(self):
        assert "data_format_id" in DataTypeFormatModel.__table__.columns

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(DataTypeFormatModel)
        assert "gemini.data_types.id" in targets
        assert "gemini.data_formats.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(DataTypeFormatModel, "data_type_id", "data_format_id")

    def test_has_info_column(self):
        assert "info" in DataTypeFormatModel.__table__.columns

    def test_has_timestamps(self):
        assert "created_at" in DataTypeFormatModel.__table__.columns
        assert "updated_at" in DataTypeFormatModel.__table__.columns


# ===========================================================================
# ExperimentSiteModel
# ===========================================================================


class TestExperimentSiteModel:

    def test_tablename(self):
        assert ExperimentSiteModel.__tablename__ == "experiment_sites"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentSiteModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.sites.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(ExperimentSiteModel, "experiment_id", "site_id")

    def test_has_timestamps(self):
        assert "created_at" in ExperimentSiteModel.__table__.columns
        assert "updated_at" in ExperimentSiteModel.__table__.columns


# ===========================================================================
# ExperimentSensorModel
# ===========================================================================


class TestExperimentSensorModel:

    def test_tablename(self):
        assert ExperimentSensorModel.__tablename__ == "experiment_sensors"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentSensorModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.sensors.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(
            ExperimentSensorModel, "experiment_id", "sensor_id"
        )


# ===========================================================================
# ExperimentTraitModel
# ===========================================================================


class TestExperimentTraitModel:

    def test_tablename(self):
        assert ExperimentTraitModel.__tablename__ == "experiment_traits"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentTraitModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.traits.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(
            ExperimentTraitModel, "experiment_id", "trait_id"
        )


# ===========================================================================
# ExperimentCultivarModel
# ===========================================================================


class TestExperimentCultivarModel:

    def test_tablename(self):
        assert ExperimentCultivarModel.__tablename__ == "experiment_cultivars"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentCultivarModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.cultivars.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(
            ExperimentCultivarModel, "experiment_id", "cultivar_id"
        )


# ===========================================================================
# ExperimentDatasetModel
# ===========================================================================


class TestExperimentDatasetModel:

    def test_tablename(self):
        assert ExperimentDatasetModel.__tablename__ == "experiment_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentDatasetModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.datasets.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(
            ExperimentDatasetModel, "experiment_id", "dataset_id"
        )


# ===========================================================================
# PlotCultivarModel
# ===========================================================================


class TestPlotCultivarModel:

    def test_tablename(self):
        assert PlotCultivarModel.__tablename__ == "plot_cultivars"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(PlotCultivarModel)
        assert "gemini.plots.id" in targets
        assert "gemini.cultivars.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(PlotCultivarModel, "plot_id", "cultivar_id")


# ===========================================================================
# TraitSensorModel
# ===========================================================================


class TestTraitSensorModel:

    def test_tablename(self):
        assert TraitSensorModel.__tablename__ == "trait_sensors"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(TraitSensorModel)
        assert "gemini.traits.id" in targets
        assert "gemini.sensors.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(TraitSensorModel, "trait_id", "sensor_id")


# ===========================================================================
# SensorPlatformSensorModel
# ===========================================================================


class TestSensorPlatformSensorModel:

    def test_tablename(self):
        assert SensorPlatformSensorModel.__tablename__ == "sensor_platform_sensors"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(SensorPlatformSensorModel)
        assert "gemini.sensor_platforms.id" in targets
        assert "gemini.sensors.id" in targets

    def test_unique_constraint(self):
        assert _has_unique_constraint(
            SensorPlatformSensorModel, "sensor_platform_id", "sensor_id"
        )


# ===========================================================================
# SensorDatasetModel
# ===========================================================================


class TestSensorDatasetModel:

    def test_tablename(self):
        assert SensorDatasetModel.__tablename__ == "sensor_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(SensorDatasetModel)
        assert "gemini.sensors.id" in targets
        assert "gemini.datasets.id" in targets


# ===========================================================================
# TraitDatasetModel
# ===========================================================================


class TestTraitDatasetModel:

    def test_tablename(self):
        assert TraitDatasetModel.__tablename__ == "trait_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(TraitDatasetModel)
        assert "gemini.traits.id" in targets
        assert "gemini.datasets.id" in targets


# ===========================================================================
# ModelDatasetModel
# ===========================================================================


class TestModelDatasetModel:

    def test_tablename(self):
        assert ModelDatasetModel.__tablename__ == "model_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ModelDatasetModel)
        assert "gemini.models.id" in targets
        assert "gemini.datasets.id" in targets


# ===========================================================================
# ScriptDatasetModel
# ===========================================================================


class TestScriptDatasetModel:

    def test_tablename(self):
        assert ScriptDatasetModel.__tablename__ == "script_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ScriptDatasetModel)
        assert "gemini.scripts.id" in targets
        assert "gemini.datasets.id" in targets


# ===========================================================================
# ProcedureDatasetModel
# ===========================================================================


class TestProcedureDatasetModel:

    def test_tablename(self):
        assert ProcedureDatasetModel.__tablename__ == "procedure_datasets"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ProcedureDatasetModel)
        assert "gemini.procedures.id" in targets
        assert "gemini.datasets.id" in targets


# ===========================================================================
# Remaining Experiment association models
# ===========================================================================


class TestExperimentSensorPlatformModel:

    def test_tablename(self):
        assert ExperimentSensorPlatformModel.__tablename__ == "experiment_sensor_platforms"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentSensorPlatformModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.sensor_platforms.id" in targets


class TestExperimentModelModel:

    def test_tablename(self):
        assert ExperimentModelModel.__tablename__ == "experiment_models"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentModelModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.models.id" in targets


class TestExperimentProcedureModel:

    def test_tablename(self):
        assert ExperimentProcedureModel.__tablename__ == "experiment_procedures"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentProcedureModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.procedures.id" in targets


class TestExperimentScriptModel:

    def test_tablename(self):
        assert ExperimentScriptModel.__tablename__ == "experiment_scripts"

    def test_foreign_keys(self):
        targets = _get_fk_target_tables(ExperimentScriptModel)
        assert "gemini.experiments.id" in targets
        assert "gemini.scripts.id" in targets
