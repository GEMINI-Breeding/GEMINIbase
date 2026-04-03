"""
This module defines the DataFormat class, which represents a data format for storing and exchanging data.

It includes methods for creating, retrieving, updating, and deleting data formats,
as well as methods for checking existence, searching, and managing associations with data types.

This module includes the following methods:

- `exists`: Check if a data format with the given name exists.
- `create`: Create a new data format.
- `get`: Retrieve a data format by its name.
- `get_by_id`: Retrieve a data format by its ID.
- `get_all`: Retrieve all data formats.
- `search`: Search for data formats based on various criteria.
- `update`: Update the details of a data format.
- `delete`: Delete a data format.
- `refresh`: Refresh the data format's data from the database.
- `get_info`: Get the additional information of the data format.
- `set_info`: Set the additional information of the data format.
- `get_associated_data_types`: Get all data types associated with the data format.
- `associate_data_type`: Associate the data format with a data type.
- `unassociate_data_type`: Unassociate the data format from a data type.
- `belongs_to_data_type`: Check if the data format is associated with a specific data type

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.data_formats import DataFormatModel
from gemini.db.models.associations import DataTypeFormatModel
from gemini.db.models.views.datatype_format_view import DataTypeFormatsViewModel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gemini.api.data_type import DataType  # Import DataType only if type checking is needed

logger = logging.getLogger(__name__)

class DataFormat(APIBase):
    """
    Represents a data format for storing and exchanging data.

    Attributes:
        id (Optional[ID]): The unique identifier of the data format.
        data_format_name (str): The name of the data format (e.g., "CSV", "JSON").
        data_format_mime_type (Optional[str]): The MIME type of the data format (e.g., "text/csv").
        data_format_info (Optional[dict]): Additional information about the data format.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "data_format_id"))

    data_format_name: str
    data_format_mime_type: Optional[str] = None
    data_format_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the DataFormat object."""
        return f"DataFormat(data_format_name={self.data_format_name}, data_format_mime_type={self.data_format_mime_type}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the DataFormat object."""
        return f"DataFormat(data_format_name={self.data_format_name}, data_format_mime_type={self.data_format_mime_type}, id={self.id})"

    @classmethod
    def exists(
        cls,
        data_format_name: str
    ) -> bool:
        """
        Check if a data format with the given name exists.

        Examples:
            >>> DataFormat.exists("CSV")
            True
            >>> DataFormat.exists("Parquet")
            False

        Args:
            data_format_name (str): The name of the data format.

        Returns:
            bool: True if the data format exists, False otherwise.
        """
        try:
            exists = DataFormatModel.exists(data_format_name=data_format_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of data format: {e}")
            return False

    @classmethod
    def create(
        cls,
        data_format_name: str,
        data_format_mime_type: str = None,
        data_format_info: dict = None,
    ) -> Optional["DataFormat"]:
        """
        Create a new data format. If a data format with the same name already exists, it will return that instance.

        Examples:
            >>> new_format = DataFormat.create(
            ...     data_format_name="GeoJSON",
            ...     data_format_mime_type="application/geo+json",
            ...     data_format_info={"version": "1.0"}
            ... )
            >>> print(new_format)
            DataFormat(data_format_name=GeoJSON, data_format_mime_type=application/geo+json, id=...)

        Args:
            data_format_name (str): The name of the data format.
            data_format_mime_type (str, optional): The MIME type of the data format. Defaults to None.
            data_format_info (dict, optional): Additional information about the data format. Defaults to {}.

        Returns:
            Optional["DataFormat"]: The created data format, or None if an error occurred.
        """
        try:
            db_instance = DataFormatModel.get_or_create(
                data_format_name=data_format_name,
                data_format_mime_type=data_format_mime_type,
                data_format_info=data_format_info,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating data format: {e}")
            return None

    @classmethod
    def get(cls, data_format_name: str) -> Optional["DataFormat"]:
        """
        Get a data format by its name.

        Examples:
            >>> csv_format = DataFormat.get("CSV")
            >>> print(csv_format)
            DataFormat(data_format_name=CSV, data_format_mime_type=text/csv, id=...)

        Args:
            data_format_name (str): The name of the data format.

        Returns:
            Optional["DataFormat"]: The data format, or None if not found.
        """
        try:
            db_instance = DataFormatModel.get_by_parameters(data_format_name=data_format_name)
            if not db_instance:
                logger.debug(f"Data format with name {data_format_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting data format: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["DataFormat"]:
        """
        Get a data format by its ID.

        Examples:
            >>> data_format = DataFormat.get_by_id(...)
            >>> print(data_format)
            DataFormat(data_format_name=JSON, data_format_mime_type=application/json, id=...)

        Args:
            id (UUID | int | str): The ID of the data format.

        Returns:
            Optional["DataFormat"]: The data format, or None if not found.
        """
        try:
            db_instance = DataFormatModel.get(id)
            if not db_instance:
                logger.warning(f"Data format with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting data format by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["DataFormat"]]:
        """
        Get all data formats.

        Examples:
            >>> all_formats = DataFormat.get_all()
            >>> for fmt in all_formats:
            ...     print(fmt)
            DataFormat(data_format_name=CSV, data_format_mime_type=text/csv, id=...)
            DataFormat(data_format_name=JSON, data_format_mime_type=application/json, id=...)

        Returns:
            Optional[List["DataFormat"]]: A list of all data formats, or None if an error occurred.
        """
        try:
            instances = DataFormatModel.all(limit=limit, offset=offset)
            if not instances or len(instances) == 0:
                logger.info("No data formats found.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error getting all data formats: {e}")
            return None

    @classmethod
    def search(
        cls,
        data_format_name: str = None,
        data_format_mime_type: str = None,
        data_format_info: dict = None
    ) -> Optional[List["DataFormat"]]:
        """
        Search for data formats based on various criteria.

        Examples:
            >>> formats = DataFormat.search(data_format_name="CSV")
            >>> for fmt in formats:
            ...     print(fmt)
            DataFormat(data_format_name=CSV, data_format_mime_type=text/csv, id=...)
            

        Args:
            data_format_name (str, optional): The name of the data format. Defaults to None.
            data_format_mime_type (str, optional): The MIME type of the data format. Defaults to None.
            data_format_info (dict, optional): Additional information about the data format. Defaults to None.

        Returns:
            Optional[List["DataFormat"]]: A list of matching data formats, or None if an error occurred.
        """
        try:
            if not any([data_format_name, data_format_mime_type, data_format_info]):
                logger.warning("At least one search parameter must be provided.")
                return None

            data_formats = DataFormatModel.search(
                data_format_name=data_format_name,
                data_format_mime_type=data_format_mime_type,
                data_format_info=data_format_info,
            )
            if not data_formats or len(data_formats) == 0:
                logger.info("No data formats found with the provided search parameters.")
                return None
            data_formats = [cls.model_validate(data_format) for data_format in data_formats]
            return data_formats
        except Exception as e:
            logger.error(f"Error searching data formats: {e}")
            return None

    def update(
        self,
        data_format_name: str = None,
        data_format_mime_type: str = None,
        data_format_info: dict = None,
    ) -> Optional["DataFormat"]:
        """
        Update the details of the data format.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> updated_format = data_format.update(
            ...     data_format_name="Updated CSV",
            ...     data_format_mime_type="text/csv",
            ...     data_format_info={"version": "2.0"}
            ... )
            >>> print(updated_format)
            DataFormat(data_format_name=Updated CSV, data_format_mime_type=text/csv, id=...)


        Args:
            data_format_name (str, optional): The new name of the data format. Defaults to None.
            data_format_mime_type (str, optional): The new MIME type. Defaults to None.
            data_format_info (dict, optional): The new information. Defaults to None.

        Returns:
            Optional["DataFormat"]: The updated data format, or None if an error occurred.
        """
        try:
            if not any([data_format_name, data_format_mime_type, data_format_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            data_format = DataFormatModel.get(current_id)
            if not data_format:
                logger.warning(f"Data format with ID {current_id} does not exist.")
                return None

            data_format = DataFormatModel.update(
                data_format,
                data_format_name=data_format_name,
                data_format_mime_type=data_format_mime_type,
                data_format_info=data_format_info,
            )
            instance = self.model_validate(data_format)
            self.refresh() # Refresh self with updated data
            return instance # Return the validated instance
        except Exception as e:
            logger.error(f"Error updating data format: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the data format.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> success = data_format.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the data format was deleted successfully, False otherwise.
        """
        try:
            current_id = self.id
            data_format = DataFormatModel.get(current_id)
            if not data_format:
                logger.warning(f"Data format with ID {current_id} does not exist.")
                return False
            DataFormatModel.delete(data_format)
            return True
        except Exception as e:
            logger.error(f"Error deleting data format: {e}")
            return False

    def refresh(self) -> Optional["DataFormat"]:
        """
        Refresh the data format's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> refreshed_format = data_format.refresh()
            >>> print(refreshed_format)
            DataFormat(data_format_name=CSV, data_format_mime_type=text/csv, id=...)


        Returns:
            Optional["DataFormat"]: The refreshed data format, or None if an error occurred.
        """
        try:
            db_instance = DataFormatModel.get(self.id)
            if not db_instance:
                logger.warning(f"Data format with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            # Update self attributes
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing data format: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the data format.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> info = data_format.get_info()
            >>> print(info)
            {'version': '1.0', 'description': 'Comma-separated values format'}

        Returns:
            Optional[dict]: The data format's information, or None if not found.
        """
        try:
            current_id = self.id
            data_format = DataFormatModel.get(current_id)
            if not data_format:
                logger.warning(f"Data format with ID {current_id} does not exist.")
                return None
            data_format_info = data_format.data_format_info
            if not data_format_info:
                logger.info("DataFormat info is empty.")
                return None # Return None if info is empty/None
            return data_format_info
        except Exception as e:
            logger.error(f"Error getting data format info: {e}")
            return None

    def set_info(self, data_format_info: dict) -> Optional["DataFormat"]:
        """
        Set the additional information of the data format.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> updated_format = data_format.set_info({"version": "2.0", "description": "Updated CSV format"})
            >>> print(updated_format.get_info())
            {'version': '2.0', 'description': 'Updated CSV format'}

        Args:
            data_format_info (dict): The new information to set.

        Returns:
            Optional["DataFormat"]: The updated data format, or None if an error occurred.
        """
        try:
            current_id = self.id
            data_format = DataFormatModel.get(current_id)
            if not data_format:
                logger.warning(f"Data format with ID {current_id} does not exist.")
                return None
            data_format = DataFormatModel.update(
                data_format,
                data_format_info=data_format_info,
            )
            instance = self.model_validate(data_format)
            self.refresh() # Refresh self
            return instance # Return validated instance
        except Exception as e:
            logger.error(f"Error setting data format info: {e}")
            return None

    def get_associated_data_types(self) -> Optional[List["DataType"]]:
        """
        Get all data types associated with the data format.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> associated_data_types = data_format.get_associated_data_types()
            >>> for dt in associated_data_types:
            ...     print(dt)
            DataType(data_type_name=Text, id=...)
            DataType(data_type_name=Numeric, id=...)

        Returns:
            A list of associated data types, or None if an error occurred.
        """
        try:
            from gemini.api.data_type import DataType
            current_id = self.id
            data_type_formats = DataTypeFormatsViewModel.search(
                data_format_id=current_id
            )
            if not data_type_formats or len(data_type_formats) == 0:
                logger.info(f"No associated data types found for data format ID {current_id}.")
                return None
            data_types = [DataType.model_validate(data_type_format) for data_type_format in data_type_formats]
            return data_types
        except Exception as e:
            logger.error(f"Error getting associated data types: {e}")
            return None

    def associate_data_type(self, data_type_name: str) -> Optional["DataType"]:
        """
        Associate the data format with a data type.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> associated_data_type = data_format.associate_data_type("Text")
            >>> print(associated_data_type)
            DataType(data_type_name=Text, id=...)

        Args:
            data_type_name (str): The name of the data type to associate with.

        Returns:
            The associated data type, or None if an error occurred.
        """
        try:
            from gemini.api.data_type import DataType
            data_type = DataType.get(data_type_name=data_type_name)
            if not data_type:
                logger.warning(f"Data type with name {data_type_name} does not exist.")
                return None
            existing_association = DataTypeFormatModel.get_or_create(
                data_type_id=data_type.id,
                data_format_id=self.id
            )
            if existing_association:
                logger.info(f"Data type {data_type_name} is already associated with data format ID {self.id}.")
                return data_type
            new_association = DataTypeFormatModel.create(
                data_type_id=data_type.id,
                data_format_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to create association for data type {data_type_name} with data format ID {self.id}.")
                return None
            self.refresh()  # Refresh self with updated data
            return data_type
        except Exception as e:
            logger.error(f"Error associating data type {data_type_name} with data format: {e}")
            return None


    def unassociate_data_type(self, data_type_name: str) -> Optional["DataType"]:
        """
        Unassociate the data format from a data type.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> unassociated_data_type = data_format.unassociate_data_type("Text")
            >>> print(unassociated_data_type)
            DataType(data_type_name=Text, id=...)

        Args:
            data_type_name (str): The name of the data type to unassociate from.

        Returns:
            The unassociated data type, or None if an error occurred.
        """
        try:
            from gemini.api.data_type import DataType
            data_type = DataType.get(data_type_name=data_type_name)
            if not data_type:
                logger.warning(f"Data type with name {data_type_name} does not exist.")
                return None
            existing_association = DataTypeFormatModel.get_by_parameters(
                data_type_id=data_type.id,
                data_format_id=self.id
            )
            if not existing_association:
                logger.info(f"Data type {data_type_name} is not associated with data format ID {self.id}.")
                return None
            is_deleted = DataTypeFormatModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate data type {data_type_name} from data format ID {self.id}.")
                return None
            self.refresh()  # Refresh self with updated data
            return data_type
        except Exception as e:
            logger.error(f"Error unassociating data type {data_type_name} from data format: {e}")
            return None

    def belongs_to_data_type(self, data_type_name: str) -> bool:
        """
        Check if the data format is associated with a specific data type.

        Examples:
            >>> data_format = DataFormat.get("CSV")
            >>> is_associated = data_format.belongs_to_data_type("Text")
            >>> print(is_associated)
            True

        Args:
            data_type_name (str): The name of the data type.

        Returns:
            bool: True if the data format is associated with the data type, False otherwise.
        """
        try:
            from gemini.api.data_type import DataType
            data_type = DataType.get(data_type_name=data_type_name)
            if not data_type:
                logger.warning(f"Data type with name {data_type_name} does not exist.")
                return False
            association_exists = DataTypeFormatModel.exists(
                data_type_id=data_type.id,
                data_format_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if data format belongs to data type {data_type_name}: {e}")
            return False
