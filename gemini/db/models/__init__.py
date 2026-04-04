"""
SQLAlchemy models for the GEMINI database.

This package defines the database schema and provides ORM models
for various entities within the GEMINI system, including core data
models, associations, columnar tables, and database views.
"""

from gemini.db.core.base import BaseModel, ColumnarBaseModel, ViewBaseModel
from gemini.db.models.data_formats import DataFormatModel
from gemini.db.models.data_types import DataTypeModel
from gemini.db.models.dataset_types import DatasetTypeModel
from gemini.db.models.sensor_types import SensorTypeModel
from gemini.db.models.trait_levels import TraitLevelModel
from gemini.db.models.datasets import DatasetModel
from gemini.db.models.resources import ResourceModel
from gemini.db.models.model_runs import ModelRunModel
from gemini.db.models.models import ModelModel
from gemini.db.models.procedure_runs import ProcedureRunModel
from gemini.db.models.procedures import ProcedureModel
from gemini.db.models.script_runs import ScriptRunModel
from gemini.db.models.scripts import ScriptModel
from gemini.db.models.resources import ResourceModel
from gemini.db.models.sensor_platforms import SensorPlatformModel
from gemini.db.models.sensors import SensorModel
from gemini.db.models.traits import TraitModel
from gemini.db.models.seasons import SeasonModel
from gemini.db.models.sites import SiteModel
from gemini.db.models.populations import PopulationModel
from gemini.db.models.experiments import ExperimentModel
from gemini.db.models.plots import PlotModel
from gemini.db.models.plants import PlantModel

# Associations
import gemini.db.models.associations as Associations

# Columnar
from gemini.db.models.columnar.dataset_records import DatasetRecordModel
from gemini.db.models.columnar.model_records import ModelRecordModel
from gemini.db.models.columnar.procedure_records import ProcedureRecordModel
from gemini.db.models.columnar.script_records import ScriptRecordModel
from gemini.db.models.columnar.sensor_records import SensorRecordModel
from gemini.db.models.columnar.trait_records import TraitRecordModel

# Views
from gemini.db.models.views.plot_view import PlotViewModel
from gemini.db.models.views.plot_population_view import PlotPopulationViewModel

# Dataset Views
from gemini.db.models.views.dataset_views import (
    SensorDatasetsViewModel,
    TraitDatasetsViewModel,
    ProcedureDatasetsViewModel,
    ScriptDatasetsViewModel,
    ModelDatasetsViewModel,
)

# Experiment Views
from gemini.db.models.views.experiment_views import (
    ExperimentSitesViewModel,
    ExperimentTraitsViewModel,
    ExperimentSensorsViewModel,
    ExperimentPopulationsViewModel,
    ExperimentProceduresViewModel,
    ExperimentScriptsViewModel,
    ExperimentModelsViewModel,
    ExperimentDatasetsViewModel
)

# IMMV Views
from gemini.db.models.views.sensor_records_immv import SensorRecordsIMMVModel
from gemini.db.models.views.trait_records_immv import TraitRecordsIMMVModel


