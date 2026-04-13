from gemini.rest_api.controllers.population import PopulationController
from gemini.rest_api.controllers.data_format import DataFormatController
from gemini.rest_api.controllers.data_type import DataTypeController
from gemini.rest_api.controllers.dataset_type import DatasetTypeController
from gemini.rest_api.controllers.dataset import DatasetController
from gemini.rest_api.controllers.experiment import ExperimentController
from gemini.rest_api.controllers.model import ModelController
from gemini.rest_api.controllers.line import LineController
from gemini.rest_api.controllers.accession import AccessionController
from gemini.rest_api.controllers.plot import PlotController
from gemini.rest_api.controllers.script import ScriptController
from gemini.rest_api.controllers.season import SeasonController
from gemini.rest_api.controllers.sensor_platform import SensorPlatformController
from gemini.rest_api.controllers.sensor_type import SensorTypeController
from gemini.rest_api.controllers.sensor import SensorController
from gemini.rest_api.controllers.site import SiteController
from gemini.rest_api.controllers.trait_level import TraitLevelController
from gemini.rest_api.controllers.trait import TraitController
from gemini.rest_api.controllers.procedure import ProcedureController
from gemini.rest_api.controllers.files import FileController
from gemini.rest_api.controllers.geojson import GeoJsonController
from gemini.rest_api.controllers.csv_data import CsvController
from gemini.rest_api.controllers.jobs import JobController
from gemini.rest_api.controllers.plot_geometry import PlotGeometryController
from gemini.rest_api.controllers.model_management import ModelManagementController
from gemini.rest_api.controllers.annotations import AnnotationsController
from gemini.rest_api.controllers.variant import VariantController
from gemini.rest_api.controllers.genotyping_study import GenotypingStudyController

controllers = {
    "populations": PopulationController,
    "data_formats": DataFormatController,
    "data_types": DataTypeController,
    "dataset_types": DatasetTypeController,
    "datasets": DatasetController,
    "experiments": ExperimentController,
    "models": ModelController,
    "lines": LineController,
    "accessions": AccessionController,
    "plots": PlotController,
    "procedures": ProcedureController,
    "scripts": ScriptController,
    "seasons": SeasonController,
    "sensor_platforms": SensorPlatformController,
    "sensor_types": SensorTypeController,
    "sensors": SensorController,
    "sites": SiteController,
    "trait_levels": TraitLevelController,
    "traits": TraitController,
    "files": FileController,
    "geojson": GeoJsonController,
    "csv": CsvController,
    "jobs": JobController,
    "plot_geometry": PlotGeometryController,
    "model_management": ModelManagementController,
    "annotations": AnnotationsController,
    "variants": VariantController,
    "genotyping_studies": GenotypingStudyController,
}

