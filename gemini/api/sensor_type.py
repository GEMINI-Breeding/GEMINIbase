"""
This module defines the SensorType class, which represents a type or category for sensors.

It includes methods for creating, retrieving, updating, and deleting sensor types, as well as methods for checking existence, searching, and managing additional information.

This module includes the following methods:

- `exists`: Check if a sensor type with the given name exists.
- `create`: Create a new sensor type.
- `get`: Retrieve a sensor type by its name.
- `get_by_id`: Retrieve a sensor type by its ID.
- `get_all`: Retrieve all sensor types.
- `search`: Search for sensor types based on various criteria.
- `update`: Update the details of a sensor type.
- `delete`: Delete a sensor type.
- `refresh`: Refresh the sensor type's data from the database.
- `get_info`: Get the additional information of the sensor type.
- `set_info`: Set the additional information of the sensor type.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.sensor_types import SensorTypeModel

logger = logging.getLogger(__name__)

class SensorType(APIBase):
    """
    Represents a type or category for sensors.

    Attributes:
        id (Optional[ID]): The unique identifier of the sensor type.
        sensor_type_name (str): The name of the sensor type.
        sensor_type_info (Optional[dict]): Additional information about the sensor type.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "sensor_type_id"))

    sensor_type_name: str
    sensor_type_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the SensorType object."""
        return f"SensorType(sensor_type_name={self.sensor_type_name}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the SensorType object."""
        return f"SensorType(sensor_type_name={self.sensor_type_name}, id={self.id})"

    @classmethod
    def exists(
        cls,
        sensor_type_name: str
    ) -> bool:
        """
        Check if a sensor type with the given name exists.

        Examples:
            >>> SensorType.exists("TemperatureSensor")
            True
            >>> SensorType.exists("NonExistentSensor")
            False

        Args:
            sensor_type_name (str): The name of the sensor type.
        Returns:
            bool: True if the sensor type exists, False otherwise.
        """
        try:
            exists = SensorTypeModel.exists(sensor_type_name=sensor_type_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of sensor type: {e}")
            return False

    @classmethod
    def create(
        cls,
        sensor_type_name: str,
        sensor_type_info: dict = None,
    ) -> Optional["SensorType"]:
        """
        Create a new sensor type.

        Examples:
            >>> SensorType.create("TemperatureSensor", {"unit": "Celsius"})
            SensorType(sensor_type_name='TemperatureSensor', id=UUID(...))

        Args:
            sensor_type_name (str): The name of the sensor type.
            sensor_type_info (dict, optional): Additional information about the sensor type. Defaults to {{}}.
        Returns:
            Optional[SensorType]: The created sensor type, or None if an error occurred.
        """
        try:
            db_instance = SensorTypeModel.get_or_create(
                sensor_type_name=sensor_type_name,
                sensor_type_info=sensor_type_info,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating sensor type: {e}")
            return None

    @classmethod
    def get(cls, sensor_type_name: str) -> Optional["SensorType"]:
        """
        Retrieve a sensor type by its name.

        Examples:
            >>> SensorType.get("TemperatureSensor")
            SensorType(sensor_type_name='TemperatureSensor', id=UUID(...))

        Args:
            sensor_type_name (str): The name of the sensor type.
        Returns:
            Optional[SensorType]: The sensor type, or None if not found.
        """
        try:
            db_instance = SensorTypeModel.get_by_parameters(sensor_type_name=sensor_type_name)
            if not db_instance:
                logger.debug(f"Sensor type with name {sensor_type_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting sensor type: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["SensorType"]:
        """
        Retrieve a sensor type by its ID.

        Examples:
            >>> SensorType.get_by_id(UUID('...'))
            SensorType(sensor_type_name='TemperatureSensor', id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the sensor type.
        Returns:
            Optional[SensorType]: The sensor type, or None if not found.
        """
        try:
            db_instance = SensorTypeModel.get(id)
            if not db_instance:
                logger.warning(f"Sensor type with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting sensor type by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["SensorType"]]:
        """
        Retrieve all sensor types.

        Examples:
            >>> SensorType.get_all()
            [SensorType(sensor_type_name='TemperatureSensor', id=UUID(...)), ...]

        Returns:
            Optional[List[SensorType]]: List of all sensor types, or None if not found.
        """
        try:
            instances = SensorTypeModel.all(limit=limit, offset=offset)
            if not instances or len(instances) == 0:
                logger.info("No sensor types found.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error getting all sensor types: {e}")
            return None

    @classmethod
    def search(
        cls,
        sensor_type_name: str = None,
        sensor_type_info: dict = None
    ) -> Optional[List["SensorType"]]:
        """
        Search for sensor types based on various criteria.

        Examples:
            >>> SensorType.search(sensor_type_name="TemperatureSensor")
            [SensorType(sensor_type_name='TemperatureSensor', id=UUID(...))]

        Args:
            sensor_type_name (str, optional): The name of the sensor type. Defaults to None.
            sensor_type_info (dict, optional): Additional information. Defaults to None.
        Returns:
            Optional[List[SensorType]]: List of matching sensor types, or None if not found.
        """
        try:
            if not any([sensor_type_name, sensor_type_info]):
                logger.warning("At least one search parameter must be provided.")
                return None

            instances = SensorTypeModel.search(
                sensor_type_name=sensor_type_name,
                sensor_type_info=sensor_type_info
            )
            if not instances or len(instances) == 0:
                logger.info("No sensor types found with the provided search parameters.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error searching sensor types: {e}")
            return None

    def update(
        self,
        sensor_type_name: str = None,
        sensor_type_info: dict = None,
    ) -> Optional["SensorType"]:
        """
        Update the details of the sensor type.

        Examples:
            >>> sensor_type = SensorType.get("TemperatureSensor")
            >>> sensor_type.update(sensor_type_name="NewTemperatureSensor")
            SensorType(sensor_type_name='NewTemperatureSensor', id=UUID(...))

        Args:
            sensor_type_name (str, optional): The new name. Defaults to None.
            sensor_type_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[SensorType]: The updated sensor type, or None if an error occurred.
        """
        try:
            if not any([sensor_type_name, sensor_type_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            sensor_type = SensorTypeModel.get(current_id)
            if not sensor_type:
                logger.warning(f"Sensor type with ID {current_id} does not exist.")
                return None

            sensor_type = SensorTypeModel.update(
                sensor_type,
                sensor_type_name=sensor_type_name,
                sensor_type_info=sensor_type_info
            )
            instance = self.model_validate(sensor_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating sensor type: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the sensor type.

        Examples:
            >>> sensor_type = SensorType.get("TemperatureSensor")
            >>> sensor_type.delete()
            True

        Returns:
            bool: True if the sensor type was deleted, False otherwise.
        """
        try:
            current_id = self.id
            sensor_type = SensorTypeModel.get(current_id)
            if not sensor_type:
                logger.warning(f"Sensor type with ID {current_id} does not exist.")
                return False
            SensorTypeModel.delete(sensor_type)
            return True
        except Exception as e:
            logger.error(f"Error deleting sensor type: {e}")
            return False

    def refresh(self) -> Optional["SensorType"]:
        """
        Refresh the sensor type's data from the database.

        Examples:
            >>> sensor_type = SensorType.get("TemperatureSensor")
            >>> sensor_type.refresh()
            SensorType(sensor_type_name='TemperatureSensor', id=UUID(...))

        Returns:
            Optional[SensorType]: The refreshed sensor type, or None if an error occurred.
        """
        try:
            db_instance = SensorTypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Sensor type with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing sensor type: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the sensor type.

        Examples:
            >>> sensor_type = SensorType.get("TemperatureSensor")
            >>> sensor_type.get_info()
            {'unit': 'Celsius'}

        Returns:
            Optional[dict]: The sensor type's info, or None if not found.
        """
        try:
            current_id = self.id
            sensor_type = SensorTypeModel.get(current_id)
            if not sensor_type:
                logger.warning(f"Sensor type with ID {current_id} does not exist.")
                return None
            sensor_type_info = sensor_type.sensor_type_info
            if not sensor_type_info:
                logger.info("SensorType info is empty.")
                return None
            return sensor_type_info
        except Exception as e:
            logger.error(f"Error getting sensor type info: {e}")
            return None

    def set_info(self, sensor_type_info: dict) -> Optional["SensorType"]:
        """
        Set the additional information of the sensor type.

        Examples:
            >>> sensor_type = SensorType.get("TemperatureSensor")
            >>> sensor_type.set_info({"unit": "Celsius"})
            >>> sensor_type.get_info()
            {'unit': 'Celsius'}

        Args:
            sensor_type_info (dict): The new information to set.
        Returns:
            Optional[SensorType]: The updated sensor type, or None if an error occurred.
        """
        try:
            current_id = self.id
            sensor_type = SensorTypeModel.get(current_id)
            if not sensor_type:
                logger.warning(f"Sensor type with ID {current_id} does not exist.")
                return None
            sensor_type = SensorTypeModel.update(
                sensor_type,
                sensor_type_info=sensor_type_info,
            )
            instance = self.model_validate(sensor_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting sensor type info: {e}")
            return None
