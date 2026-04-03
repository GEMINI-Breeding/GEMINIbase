"""
This module defines the Sensor class, which represents a sensor entity, including its metadata, associations to sensor platforms, experiments, datasets, and records, and related operations.

It includes methods for creating, retrieving, updating, and deleting sensors, as well as methods for checking existence, searching, and managing associations with related entities and records.

This module includes the following methods:

- `exists`: Check if a sensor with the given name exists.
- `create`: Create a new sensor.
- `get`: Retrieve a sensor by its name and experiment.
- `get_by_id`: Retrieve a sensor by its ID.
- `get_all`: Retrieve all sensors.
- `search`: Search for sensors based on various criteria.
- `update`: Update the details of a sensor.
- `delete`: Delete a sensor.
- `refresh`: Refresh the sensor's data from the database.
- `get_info`: Get the additional information of the sensor.
- `set_info`: Set the additional information of the sensor.
- Association methods for sensor platforms, experiments, datasets, and records.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.sensor_record import SensorRecord
from gemini.api.dataset import Dataset, GEMINIDatasetType
from gemini.api.enums import GEMINISensorType, GEMINIDataType, GEMINIDataFormat
from gemini.db.models.sensors import SensorModel
from gemini.db.models.views.experiment_views import ExperimentSensorsViewModel
from gemini.db.models.associations import ExperimentSensorModel, SensorPlatformSensorModel, SensorDatasetModel
from gemini.db.models.views.dataset_views import SensorDatasetsViewModel
from gemini.db.models.views.sensor_platform_sensors_view import SensorPlatformSensorsViewModel
from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.sensor_platform import SensorPlatform
    from gemini.api.dataset import Dataset

logger = logging.getLogger(__name__)

class Sensor(APIBase):
    """
    Represents a sensor entity, including its metadata, associations to sensor platforms, experiments, datasets, and records, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the sensor.
        sensor_name (str): The name of the sensor.
        sensor_type_id (int): The ID of the sensor type.
        sensor_data_type_id (int): The ID of the sensor data type.
        sensor_data_format_id (int): The ID of the sensor data format.
        sensor_info (Optional[dict]): Additional information about the sensor.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "sensor_id"))

    sensor_name: str
    sensor_type_id: int
    sensor_data_type_id: int
    sensor_data_format_id: int
    sensor_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Sensor object."""
        return f"Sensor(sensor_name={self.sensor_name}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Sensor object."""
        return f"Sensor(sensor_name={self.sensor_name}, id={self.id}, sensor_type_id={self.sensor_type_id}, sensor_data_type_id={self.sensor_data_type_id}, sensor_data_format_id={self.sensor_data_format_id})"
    
    @classmethod
    def exists(
        cls,
        sensor_name: str
    ) -> bool:
        """
        Check if a sensor with the given name exists.

        Examples:
            >>> Sensor.exists(sensor_name="Temperature Sensor")
            True

            >>> Sensor.exists(sensor_name="Nonexistent Sensor")
            False

        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            bool: True if the sensor exists, False otherwise.
        """
        try:
            exists = SensorModel.exists(sensor_name=sensor_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of sensor: {e}")
            return False
    
    @classmethod
    def create(
        cls,
        sensor_name: str,
        sensor_type: GEMINISensorType = GEMINISensorType.Default,
        sensor_data_type: GEMINIDataType = GEMINIDataType.Default,
        sensor_data_format: GEMINIDataFormat = GEMINIDataFormat.Default,
        sensor_info: dict = None,
        experiment_name: str = None,
        sensor_platform_name: str = None
    ) -> Optional["Sensor"]:
        """
        Create a new sensor.

        Examples:
            >>> sensor = Sensor.create(sensor_name="Temperature Sensor", sensor_type=GEMINISensorType.Temperature, sensor_data_type=GEMINIDataType.Float, sensor_data_format=GEMINIDataFormat.JSON)
            >>> print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

        Args:
            sensor_name (str): The name of the sensor.
            sensor_type (GEMINISensorType, optional): The type of the sensor. Defaults to Default.
            sensor_data_type (GEMINIDataType, optional): The data type. Defaults to Default.
            sensor_data_format (GEMINIDataFormat, optional): The data format. Defaults to Default.
            sensor_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
            sensor_platform_name (str, optional): The name of the sensor platform to associate. Defaults to None.
        Returns:
            Optional[Sensor]: The created sensor, or None if an error occurred.
        """
        try:
            sensor_type_id = sensor_type.value
            sensor_data_format_id = sensor_data_format.value
            sensor_data_type_id = sensor_data_type.value

            db_instance = SensorModel.get_or_create(
                sensor_name=sensor_name,
                sensor_type_id=sensor_type_id,
                sensor_data_type_id=sensor_data_type_id,
                sensor_data_format_id=sensor_data_format_id,
                sensor_info=sensor_info,
            )
            sensor = cls.model_validate(db_instance)
            if experiment_name:
                sensor.associate_experiment(experiment_name=experiment_name)
            if sensor_platform_name:
                sensor.associate_sensor_platform(sensor_platform_name=sensor_platform_name)
            return sensor
        except Exception as e:
            logger.error(f"Error creating sensor: {e}")
            return None
    
    @classmethod
    def get(
        cls,
        sensor_name: str,
        experiment_name: str = None
    ) -> Optional["Sensor"]:
        """
        Retrieve a sensor by its name and experiment.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor", experiment_name="Experiment 1")
            >>> print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

        Args:
            sensor_name (str): The name of the sensor.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Sensor]: The sensor, or None if not found.
        """
        try:
            db_instance = SensorModel.get_by_parameters(
                sensor_name=sensor_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Sensor with name {sensor_name} not found.")
                return None
            sensor = cls.model_validate(db_instance)
            return sensor
        except Exception as e:
            logger.error(f"Error getting sensor: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Sensor"]:
        """
        Retrieve a sensor by its ID.

        Examples:
            >>> sensor = Sensor.get_by_id(id=UUID('...'))
            >>> print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

        Args:
            id (UUID | int | str): The ID of the sensor.
        Returns:
            Optional[Sensor]: The sensor, or None if not found.
        """
        try:
            db_instance = SensorModel.get(id)
            if not db_instance:
                logger.warning(f"Sensor with ID {id} does not exist.")
                return None
            sensor = cls.model_validate(db_instance)
            return sensor
        except Exception as e:
            logger.error(f"Error getting sensor by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Sensor"]]:
        """
        Retrieve all sensors.

        Examples:
            >>> sensors = Sensor.get_all()
            >>> for sensor in sensors:
            ...     print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))
            Sensor(sensor_name=Humidity Sensor, sensor_type_id=2, sensor_data_type_id=2, sensor_data_format_id=2, id=UUID('...'))

        Returns:
            Optional[List[Sensor]]: List of all sensors, or None if not found.
        """
        try:
            sensors = SensorModel.all(limit=limit, offset=offset)
            if not sensors or len(sensors) == 0:
                logger.info("No sensors found.")
                return None
            sensors = [cls.model_validate(sensor) for sensor in sensors]
            return sensors
        except Exception as e:
            logger.error(f"Error getting all sensors: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        sensor_name: str = None,
        sensor_type: GEMINISensorType = None,
        sensor_data_type: GEMINIDataType = None,
        sensor_data_format: GEMINIDataFormat = None,
        sensor_info: dict = None,
        experiment_name: str = None,
        sensor_platform_name: str = None
    ) -> Optional[List["Sensor"]]:
        """
        Search for sensors based on various criteria.

        Examples:
            >>> sensors = Sensor.search(sensor_name="Temperature Sensor")
            >>> for sensor in sensors:
            ...     print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

            >>> sensors = Sensor.search(sensor_type=GEMINISensorType.Temperature)
            >>> for sensor in sensors:
            ...     print(sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))
            

        Args:
            sensor_name (str, optional): The name of the sensor. Defaults to None.
            sensor_type (GEMINISensorType, optional): The type of the sensor. Defaults to None.
            sensor_data_type (GEMINIDataType, optional): The data type. Defaults to None.
            sensor_data_format (GEMINIDataFormat, optional): The data format. Defaults to None.
            sensor_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            sensor_platform_name (str, optional): The name of the sensor platform. Defaults to None.
        Returns:
            Optional[List[Sensor]]: List of matching sensors, or None if not found.
        """
        try:
            if not any([sensor_name, sensor_type, sensor_data_type, sensor_data_format, sensor_info, experiment_name, sensor_platform_name]):
                logger.info("Must provide at least one search parameter.")
                return None
            sensors = ExperimentSensorsViewModel.search(
                sensor_name=sensor_name,
                sensor_type=sensor_type.value if sensor_type else None,
                sensor_data_type=sensor_data_type.value if sensor_data_type else None,
                sensor_data_format=sensor_data_format.value if sensor_data_format else None,
                sensor_info=sensor_info,
                experiment_name=experiment_name,
                sensor_platform_name=sensor_platform_name
            )
            if not sensors or len(sensors) == 0:
                logger.info("No sensors found with the provided search parameters.")
                return None
            sensors = [cls.model_validate(sensor) for sensor in sensors]
            return sensors
        except Exception as e:
            logger.error(f"Error searching sensors: {e}")
            return None
        
    def update(
        self,
        sensor_name: str = None, 
        sensor_type: GEMINISensorType = None,
        sensor_data_type: GEMINIDataType = None,
        sensor_data_format: GEMINIDataFormat = None,
        sensor_info: dict = None
    ) -> Optional["Sensor"]:
        """
        Update the details of the sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> updated_sensor = sensor.update(sensor_name="New Temperature Sensor", sensor_type=GEMINISensorType.Humidity)
            >>> print(updated_sensor)
            Sensor(sensor_name=New Temperature Sensor, sensor_type_id=2, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

        Args:
            sensor_name (str, optional): The new name. Defaults to None.
            sensor_type (GEMINISensorType, optional): The new type. Defaults to None.
            sensor_data_type (GEMINIDataType, optional): The new data type. Defaults to None.
            sensor_data_format (GEMINIDataFormat, optional): The new data format. Defaults to None.
            sensor_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[Sensor]: The updated sensor, or None if an error occurred.
        """
        try:
            if not any([sensor_type, sensor_data_type, sensor_data_format, sensor_info, sensor_name]):
                logger.warning("At least one update parameter must be provided.")
                return None

            current_id = self.id
            sensor = SensorModel.get(current_id)
            if not sensor:
                logger.warning(f"Sensor with ID {current_id} does not exist.")
                return None
            
            sensor = SensorModel.update(
                sensor,
                sensor_name=sensor_name,
                sensor_type_id=sensor_type.value if sensor_type else None,
                sensor_data_type_id=sensor_data_type.value if sensor_data_type else None,
                sensor_data_format_id=sensor_data_format.value if sensor_data_format else None,
                sensor_info=sensor_info
            )
            updated_sensor = self.model_validate(sensor)
            self.refresh()
            return updated_sensor
        except Exception as e:
            logger.error(f"Error updating sensor: {e}")
            return None
    
    def delete(self) -> bool:
        """
        Delete the sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> success = sensor.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the sensor was deleted, False otherwise.
        """
        try:
            current_id = self.id
            sensor = SensorModel.get(current_id)
            if not sensor:
                logger.warning(f"Sensor with ID {current_id} does not exist.")
                return False
            SensorModel.delete(sensor)
            return True
        except Exception as e:
            logger.error(f"Error deleting sensor: {e}")
            return False
        
    def refresh(self) -> Optional["Sensor"]:
        """
        Refresh the sensor's data from the database.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> refreshed_sensor = sensor.refresh()
            >>> print(refreshed_sensor)
            Sensor(sensor_name=Temperature Sensor, sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1, id=UUID('...'))

        Returns:
            Optional[Sensor]: The refreshed sensor, or None if an error occurred.
        """
        try:
            db_instance = SensorModel.get(self.id)
            if not db_instance:
                logger.warning(f"Sensor with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    actual_value = getattr(instance, key)
                    setattr(self, key, actual_value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing sensor: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> sensor_info = sensor.get_info()
            >>> print(sensor_info)
            {'manufacturer': 'SensorCorp', 'model': 'TempX1000', 'calibration_date': '2023-01-01'}

        Returns:
            Optional[dict]: The sensor's info, or None if not found.
        """
        try:
            current_id = self.id
            sensor = SensorModel.get(current_id)
            if not sensor:
                logger.warning(f"Sensor with ID {current_id} does not exist.")
                return None
            sensor_info = sensor.sensor_info
            if not sensor_info:
                logger.info("Sensor info is empty.")
                return None
            return sensor_info
        except Exception as e:
            logger.error(f"Error getting sensor info: {e}")
            return None
        
    def set_info(self, sensor_info: dict) -> Optional["Sensor"]:
        """
        Set the additional information of the sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> updated_sensor = sensor.set_info(sensor_info={'manufacturer': 'SensorCorp', 'model': 'TempX1000'})
            >>> print(updated_sensor.get_info())
            {'manufacturer': 'SensorCorp', 'model': 'TempX1000'}

        Args:
            sensor_info (dict): The new information to set.
        Returns:
            Optional[Sensor]: The updated sensor, or None if an error occurred.
        """
        try:
            current_id = self.id
            sensor = SensorModel.get(current_id)
            if not sensor:
                logger.warning(f"Sensor with ID {current_id} does not exist.")
                return None
            sensor = SensorModel.update(
                sensor,
                sensor_info=sensor_info
            )
            sensor = self.model_validate(sensor)
            self.refresh()
            return sensor
        except Exception as e:
            logger.error(f"Error setting sensor info: {e}")
            return None

    def get_associated_sensor_platforms(self) -> Optional[List["SensorPlatform"]]:
        """
        Get all sensor platforms associated with this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> sensor_platforms = sensor.get_associated_sensor_platforms()
            >>> for platform in sensor_platforms:
            ...     print(platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID('...'))
            SensorPlatform(sensor_platform_name=Platform 2, id=UUID('...'))

        Returns:
            Optional[List[SensorPlatform]]: A list of associated sensor platforms, or None if not found.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platforms = SensorPlatformSensorsViewModel.search(sensor_id=self.id)
            if not sensor_platforms or len(sensor_platforms) == 0:
                logger.info("No associated sensor platforms found.")
                return None
            sensor_platforms = [SensorPlatform.model_validate(sensor_platform) for sensor_platform in sensor_platforms]
            return sensor_platforms
        except Exception as e:
            logger.error(f"Error getting associated sensor platforms: {e}")
            return None

    def associate_sensor_platform(self, sensor_platform_name: str) -> Optional["SensorPlatform"]:
        """
        Associate this sensor with a sensor platform.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> sensor_platform = sensor.associate_sensor_platform(sensor_platform_name="Platform 1")
            >>> print(sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID('...'))

        Args:
            sensor_platform_name (str): The name of the sensor platform to associate.
        Returns:
            Optional[SensorPlatform]: The associated sensor platform, or None if an error occurred.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.warning(f"Sensor platform {sensor_platform_name} does not exist.")
                return None
            existing_association = SensorPlatformSensorModel.get_by_parameters(
                sensor_platform_id=sensor_platform.id,
                sensor_id=self.id
            )
            if existing_association:
                logger.info(f"Sensor {self.sensor_name} already associated with sensor platform {sensor_platform_name}.")
                return None
            new_association = SensorPlatformSensorModel.get_or_create(
                sensor_platform_id=sensor_platform.id,
                sensor_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate sensor {self.sensor_name} with sensor platform {sensor_platform_name}.")
                return None
            self.refresh()
            return sensor_platform
        except Exception as e:
            logger.error(f"Error associating sensor platform: {e}")
            return None

    def unassociate_sensor_platform(self, sensor_platform_name: str) -> Optional["SensorPlatform"]:
        """
        Unassociate this sensor from a sensor platform.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> sensor_platform = sensor.unassociate_sensor_platform(sensor_platform_name="Platform 1")
            >>> print(sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID('...'))

        Args:
            sensor_platform_name (str): The name of the sensor platform to unassociate.
        Returns:
            Optional[SensorPlatform]: The unassociated sensor platform, or None if an error occurred.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.warning(f"Sensor platform {sensor_platform_name} does not exist.")
                return None
            existing_association = SensorPlatformSensorModel.get_by_parameters(
                sensor_platform_id=sensor_platform.id,
                sensor_id=self.id
            )
            if not existing_association:
                logger.info(f"Sensor {self.sensor_name} not associated with sensor platform {sensor_platform_name}.")
                return None
            is_deleted = SensorPlatformSensorModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate sensor {self.sensor_name} from sensor platform {sensor_platform_name}.")
                return None
            self.refresh()
            return sensor_platform
        except Exception as e:
            logger.error(f"Error unassociating sensor platform: {e}")
            return None

    def belongs_to_sensor_platform(self, sensor_platform_name: str) -> bool:
        """
        Check if this sensor is associated with a specific sensor platform.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> is_associated = sensor.belongs_to_sensor_platform(sensor_platform_name="Platform 1")
            >>> print(is_associated)
            True

        Args:
            sensor_platform_name (str): The name of the sensor platform to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.warning(f"Sensor platform {sensor_platform_name} does not exist.")
                return False
            association_exists = SensorPlatformSensorModel.exists(
                sensor_platform_id=sensor_platform.id,
                sensor_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking sensor platform membership: {e}")
            return

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> experiments = sensor.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID('...'))
            Experiment(experiment_name=Experiment 2, experiment_start_date='2023-06-01', experiment_end_date='2023-11-30', id=UUID('...'))

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            experiments = ExperimentSensorsViewModel.search(sensor_id=self.id)
            if not experiments or len(experiments) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiments]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this sensor with an experiment.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> experiment = sensor.associate_experiment(experiment_name="Experiment 1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID('...'))

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional[Experiment]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentSensorModel.get_by_parameters(
                experiment_id=experiment.id,
                sensor_id=self.id
            )
            if existing_association:
                logger.info(f"Sensor {self.sensor_name} already associated with experiment {experiment_name}.")
                return None
            new_association = ExperimentSensorModel.get_or_create(
                experiment_id=experiment.id,
                sensor_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate sensor {self.sensor_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this sensor from an experiment.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> experiment = sensor.unassociate_experiment(experiment_name="Experiment 1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID('...'))

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentSensorModel.get_by_parameters(
                experiment_id=experiment.id,
                sensor_id=self.id
            )
            if not existing_association:
                logger.info(f"Sensor {self.sensor_name} not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentSensorModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate sensor {self.sensor_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this sensor is associated with a specific experiment.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> is_associated = sensor.belongs_to_experiment(experiment_name="Experiment 1")
            >>> print(is_associated)
            True

        Args:
            experiment_name (str): The name of the experiment to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentSensorModel.exists(
                experiment_id=experiment.id,
                sensor_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking experiment membership: {e}")
            return False

    def get_associated_datasets(self) -> Optional[List["Dataset"]]:
        """
        Get all datasets associated with this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> datasets = sensor.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name=Dataset 1, dataset_type=Sensor, collection_date='2023-01-01', id=UUID('...'))
            Dataset(dataset_name=Dataset 2, dataset_type=Sensor, collection_date='2023-06-01', id=UUID('...'))

        Returns:
            Optional[List[Dataset]]: A list of associated datasets, or None if not found.
        """
        try:
            datasets = SensorDatasetsViewModel.search(sensor_id=self.id)
            if not datasets or len(datasets) == 0:
                logger.info("No associated datasets found.")
                return None
            datasets = [Dataset.model_validate(dataset) for dataset in datasets]
            return datasets
        except Exception as e:
            logger.error(f"Error getting associated datasets: {e}")
            return None

    def create_new_dataset(
        self,
        dataset_name: str,
        dataset_info: dict = None,
        collection_date: date = None,
        experiment_name: str = None
    ) -> Optional["Dataset"]:
        """
        Create and associate a new dataset with this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> dataset = sensor.create_new_dataset(dataset_name="New Sensor Dataset", collection_date=date(2023, 1, 1), experiment_name="Experiment 1")
            >>> print(dataset)
            Dataset(dataset_name=New Sensor Dataset, dataset_type=Sensor, collection_date='2023-01-01', id=UUID('...'))

        Args:
            dataset_name (str): The name of the new dataset.
            dataset_info (dict, optional): Additional information. Defaults to {{}}.
            collection_date (date, optional): The collection date. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Dataset]: The created and associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.create(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                collection_date=collection_date,
                experiment_name=experiment_name,
                dataset_type=GEMINIDatasetType.Sensor
            )
            if not dataset:
                logger.info("Failed to create new dataset.")
                return None
            dataset = self.associate_dataset(dataset_name=dataset.dataset_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating new dataset: {e}")
            return None

    def associate_dataset(self, dataset_name: str) -> Optional["Dataset"]:
        """
        Associate this sensor with a dataset.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> dataset = sensor.associate_dataset(dataset_name="Sensor Dataset 1")
            >>> print(dataset)
            Dataset(dataset_name=Sensor Dataset 1, dataset_type=Sensor, collection_date='2023-01-01', id=UUID('...'))

        Args:
            dataset_name (str): The name of the dataset to associate.
        Returns:
            Optional[Dataset]: The associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name=dataset_name)
            if not dataset:
                logger.warning(f"Dataset {dataset_name} does not exist.")
                return None
            existing_association = SensorDatasetModel.get_by_parameters(
                dataset_id=dataset.id,
                sensor_id=self.id
            )
            if existing_association:
                logger.info(f"Sensor {self.sensor_name} already associated with dataset {dataset_name}.")
                return None
            new_association = SensorDatasetModel.get_or_create(
                dataset_id=dataset.id,
                sensor_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate sensor {self.sensor_name} with dataset {dataset_name}.")
                return None
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error associating dataset: {e}")
            return None
        
    def insert_record(
        self,
        timestamp: datetime = None,
        collection_date: date = None,
        dataset_name: str = None,
        sensor_data: dict = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = -1,
        plot_row_number: int = -1,
        plot_column_number: int = -1,
        record_file: str = None,
        record_info: dict = None
    ) -> tuple[bool, List[str]]:
        """
        Insert a single sensor record for this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> success, record_ids = sensor.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="Sensor Dataset 1",
            ...     sensor_data={"temperature": 22.5},
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring",
            ...     site_name="Site A",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_file=None,
            ...     record_info={"notes": "First record"}
            ... )
            >>> print(success, record_ids)
            True [UUID('...')]

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            sensor_data (dict, optional): The sensor data. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to -1.
            plot_row_number (int, optional): The plot row number. Defaults to -1.
            plot_column_number (int, optional): The plot column number. Defaults to -1.
            record_file (str, optional): The file path or URI. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name or not season_name or not site_name:
                raise ValueError("Experiment name, season name, and site name must be provided.")
            
            if not sensor_data and not record_file:
                raise ValueError("Either sensor_data or record_file must be provided.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            sensor_name = self.sensor_name

            if not dataset_name:
                dataset_name = f"{sensor_name} Dataset {collection_date}"

            sensor_record = SensorRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                sensor_name=sensor_name,
                sensor_data=sensor_data,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number if plot_number != -1 else None,
                plot_row_number=plot_row_number if plot_row_number != -1 else None,
                plot_column_number=plot_column_number if plot_column_number != -1 else None,
                record_file=record_file if record_file else None,
                record_info=record_info if record_info else {},
                insert_on_create=False
            )
            success, inserted_record_ids = SensorRecord.insert([sensor_record])
            if not success:
                logger.info("Failed to insert sensor record.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting sensor record: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        sensor_data: List[dict] = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_numbers: List[int] = None,
        plot_row_numbers: List[int] = None,
        plot_column_numbers: List[int] = None,
        record_files: List[str] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Insert multiple sensor records for this sensor.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> success, record_ids = sensor.insert_records(
            ...     timestamps=[datetime.now(), datetime.now()],
            ...     collection_date=date(2023, 1, 1),
            ...     sensor_data=[{"temperature": 22.5}, {"temperature": 23.0}],
            ...     dataset_name="Sensor Dataset 1",
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring",
            ...     site_name="Site A",
            ...     plot_numbers=[1, 2],
            ...     plot_row_numbers=[1, 2],
            ...     plot_column_numbers=[1, 2],
            ...     record_files=None,
            ...     record_info=[{"notes": "First record"}, {"notes": "Second record"}]
            ... )
            >>> print(success, record_ids)
            True [UUID('...'), UUID('...')]

        Args:
            timestamps (List[datetime], optional): List of timestamps. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            sensor_data (List[dict], optional): List of sensor data. Defaults to [].
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_numbers (List[int], optional): List of plot numbers. Defaults to None.
            plot_row_numbers (List[int], optional): List of plot row numbers. Defaults to None.
            plot_column_numbers (List[int], optional): List of plot column numbers. Defaults to None.
            record_files (List[str], optional): List of file paths or URIs. Defaults to None.
            record_info (List[dict], optional): List of additional info. Defaults to [].
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name or not season_name or not site_name:
                raise ValueError("Experiment name, season name, and site name must be provided.")
            
            if len(timestamps) == 0:
                raise ValueError("At least one timestamp must be provided.")
            
            if not dataset_name:
                dataset_name = f"{self.sensor_name} Dataset {collection_date}"

            collection_date = collection_date if collection_date else timestamps[0].date()
            sensor_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Sensor: " + self.sensor_name):
                sensor_record = SensorRecord.create(
                    timestamp=timestamps[i],
                    collection_date=collection_date,
                    sensor_name=self.sensor_name,
                    sensor_data=sensor_data[i] if sensor_data else {},
                    experiment_name=experiment_name,
                    dataset_name=dataset_name if dataset_name else f"{self.sensor_name} Dataset",
                    season_name=season_name,
                    site_name=site_name,
                    plot_number=plot_numbers[i] if plot_numbers else None,
                    plot_row_number=plot_row_numbers[i] if plot_row_numbers else None,
                    plot_column_number=plot_column_numbers[i] if plot_column_numbers else None,
                    record_file=record_files[i] if record_files else None,
                    record_info=record_info[i] if record_info else {},
                    insert_on_create=False
                )
                sensor_records.append(sensor_record)

            success, inserted_record_ids = SensorRecord.insert(sensor_records)
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting sensor records: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        record_info: dict = None
    ) -> List[SensorRecord]:
        """
        Search for sensor records associated with this sensor based on search parameters.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> records = sensor.search_records(
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="Sensor Dataset 1",
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring",
            ...     site_name="Site A",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_info={"notes": "First record"}
            ... )
            >>> for record in records:
            ...     print(record)
            SensorRecord(id=UUID('...'), sensor_name='Temperature Sensor', timestamp='2023-01-01T00:00:00', dataset_name='Sensor Dataset 1', experiment_name='Experiment 1', season_name='Spring', site_name='Site A', plot_number=1)
            SensorRecord(id=UUID('...'), sensor_name='Temperature Sensor', timestamp='2023-01-01T00:00:00', dataset_name='Sensor Dataset 1', experiment_name='Experiment 1', season_name='Spring', site_name='Site A', plot_number=2)

        Args:
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Returns:
            List[SensorRecord]: List of matching sensor records, or empty list if not found.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = SensorRecord.search(
                sensor_name=self.sensor_name,
                collection_date=collection_date,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching sensor records: {e}")
            return []
        
    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> List[SensorRecord]:
        """
        Filter sensor records associated with this sensor using a custom filter function.

        Examples:
            >>> sensor = Sensor.get(sensor_name="Temperature Sensor")
            >>> records = sensor.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     dataset_names=["Sensor Dataset 1"],
            ...     experiment_names=["Experiment 1"],
            ...     season_names=["Spring"],
            ...     site_names=["Site A"]
            ... )
            >>> for record in records:
            ...     print(record)
            SensorRecord(id=UUID('...'), sensor_name='Temperature Sensor', timestamp='2023-01-01T00:00:00', dataset_name='Sensor Dataset 1', experiment_name='Experiment 1', season_name='Spring', site_name='Site A', plot_number=1)
            SensorRecord(id=UUID('...'), sensor_name='Temperature Sensor', timestamp='2023-01-01T00:00:00', dataset_name='Sensor Dataset 1', experiment_name='Experiment 1', season_name='Spring', site_name='Site A', plot_number=2)


        Args:
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
        Returns:
            List[SensorRecord]: List of filtered sensor records, or empty list if not found.
        """
        try:
            records = SensorRecord.filter(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                sensor_names=[self.sensor_name],
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering sensor records: {e}")
            return []



