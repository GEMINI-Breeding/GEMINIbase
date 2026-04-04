from gemini.rest_api.controllers.population import PopulationController
from gemini.rest_api.controllers.data_format import DataFormatController
from gemini.rest_api.controllers.data_type import DataTypeController
from gemini.rest_api.controllers.dataset_type import DatasetTypeController
from gemini.rest_api.controllers.dataset import DatasetController
from gemini.rest_api.controllers.experiment import ExperimentController
from gemini.rest_api.controllers.model import ModelController
from gemini.rest_api.controllers.plant import PlantController
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

controllers = {
    "populations": PopulationController,
    "data_formats": DataFormatController,
    "data_types": DataTypeController,
    "dataset_types": DatasetTypeController,
    "datasets": DatasetController,
    "experiments": ExperimentController,
    "models": ModelController,
    "plants": PlantController,
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
    "files": FileController
}

