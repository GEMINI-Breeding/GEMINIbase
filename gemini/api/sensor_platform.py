"""
This module defines the SensorPlatform class, which represents a sensor platform entity, including its metadata, associations to sensors and experiments, and related operations.

It includes methods for creating, retrieving, updating, and deleting sensor platforms, as well as methods for checking existence, searching, and managing associations with sensors and experiments.

This module includes the following methods:

- `exists`: Check if a sensor platform with the given name exists.
- `create`: Create a new sensor platform.
- `get`: Retrieve a sensor platform by its name and experiment.
- `get_by_id`: Retrieve a sensor platform by its ID.
- `get_all`: Retrieve all sensor platforms.
- `search`: Search for sensor platforms based on various criteria.
- `update`: Update the details of a sensor platform.
- `delete`: Delete a sensor platform.
- `refresh`: Refresh the sensor platform's data from the database.
- `get_info`: Get the additional information of the sensor platform.
- `set_info`: Set the additional information of the sensor platform.
- Association methods for sensors and experiments.

"""

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.sensor import Sensor, GEMINIDataFormat, GEMINIDataType, GEMINISensorType
from gemini.db.models.associations import ExperimentSensorPlatformModel, SensorPlatformSensorModel
from gemini.db.models.sensor_platforms import SensorPlatformModel
from gemini.db.models.views.experiment_views import ExperimentSensorPlatformsViewModel
from gemini.db.models.views.sensor_platform_sensors_view import SensorPlatformSensorsViewModel

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.sensor import Sensor

logger = logging.getLogger(__name__)

