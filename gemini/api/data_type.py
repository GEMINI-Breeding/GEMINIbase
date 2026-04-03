"""
This module defines the DataType class, which represents a data type for categorizing and describing data.

It includes methods for creating, retrieving, updating, and deleting data types,
as well as methods for checking existence, searching, and managing associations with data formats.

This module includes the following methods:

- `exists`: Check if a data type with the given name exists.
- `create`: Create a new data type.
- `get`: Retrieve a data type by its name.
- `get_by_id`: Retrieve a data type by its ID.
- `get_all`: Retrieve all data types.
- `search`: Search for data types based on various criteria.
- `update`: Update the details of a data type.
- `delete`: Delete a data type.
- `refresh`: Refresh the data type's data from the database.
- `get_info`: Get the additional information of the data type.
- `set_info`: Set the additional information of the data type.
- `get_associated_data_formats`: Get all data formats associated with the data type.
- `associate_data_format`: Associate the data type with a data format.
- `unassociate_data_format`: Unassociate the data type from a data format.
- `belongs_to_data_format`: Check if the data type is associated with a specific data format.
- `add_new_data_format`: Create and associate a new data format with the data type.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.data_types import DataTypeModel
from gemini.db.models.associations import DataTypeFormatModel
from gemini.db.models.views.datatype_format_view import DataTypeFormatsViewModel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gemini.api.data_format import DataFormat  # Avoid circular import issues


logger = logging.getLogger(__name__)

class DataType(APIBase):
    """
    Represents a data type for categorizing and describing data.

    Attributes:
        id (Optional[ID]): The unique identifier of the data type.
        data_type_name (str): The name of the data type (e.g., "Temperature", "Yield").
        data_type_info (Optional[dict]): Additional information about the data type.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "data_type_id"))

    data_type_name: str
    data_type_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the DataType object."""
        return f"DataType(data_type_name={self.data_type_name}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the DataType object."""
        return f"DataType(data_type_name={self.data_type_name}, id={self.id})"

    @classmethod
    def exists(
        cls,
        data_type_name: str
    ) -> bool:
        """
        Check if a data type with the given name exists.

        Examples:
            >>> DataType.exists("Temperature")
            True

        Args:
            data_type_name (str): The name of the data type.
        Returns:
            bool: True if the data type exists, False otherwise.
        """
        try:
            exists = DataTypeModel.exists(data_type_name=data_type_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of data type: {e}")
            return False

    @classmethod
    def create(
        cls,
        data_type_name: str,
        data_type_info: dict = None,
    ) -> Optional["DataType"]:
        """
        Create a new data type. If a data type with the same name already exists, it will return that instance.

        Examples:
            >>> DataType.create("Temperature", {"unit": "Celsius"})
            DataType(data_type_name="Temperature", id=...)

        Args:
            data_type_name (str): The name of the data type.
            data_type_info (dict, optional): Additional information about the data type. Defaults to {{}}.
        Returns:
            Optional["DataType"]: The created data type, or None if an error occurred.
        """
        try:
            db_instance = DataTypeModel.get_or_create(
                data_type_name=data_type_name,
                data_type_info=data_type_info,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating data type: {e}")
            return None

    @classmethod
    def get(cls, data_type_name: str) -> Optional["DataType"]:
        """
        Retrieve a data type by its name.

        Examples:
            >>> DataType.get("Temperature")
            DataType(data_type_name="Temperature", id=...)

        Args:
            data_type_name (str): The name of the data type.
        Returns:
            Optional["DataType"]: The data type, or None if not found.
        """
        try:
            db_instance = DataTypeModel.get_by_parameters(data_type_name=data_type_name)
            if not db_instance:
                logger.debug(f"Data type with name {data_type_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting data type: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["DataType"]:
        """
        Retrieve a data type by its ID.

        Examples:
            >>> DataType.get_by_id(...)  
            DataType(data_type_name="Temperature", id=...)

        Args:
            id (UUID | int | str): The ID of the data type.
        Returns:
            Optional["DataType"]: The data type, or None if not found.
        """
        try:
            db_instance = DataTypeModel.get(id)
            if not db_instance:
                logger.warning(f"Data type with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting data type by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["DataType"]]:
        """
        Retrieve all data types.

        Examples:
            >>> DataType.get_all()
            [DataType(data_type_name="Temperature", id=...), DataType(data_type_name="Yield", id=...)]


        Returns:
            Optional[List["DataType"]]: A list of all data types, or None if an error occurred.
        """
        try:
            instances = DataTypeModel.all(limit=limit, offset=offset)
            if not instances or len(instances) == 0:
                logger.info("No data types found.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error getting all data types: {e}")
            return None

    @classmethod
    def search(
        cls,
        data_type_name: str = None,
        data_type_info: dict = None
    ) -> Optional[List["DataType"]]:
        """
        Search for data types based on various criteria.

        Examples:
            >>> DataType.search(data_type_name="Temperature")
            [DataType(data_type_name="Temperature", id=...)]

        Args:
            data_type_name (str, optional): The name of the data type. Defaults to None.
            data_type_info (dict, optional): Additional information about the data type. Defaults to None.
        Returns:
            Optional[List["DataType"]]: A list of matching data types, or None if an error occurred.
        """
        try:
            if not any([data_type_name, data_type_info]):
                logger.warning("At least one search parameter must be provided.")
                return None

            instances = DataTypeModel.search(
                data_type_name=data_type_name,
                data_type_info=data_type_info
            )
            if not instances or len(instances) == 0:
                logger.info("No data types found with the provided search parameters.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error searching data types: {e}")
            return None

    def update(
        self,
        data_type_name: str = None,
        data_type_info: dict = None,
    ) -> Optional["DataType"]:
        """
        Update the details of the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> updated_data_type = data_type.update(data_type_name="New Temperature", data_type_info={"unit": "Fahrenheit"})
            >>> print(updated_data_type)
            DataType(data_type_name="New Temperature", id=...)

        Args:
            data_type_name (str, optional): The new name of the data type. Defaults to None.
            data_type_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional["DataType"]: The updated data type, or None if an error occurred.
        """
        try:
            if not any([data_type_name, data_type_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            data_type = DataTypeModel.get(current_id)
            if not data_type:
                logger.warning(f"Data type with ID {current_id} does not exist.")
                return None

            data_type = DataTypeModel.update(
                data_type,
                data_type_name=data_type_name,
                data_type_info=data_type_info
            )
            instance = self.model_validate(data_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating data type: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> success = data_type.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the data type was deleted, False otherwise.
        """
        try:
            current_id = self.id
            data_type = DataTypeModel.get(current_id)
            if not data_type:
                logger.warning(f"Data type with ID {current_id} does not exist.")
                return False
            DataTypeModel.delete(data_type)
            return True
        except Exception as e:
            logger.error(f"Error deleting data type: {e}")
            return False

    def refresh(self) -> Optional["DataType"]:
        """
        Refresh the data type's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> refreshed_data_type = data_type.refresh()
            >>> print(refreshed_data_type)
            DataType(data_type_name="Temperature", id=...)

        Returns:
            Optional["DataType"]: The refreshed data type, or None if an error occurred.
        """
        try:
            db_instance = DataTypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Data type with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing data type: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> info = data_type.get_info()
            >>> print(info)
            {"unit": "Celsius"}

        Returns:
            Optional[dict]: The data type's info, or None if not found.
        """
        try:
            current_id = self.id
            data_type = DataTypeModel.get(current_id)
            if not data_type:
                logger.warning(f"Data type with ID {current_id} does not exist.")
                return None
            data_type_info = data_type.data_type_info
            if not data_type_info:
                logger.info("DataType info is empty.")
                return None
            return data_type_info
        except Exception as e:
            logger.error(f"Error getting data type info: {e}")
            return None

    def set_info(self, data_type_info: dict) -> Optional["DataType"]:
        """
        Set the additional information of the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> updated_data_type = data_type.set_info({"unit": "Fahrenheit"})
            >>> print(updated_data_type.data_type_info)
            {"unit": "Fahrenheit"}

        Args:
            data_type_info (dict): The new information to set.
        Returns:
            Optional["DataType"]: The updated data type, or None if an error occurred.
        """
        try:
            current_id = self.id
            data_type = DataTypeModel.get(current_id)
            if not data_type:
                logger.warning(f"Data type with ID {current_id} does not exist.")
                return None
            data_type = DataTypeModel.update(
                data_type,
                data_type_info=data_type_info,
            )
            instance = self.model_validate(data_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting data type info: {e}")
            return None
        
    def get_associated_data_formats(self) -> Optional[List["DataFormat"]]:
        """
        Get all data formats associated with the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> data_formats = data_type.get_associated_data_formats()
            >>> for df in data_formats:
            ...     print(df)
            DataFormat(data_format_name="CSV", data_format_mime_type="text/csv", id=...)
            DataFormat(data_format_name="JSON", data_format_mime_type="application/json", id=...)


        Returns:
            Optional[List["DataFormat"]]: A list of associated data formats, or None if not found.
        """
        try:
            from gemini.api.data_format import DataFormat
            current_id = self.id
            data_type_formats = DataTypeFormatsViewModel.search(data_type_id=current_id)
            if not data_type_formats or len(data_type_formats) == 0:
                logger.info(f"No associated data formats found for data type ID {current_id}.")
                return None
            data_formats = [DataFormat.model_validate(df) for df in data_type_formats]
            return data_formats
        except Exception as e:
            logger.error(f"Error getting associated data formats: {e}")
            return None

    def associate_data_format(self, data_format_name: str) -> Optional["DataType"]:
        """
        Associate the data type with a data format.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> associated_data_format = data_type.associate_data_format("CSV")
            >>> print(associated_data_format)
            DataFormat(data_format_name="CSV", data_format_mime_type="text/csv", id=...)

        Args:
            data_format_name (str): The name of the data format to associate.
        Returns:
            Optional["DataType"]: The associated data format, or None if an error occurred.
        """
        try:
            from gemini.api.data_format import DataFormat
            data_format = DataFormat.get(data_format_name=data_format_name)
            if not data_format:
                logger.warning(f"Data format {data_format_name} does not exist.")
                return None
            existing_association = DataTypeFormatModel.get_by_parameters(
                data_type_id=self.id,
                data_format_id=data_format.id
            )
            if existing_association:
                logger.info(f"Data format {data_format_name} is already associated with data type ID {self.id}.")
                return data_format
            new_association = DataTypeFormatModel.get_or_create(
                data_type_id=self.id,
                data_format_id=data_format.id
            )
            if not new_association:
                logger.info(f"Failed to associate data format {data_format_name} with data type ID {self.id}.")
                return None
            self.refresh()
            return data_format
        except Exception as e:
            logger.error(f"Error associating data format: {e}")
            return None

    def unassociate_data_format(self, data_format_name: str) -> Optional["DataFormat"]:
        """
        Unassociate the data type from a data format.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> unassociated_data_format = data_type.unassociate_data_format("CSV")
            >>> print(unassociated_data_format)
            DataFormat(data_format_name="CSV", data_format_mime_type="text/csv", id=...)

        Args:
            data_format_name (str): The name of the data format to unassociate.
        Returns:
            Optional["DataFormat"]: The unassociated data format, or None if an error occurred.
        """
        try:
            from gemini.api.data_format import DataFormat
            data_format = DataFormat.get(data_format_name=data_format_name)
            if not data_format:
                logger.warning(f"Data format {data_format_name} does not exist.")
                return None
            existing_association = DataTypeFormatModel.get_by_parameters(
                data_type_id=self.id,
                data_format_id=data_format.id
            )
            if not existing_association:
                logger.info(f"Data format {data_format_name} is not associated with data type ID {self.id}.")
                return None
            is_deleted = DataTypeFormatModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate data format {data_format_name} from data type ID {self.id}.")
                return None
            self.refresh()
            return data_format
        except Exception as e:
            logger.error(f"Error unassociating data format: {e}")
            return None

    def belongs_to_data_format(self, data_format_name: str) -> bool:
        """
        Check if the data type is associated with a specific data format.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> is_associated = data_type.belongs_to_data_format("CSV")
            >>> print(is_associated)
            True

        Args:
            data_format_name (str): The name of the data format to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.data_format import DataFormat
            data_format = DataFormat.get(data_format_name=data_format_name)
            if not data_format:
                logger.warning(f"Data format {data_format_name} does not exist.")
                return False
            association_exists = DataTypeFormatModel.exists(
                data_type_id=self.id,
                data_format_id=data_format.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if data type belongs to data format: {e}")
            return False
    
    def add_new_data_format(
        self,
        data_format_name: str,
        data_format_mime_type: str = None,
        data_format_info: dict = None
    ) -> Optional["DataFormat"]:
        """
        Create and associate a new data format with the data type. If the data format already exists,
        it will associate the existing data format with the data type.

        Examples:
            >>> data_type = DataType.get("Temperature")
            >>> new_data_format = data_type.add_new_data_format("NewFormat", "application/newformat", {"description": "A new format"})
            >>> print(new_data_format)
            DataFormat(data_format_name="NewFormat", id=5, data_format_mime_type="application/newformat", id=...)

        Args:
            data_format_name (str): The name of the new data format.
            data_format_mime_type (str, optional): The MIME type of the data format. Defaults to None.
            data_format_info (dict, optional): Additional information about the data format. Defaults to {{}}.
        Returns:
            Optional["DataFormat"]: The created and associated data format, or None if an error occurred.
        """
        try:
            from gemini.api.data_format import DataFormat
            new_data_format = DataFormat.create(
                data_format_name=data_format_name,
                data_format_mime_type=data_format_mime_type,
                data_format_info=data_format_info
            )
            if not new_data_format:
                logger.info(f"Failed to create new data format {data_format_name}.")
                return None
            new_association = DataTypeFormatModel.get_or_create(
                data_type_id=self.id,
                data_format_id=new_data_format.id
            )
            if not new_association:
                logger.info(f"Failed to associate new data format {data_format_name} with data type ID {self.id}.")
                return None
            self.refresh()
            return new_data_format
        except Exception as e:
            logger.error(f"Error adding new data format: {e}")
            return None