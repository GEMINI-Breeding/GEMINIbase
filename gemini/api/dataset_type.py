"""
This module defines the DatasetType class, which represents a type or category for datasets.

It includes methods for creating, retrieving, updating, and deleting dataset types, as well as methods for checking existence, searching, and managing additional information.

This module includes the following methods:

- `exists`: Check if a dataset type with the given name exists.
- `create`: Create a new dataset type.
- `get`: Retrieve a dataset type by its name.
- `get_by_id`: Retrieve a dataset type by its ID.
- `get_all`: Retrieve all dataset types.
- `search`: Search for dataset types based on various criteria.
- `update`: Update the details of a dataset type.
- `delete`: Delete a dataset type.
- `refresh`: Refresh the dataset type's data from the database.
- `get_info`: Get the additional information of the dataset type.
- `set_info`: Set the additional information of the dataset type.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.dataset_types import DatasetTypeModel

logger = logging.getLogger(__name__)

class DatasetType(APIBase):
    """
    Represents a type or category for datasets.

    Attributes:
        id (Optional[ID]): The unique identifier of the dataset type.
        dataset_type_name (str): The name of the dataset type.
        dataset_type_info (Optional[dict]): Additional information about the dataset type.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "dataset_type_id"))

    dataset_type_name: str
    dataset_type_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the DatasetType object."""
        return f"DatasetType(dataset_type_name={self.dataset_type_name}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the DatasetType object."""
        return f"DatasetType(dataset_type_name={self.dataset_type_name}, id={self.id})"

    @classmethod
    def exists(
        cls,
        dataset_type_name: str
    ) -> bool:
        """
        Check if a dataset type with the given name exists.

        Examples:
            >>> DatasetType.exists("example_dataset_type")
            True
            >>> DatasetType.exists("non_existent_type")
            False

        Args:
            dataset_type_name (str): The name of the dataset type.
        Returns:
            bool: True if the dataset type exists, False otherwise.
        """
        try:
            exists = DatasetTypeModel.exists(dataset_type_name=dataset_type_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of dataset type: {e}")
            return False

    @classmethod
    def create(
        cls,
        dataset_type_name: str,
        dataset_type_info: dict = None,
    ) -> Optional["DatasetType"]:
        """
        Create a new dataset type. If a dataset type with same name already exists, it will return the existing one.

        Examples:
            >>> DatasetType.create("example_dataset_type", {"description": "An example dataset type"})
            DatasetType(dataset_type_name='example_dataset_type', id=...)

        Args:
            dataset_type_name (str): The name of the dataset type.
            dataset_type_info (dict, optional): Additional information about the dataset type. Defaults to {{}}.
        Returns:
            Optional["DatasetType"]: The created dataset type, or None if an error occurred.
        """
        try:
            db_instance = DatasetTypeModel.get_or_create(
                dataset_type_name=dataset_type_name,
                dataset_type_info=dataset_type_info,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating dataset type: {e}")
            return None

    @classmethod
    def get(cls, dataset_type_name: str) -> Optional["DatasetType"]:
        """
        Retrieve a dataset type by its name.

        Examples:
            >>> DatasetType.get("example_dataset_type")
            DatasetType(dataset_type_name='example_dataset_type', id=...)

        Args:
            dataset_type_name (str): The name of the dataset type.
        Returns:
            Optional["DatasetType"]: The dataset type, or None if not found.
        """
        try:
            db_instance = DatasetTypeModel.get_by_parameters(dataset_type_name=dataset_type_name)
            if not db_instance:
                logger.debug(f"Dataset type with name {dataset_type_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting dataset type: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["DatasetType"]:
        """
        Retrieve a dataset type by its ID.

        Examples:
            >>> DatasetType.get_by_id(...)
            DatasetType(dataset_type_name='example_dataset_type', id=...)

        Args:
            id (UUID | int | str): The ID of the dataset type.
        Returns:
            Optional["DatasetType"]: The dataset type, or None if not found.
        """
        try:
            db_instance = DatasetTypeModel.get(id)
            if not db_instance:
                logger.warning(f"Dataset type with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting dataset type by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["DatasetType"]]:
        """
        Retrieve all dataset types.

        Examples:
            >>> DatasetType.get_all()
            [DatasetType(dataset_type_name='example_dataset_type', id=...), DatasetType(dataset_type_name='another_dataset_type', id=...)]


        Returns:
            Optional[List["DatasetType"]]: A list of all dataset types, or None if an error occurred.
        """
        try:
            instances = DatasetTypeModel.all(limit=limit, offset=offset)
            if not instances or len(instances) == 0:
                logger.info("No dataset types found.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error getting all dataset types: {e}")
            return None

    @classmethod
    def search(
        cls,
        dataset_type_name: str = None,
        dataset_type_info: dict = None
    ) -> Optional[List["DatasetType"]]:
        """
        Search for dataset types based on various criteria.

        Examples:
            >>> DatasetType.search(dataset_type_name="example_dataset_type")
            [DatasetType(dataset_type_name='example_dataset_type', id=...)]


        Args:
            dataset_type_name (str, optional): The name of the dataset type. Defaults to None.
            dataset_type_info (dict, optional): Additional information about the dataset type. Defaults to None.
        Returns:
            Optional[List["DatasetType"]]: A list of matching dataset types, or None if an error occurred.
        """
        try:
            if not any([dataset_type_name, dataset_type_info]):
                logger.warning("At least one search parameter must be provided.")
                return None

            instances = DatasetTypeModel.search(
                dataset_type_name=dataset_type_name,
                dataset_type_info=dataset_type_info
            )
            if not instances or len(instances) == 0:
                logger.info("No dataset types found with the provided search parameters.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error searching dataset types: {e}")
            return None

    def update(
            self,
            dataset_type_name: str = None,
            dataset_type_info: dict = None
        ) -> Optional["DatasetType"]:
        """
        Update the details of the dataset type.

        Examples:
            >>> dataset_type = DatasetType.get("example_dataset_type")
            >>> updated_dataset_type = dataset_type.update(dataset_type_name="new_name", dataset_type_info{"description": "Updated description"})
            >>> print(updated_dataset_type)
            DatasetType(dataset_type_name='new_name', id=...)

        Args:
            dataset_type_name (str, optional): The new name of the dataset type. Defaults to None.
            dataset_type_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional["DatasetType"]: The updated dataset type, or None if an error occurred.
        """
        try:
            if not any([dataset_type_name, dataset_type_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            dataset_type = DatasetTypeModel.get(current_id)
            if not dataset_type:
                 logger.warning(f"Dataset type with ID {current_id} does not exist.")
                 return None

            dataset_type = DatasetTypeModel.update(
                dataset_type,
                dataset_type_name=dataset_type_name,
                dataset_type_info=dataset_type_info,
            )
            instance = self.model_validate(dataset_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating dataset type: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the dataset type.

        Examples:
            >>> dataset_type = DatasetType.get("example_dataset_type")
            >>> success = dataset_type.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the dataset type was deleted, False otherwise.
        """
        try:
            current_id = self.id
            dataset_type = DatasetTypeModel.get(current_id)
            if not dataset_type:
                 logger.warning(f"Dataset type with ID {current_id} does not exist.")
                 return False
            DatasetTypeModel.delete(dataset_type)
            return True
        except Exception as e:
            logger.error(f"Error deleting dataset type: {e}")
            return False

    def refresh(self) -> Optional["DatasetType"]:
        """
        Refresh the dataset type's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> dataset_type = DatasetType.get("example_dataset_type")
            >>> refreshed_dataset_type = dataset_type.refresh()
            >>> print(refreshed_dataset_type)
            DatasetType(dataset_type_name='example_dataset_type', id=...)

        Returns:
            Optional["DatasetType"]: The refreshed dataset type, or None if an error occurred.
        """
        try:
            db_instance = DatasetTypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Dataset type with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing dataset type: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the dataset type.

        Examples:
            >>> dataset_type = DatasetType.get("example_dataset_type")
            >>> info = dataset_type.get_info()
            >>> print(info)
            {'description': 'An example dataset type'}

        Returns:
            Optional[dict]: The dataset type's info, or None if not found.
        """
        try:
            current_id = self.id
            dataset_type = DatasetTypeModel.get(current_id)
            if not dataset_type:
                logger.warning(f"Dataset type with ID {current_id} does not exist.")
                return None
            dataset_type_info = dataset_type.dataset_type_info
            if not dataset_type_info:
                logger.info("DatasetType info is empty.")
                return None
            return dataset_type_info
        except Exception as e:
            logger.error(f"Error getting dataset type info: {e}")
            return None

    def set_info(self, dataset_type_info: dict) -> Optional["DatasetType"]:
        """
        Set the additional information of the dataset type.

        Examples:
            >>> dataset_type = DatasetType.get("example_dataset_type")
            >>> updated_dataset_type = dataset_type.set_info({"description": "Updated description"})
            >>> print(updated_dataset_type.get_info())
            {'description': 'Updated description'}

        Args:
            dataset_type_info (dict): The new information to set.
        Returns:
            Optional["DatasetType"]: The updated dataset type, or None if an error occurred.
        """
        try:
            current_id = self.id
            dataset_type = DatasetTypeModel.get(current_id)
            if not dataset_type:
                logger.warning(f"Dataset type with ID {current_id} does not exist.")
                return None
            dataset_type = DatasetTypeModel.update(
                dataset_type,
                dataset_type_info=dataset_type_info,
            )
            instance = self.model_validate(dataset_type)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting dataset type info: {e}")
            return None