class SensorPlatform(APIBase):
    """
    Represents a sensor platform entity, including its metadata, associations to sensors and experiments, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the sensor platform.
        sensor_platform_name (str): The name of the sensor platform.
        sensor_platform_info (Optional[dict]): Additional information about the sensor platform.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "sensor_platform_id"))

    sensor_platform_name: str
    sensor_platform_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the SensorPlatform object."""
        return f"SensorPlatform(id={self.id}, sensor_platform_name={self.sensor_platform_name})"
    
    def __repr__(self):
        """Return a detailed string representation of the SensorPlatform object."""
        return f"SensorPlatform(id={self.id}, sensor_platform_name={self.sensor_platform_name})"
    
    @classmethod
    def exists(
        cls,
        sensor_platform_name: str,
    ) -> bool:
        """
        Check if a sensor platform with the given name exists.

        Examples:
            >>> SensorPlatform.exists(sensor_platform_name="MySensorPlatform")
            True
            >>> SensorPlatform.exists(sensor_platform_name="NonExistentPlatform")
            False

        Args:
            sensor_platform_name (str): The name of the sensor platform.
        Returns:
            bool: True if the sensor platform exists, False otherwise.
        """
        try:
            exists = SensorPlatformModel.exists(sensor_platform_name=sensor_platform_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of SensorPlatform: {e}")
            return False
    
    @classmethod
    def create(
        cls,
        sensor_platform_name: str,
        sensor_platform_info: dict = None,
        experiment_name: str = None
    ) -> Optional["SensorPlatform"]:
        """
        Create a new sensor platform.

        Examples:
            >>> SensorPlatform.create(sensor_platform_name="MySensorPlatform")
            SensorPlatform(id=UUID(...), sensor_platform_name="MySensorPlatform")

        Args:
            sensor_platform_name (str): The name of the sensor platform.
            sensor_platform_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[SensorPlatform]: The created sensor platform, or None if an error occurred.
        """
        try:
            db_instance = SensorPlatformModel.get_or_create(
                sensor_platform_name=sensor_platform_name,
                sensor_platform_info=sensor_platform_info,
            )
            sensor_platform = cls.model_validate(db_instance)
            if experiment_name:
                sensor_platform.associate_experiment(experiment_name=experiment_name)
            return sensor_platform
        except Exception as e:
            logger.error(f"Error creating SensorPlatform: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        sensor_platform_name: str,
        experiment_name: str = None
    ) -> Optional["SensorPlatform"]:
        """
        Retrieve a sensor platform by its name and experiment.

        Examples:
            >>> SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            SensorPlatform(id=UUID(...), sensor_platform_name="MySensorPlatform")

        Args:
            sensor_platform_name (str): The name of the sensor platform.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[SensorPlatform]: The sensor platform, or None if not found.
        """
        try:
            db_instance = ExperimentSensorPlatformsViewModel.get_by_parameters(
                sensor_platform_name=sensor_platform_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"SensorPlatform with name {sensor_platform_name} not found.")
                return None
            sensor_platform = cls.model_validate(db_instance)
            return sensor_platform
        except Exception as e:
            logger.error(f"Error retrieving SensorPlatform: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["SensorPlatform"]:
        """
        Retrieve a sensor platform by its ID.

        Examples:
            >>> SensorPlatform.get_by_id(UUID('...'))
            SensorPlatform(id=UUID(...), sensor_platform_name="MySensorPlatform")

        Args:
            id (UUID | int | str): The ID of the sensor platform.
        Returns:
            Optional[SensorPlatform]: The sensor platform, or None if not found.
        """
        try:
            db_instance = SensorPlatformModel.get(id)
            if not db_instance:
                logger.debug(f"SensorPlatform with ID {id} not found.")
                return None
            sensor_platform = cls.model_validate(db_instance)
            return sensor_platform
        except Exception as e:
            logger.error(f"Error retrieving SensorPlatform by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["SensorPlatform"]]:
        """
        Retrieve all sensor platforms.

        Examples:
            >>> SensorPlatform.get_all()
            [SensorPlatform(id=UUID(...), sensor_platform_name="Platform1"), SensorPlatform(id=UUID(...), sensor_platform_name="Platform2")]

        Returns:
            Optional[List[SensorPlatform]]: List of all sensor platforms, or None if not found.
        """
        try:
            sensor_platforms = SensorPlatformModel.all(limit=limit, offset=offset)
            if not sensor_platforms or len(sensor_platforms) == 0:
                logger.info("No SensorPlatforms found.")
                return None
            sensor_platforms = [cls.model_validate(sp) for sp in sensor_platforms]
            return sensor_platforms
        except Exception as e:
            logger.error(f"Error retrieving all SensorPlatforms: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        sensor_platform_name: str = None,
        sensor_platform_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["SensorPlatform"]]:
        """
        Search for sensor platforms based on various criteria.

        Examples:
            >>> SensorPlatform.search(sensor_platform_name="MySensorPlatform")
            [SensorPlatform(id=UUID(...), sensor_platform_name="MySensorPlatform")]


        Args:
            sensor_platform_name (str, optional): The name of the sensor platform. Defaults to None.
            sensor_platform_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List[SensorPlatform]]: List of matching sensor platforms, or None if not found.
        """
        try:
            if not any([sensor_platform_name, sensor_platform_info, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            instances = ExperimentSensorPlatformsViewModel.search(
                sensor_platform_name=sensor_platform_name,
                sensor_platform_info=sensor_platform_info,
                experiment_name=experiment_name
            )
            if not instances or len(instances) == 0:
                logger.info("No SensorPlatforms found matching the search criteria.")
                return None
            sensor_platforms = [cls.model_validate(instance) for instance in instances]
            return sensor_platforms
        except Exception as e:
            logger.error(f"Error searching SensorPlatforms: {e}")
            return None
        
    def update(
        self,
        sensor_platform_name: str = None,
        sensor_platform_info: dict = None
    ) -> Optional["SensorPlatform"]:
        """
        Update the details of the sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> updated_platform = sensor_platform.update(sensor_platform_name="UpdatedPlatformName")
            SensorPlatform(id=UUID(...), sensor_platform_name="UpdatedPlatformName")

        Args:
            sensor_platform_name (str, optional): The new name. Defaults to None.
            sensor_platform_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[SensorPlatform]: The updated sensor platform, or None if an error occurred.
        """
        try:
            if not any([sensor_platform_name, sensor_platform_info]):
                logger.warning("At least one update parameter must be provided.")
                return None
            current_id = self.id
            platform = SensorPlatformModel.get(current_id)
            if not platform:
                logger.debug(f"SensorPlatform with ID {current_id} not found.")
                return None
            platform = SensorPlatformModel.update(
                platform, 
                sensor_platform_info=sensor_platform_info,
                sensor_platform_name=sensor_platform_name
            )
            platform = self.model_validate(platform)
            self.refresh()
            return platform
        except Exception as e:
            logger.error(f"Error updating SensorPlatform: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> sensor_platform.delete()
            True

        Returns:
            bool: True if the sensor platform was deleted, False otherwise.
        """
        try:
            current_id = self.id
            platform = SensorPlatformModel.get(current_id)
            if not platform:
                logger.debug(f"SensorPlatform with ID {current_id} not found.")
                return False
            SensorPlatformModel.delete(platform)
            return True
        except Exception as e:
            logger.error(f"Error deleting SensorPlatform: {e}")
            return False
        
    def refresh(self) -> Optional["SensorPlatform"]:
        """
        Refresh the sensor platform's data from the database.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> sensor_platform.refresh()
            SensorPlatform(id=UUID(...), sensor_platform_name="MySensorPlatform")

        Returns:
            Optional[SensorPlatform]: The refreshed sensor platform, or None if an error occurred.
        """
        try:
            db_instance = SensorPlatformModel.get(self.id)
            if not db_instance:
                logger.debug(f"SensorPlatform with ID {self.id} not found.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing SensorPlatform: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> info = sensor_platform.get_info()
            {'key1': 'value1', 'key2': 'value2'}

        Returns:
            Optional[dict]: The sensor platform's info, or None if not found.
        """
        try:
            current_id = self.id
            sensor_platform = SensorPlatformModel.get(current_id)
            if not sensor_platform:
                logger.debug(f"SensorPlatform with ID {current_id} not found.")
                return None
            sensor_platform_info = sensor_platform.sensor_platform_info
            if not sensor_platform_info:
                logger.info("SensorPlatform info is empty.")
                return None
            return sensor_platform_info
        except Exception as e:
            logger.error(f"Error retrieving SensorPlatform info: {e}")
            return None
        
    def set_info(self, sensor_platform_info: dict) -> Optional["SensorPlatform"]:
        """
        Set the additional information of the sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> updated_platform = sensor_platform.set_info({'key1': 'value1', 'key2': 'value2'})
            >>> updated_platform.get_info()
            {'key1': 'value1', 'key2': 'value2'}
            
        Args:
            sensor_platform_info (dict): The new information to set.
        Returns:
            Optional[SensorPlatform]: The updated sensor platform, or None if an error occurred.
        """
        try:
            current_id = self.id
            sensor_platform = SensorPlatformModel.get(current_id)
            if not sensor_platform:
                logger.debug(f"SensorPlatform with ID {current_id} not found.")
                return None
            sensor_platform = SensorPlatformModel.update(
                sensor_platform,
                sensor_platform_info=sensor_platform_info
            )
            sensor_platform = self.model_validate(sensor_platform)
            self.refresh()
            return self
        except Exception as e:
            logger.error(f"Error setting SensorPlatform info: {e}")
            return None
            
    def get_associated_sensors(self) -> Optional[List["Sensor"]]:
        """
        Get all sensors associated with this sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> sensors = sensor_platform.get_associated_sensors()
            >>> for sensor in sensors:
            ...     print(sensor)
            Sensor(id=UUID(...), sensor_name="Sensor1", sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1)
            Sensor(id=UUID(...), sensor_name="Sensor2", sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1)

        Returns:
            Optional[List[Sensor]]: A list of associated sensors, or None if not found.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor_platform_sensors = SensorPlatformSensorsViewModel.search(
                sensor_platform_id=self.id
            )
            if not sensor_platform_sensors or len(sensor_platform_sensors) == 0:
                logger.info(f"No sensors found for SensorPlatform {self.sensor_platform_name}.")
                return None
            sensors = [Sensor.model_validate(sensor) for sensor in sensor_platform_sensors]
            return sensors
        except Exception as e:
            logger.error(f"Error retrieving sensors for SensorPlatform: {e}")
            return None

    def create_new_sensor(
        self,
        sensor_name: str,
        sensor_type: GEMINISensorType = GEMINISensorType.Default,
        sensor_data_type: GEMINIDataType = GEMINIDataType.Default,
        sensor_data_format: GEMINIDataFormat = GEMINIDataFormat.Default,
        sensor_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Sensor"]:
        """
        Create and associate a new sensor with this sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> new_sensor = sensor_platform.create_new_sensor(sensor_name="NewSensor", sensor_type=GEMINISensorType.Default)
            >>> print(new_sensor)
            Sensor(id=UUID(...), sensor_name="NewSensor", sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1)

        Args:
            sensor_name (str): The name of the new sensor.
            sensor_type (GEMINISensorType, optional): The type of the sensor. Defaults to Default.
            sensor_data_type (GEMINIDataType, optional): The data type. Defaults to Default.
            sensor_data_format (GEMINIDataFormat, optional): The data format. Defaults to Default.
            sensor_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Sensor]: The created and associated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            new_sensor = Sensor.create(
                sensor_name=sensor_name,
                sensor_type=sensor_type,
                sensor_data_type=sensor_data_type,
                sensor_data_format=sensor_data_format,
                sensor_info=sensor_info,
                experiment_name=experiment_name,
                sensor_platform_name=self.sensor_platform_name
            )
            if not new_sensor:
                logger.info(f"Failed to create sensor {sensor_name}.")
                return None
            return new_sensor
        except Exception as e:
            logger.error(f"Error creating new sensor for SensorPlatform: {e}")
            return None

    def associate_sensor(self, sensor_name: str) -> Optional["Sensor"]:
        """
        Associate an existing sensor with this sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> sensor = sensor_platform.associate_sensor(sensor_name="ExistingSensor")
            >>> print(sensor)
            Sensor(id=UUID(...), sensor_name="ExistingSensor", sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1)

        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            Optional[Sensor]: The associated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug(f"Sensor {sensor_name} not found.")
                return None
            existing_association = SensorPlatformSensorModel.exists(
                sensor_platform_id=self.id,
                sensor_id=sensor.id
            )
            if existing_association:
                logger.info(f"Sensor {sensor_name} is already associated with SensorPlatform {self.sensor_platform_name}.")
                return None
            new_association = SensorPlatformSensorModel.create(
                sensor_platform_id=self.id,
                sensor_id=sensor.id
            )
            self.refresh()
            return sensor
        except Exception as e:
            logger.error(f"Error associating sensor {sensor_name} with SensorPlatform: {e}")
            return None

    def unassociate_sensor(self, sensor_name: str) -> Optional["Sensor"]:
        """
        Unassociate a sensor from this sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> sensor = sensor_platform.unassociate_sensor(sensor_name="ExistingSensor")
            >>> print(sensor)
            Sensor(id=UUID(...), sensor_name="ExistingSensor", sensor_type_id=1, sensor_data_type_id=1, sensor_data_format_id=1)

        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            Optional[Sensor]: The unassociated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug(f"Sensor {self.sensor_platform_name} not found.")
                return None
            existing_association = SensorPlatformSensorModel.get_by_parameters(
                sensor_platform_id=self.id,
                sensor_id=sensor.id
            )
            if not existing_association:
                logger.info(f"Sensor {self.sensor_platform_name} is not associated with SensorPlatform {self.sensor_platform_name}.")
                return None
            is_deleted = SensorPlatformSensorModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate sensor {self.sensor_platform_name} from SensorPlatform {self.sensor_platform_name}.")
                return None
            self.refresh()
            return sensor
        except Exception as e:
            logger.error(f"Error unassociating sensor {self.sensor_platform_name} from SensorPlatform: {e}")
            return None

    def belongs_to_sensor(self, sensor_name: str) -> bool:
        """
        Check if this sensor platform is associated with a specific sensor.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> is_associated = sensor_platform.belongs_to_sensor(sensor_name="ExistingSensor")
            >>> print(is_associated)
            True

        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug(f"Sensor {sensor_name} not found.")
                return False
            association_exists = SensorPlatformSensorModel.exists(
                sensor_platform_id=self.id,
                sensor_id=sensor.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if SensorPlatform belongs to sensor {sensor_name}: {e}")
            return False

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this sensor platform.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> experiments = sensor_platform.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(id=UUID(...), experiment_name="Experiment1", experiment_start_date="2023-01-01", experiment_end_date="2023-12-31")
            Experiment(id=UUID(...), experiment_name="Experiment2", experiment_start_date="2023-02-01", experiment_end_date="2023-11-30")

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment_sensor_platforms = ExperimentSensorPlatformsViewModel.search(
                sensor_platform_id=self.id
            )
            if not experiment_sensor_platforms or len(experiment_sensor_platforms) == 0:
                logger.info(f"No experiments found for SensorPlatform {self.sensor_platform_name}.")
                return None
            experiments = [Experiment.model_validate(exp) for exp in experiment_sensor_platforms]
            return experiments
        except Exception as e:
            logger.error(f"Error retrieving associated experiments for SensorPlatform: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this sensor platform with an experiment.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> experiment = sensor_platform.associate_experiment(experiment_name="MyExperiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name="MyExperiment", experiment_start_date="2023-01-01", experiment_end_date="2023-12-31")

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional[Experiment]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.debug(f"Experiment {experiment_name} not found.")
                return None
            existing_association = ExperimentSensorPlatformModel.exists(
                sensor_platform_id=self.id,
                experiment_id=experiment.id
            )
            if existing_association:
                logger.info(f"Experiment {experiment_name} is already associated with SensorPlatform {self.sensor_platform_name}.")
                return None
            new_association = ExperimentSensorPlatformModel.create(
                sensor_platform_id=self.id,
                experiment_id=experiment.id
            )
            if not new_association:
                logger.info(f"Failed to associate Experiment {experiment_name} with SensorPlatform {self.sensor_platform_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating Experiment {experiment_name} with SensorPlatform: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this sensor platform from an experiment.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> experiment = sensor_platform.unassociate_experiment(experiment_name="MyExperiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name="MyExperiment", experiment_start_date="2023-01-01", experiment_end_date="2023-12-31")

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.debug(f"Experiment {experiment_name} not found.")
                return None
            existing_association = ExperimentSensorPlatformModel.get_by_parameters(
                sensor_platform_id=self.id,
                experiment_id=experiment.id
            )
            if not existing_association:
                logger.info(f"Experiment {experiment_name} is not associated with SensorPlatform {self.sensor_platform_name}.")
                return None
            is_deleted = ExperimentSensorPlatformModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate Experiment {experiment_name} from SensorPlatform {self.sensor_platform_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating Experiment {experiment_name} from SensorPlatform: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this sensor platform is associated with a specific experiment.

        Examples:
            >>> sensor_platform = SensorPlatform.get(sensor_platform_name="MySensorPlatform")
            >>> is_associated = sensor_platform.belongs_to_experiment(experiment_name="MyExperiment")
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
                logger.debug(f"Experiment {self.sensor_platform_name} not found.")
                return False
            association_exists = ExperimentSensorPlatformModel.exists(
                sensor_platform_id=self.id,
                experiment_id=experiment.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if SensorPlatform belongs to experiment {self.sensor_platform_name}: {e}")
            return False

