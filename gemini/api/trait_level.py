"""
This module defines the TraitLevel class, which represents a level or category for traits.

It includes methods for creating, retrieving, updating, and deleting trait levels, as well as methods for checking existence, searching, and managing additional information.

This module includes the following methods:

- `exists`: Check if a trait level with the given name exists.
- `create`: Create a new trait level.
- `get`: Retrieve a trait level by its name.
- `get_by_id`: Retrieve a trait level by its ID.
- `get_all`: Retrieve all trait levels.
- `search`: Search for trait levels based on various criteria.
- `update`: Update the details of a trait level.
- `delete`: Delete a trait level.
- `refresh`: Refresh the trait level's data from the database.
- `get_info`: Get the additional information of the trait level.
- `set_info`: Set the additional information of the trait level.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase

from gemini.db.models.trait_levels import TraitLevelModel

logger = logging.getLogger(__name__)

class TraitLevel(APIBase):
    """
    Represents a level or category for traits.

    Attributes:
        id (Optional[ID]): The unique identifier of the trait level.
        trait_level_name (str): The name of the trait level.
        trait_level_info (Optional[dict]): Additional information about the trait level.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "trait_level_id"))

    trait_level_name: str
    trait_level_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the TraitLevel object."""
        return f"TraitLevel(trait_level_name={self.trait_level_name}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the TraitLevel object."""
        return f"TraitLevel(trait_level_name={self.trait_level_name}, id={self.id})"

    @classmethod
    def exists(
        cls,
        trait_level_name: str
    ) -> bool:
        """
        Check if a trait level with the given name exists.

        Examples:
            >>> TraitLevel.exists("example_trait_level")
            True

            >>> TraitLevel.exists("non_existent_trait_level")
            False

        Args:
            trait_level_name (str): The name of the trait level.
        Returns:
            bool: True if the trait level exists, False otherwise.
        """
        try:
            exists = TraitLevelModel.exists(trait_level_name=trait_level_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of trait level: {e}")
            return False

    @classmethod
    def create(
        cls,
        trait_level_name: str,
        trait_level_info: dict = None,
    ) -> Optional["TraitLevel"]:
        """
        Create a new trait level.

        Examples:
            >>> TraitLevel.create("example_trait_level", {"description": "An example trait level"})
            TraitLevel(trait_level_name='example_trait_level', id=UUID('...'))


        Args:
            trait_level_name (str): The name of the trait level.
            trait_level_info (dict, optional): Additional information about the trait level. Defaults to {{}}.
        Returns:
            Optional[TraitLevel]: The created trait level, or None if an error occurred.
        """
        try:
            db_instance = TraitLevelModel.get_or_create(
                trait_level_name=trait_level_name,
                trait_level_info=trait_level_info,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating trait level: {e}")
            return None

    @classmethod
    def get(cls, trait_level_name: str) -> Optional["TraitLevel"]:
        """
        Retrieve a trait level by its name.

        Examples:
            >>> TraitLevel.get("example_trait_level")
            TraitLevel(trait_level_name='example_trait_level', id=UUID('...'))

        Args:
            trait_level_name (str): The name of the trait level.
        Returns:
            Optional[TraitLevel]: The trait level, or None if not found.
        """
        try:
            db_instance = TraitLevelModel.get_by_parameters(trait_level_name=trait_level_name)
            if not db_instance:
                logger.debug(f"Trait level with name {trait_level_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting trait level: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["TraitLevel"]:
        """
        Retrieve a trait level by its ID.

        Examples:
            >>> TraitLevel.get_by_id(UUID('...'))
            TraitLevel(trait_level_name='example_trait_level', id=UUID('...'))

        Args:
            id (UUID | int | str): The ID of the trait level.
        Returns:
            Optional[TraitLevel]: The trait level, or None if not found.
        """
        try:
            db_instance = TraitLevelModel.get(id)
            if not db_instance:
                logger.warning(f"Trait level with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting trait level by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["TraitLevel"]]:
        """
        Retrieve all trait levels.

        Examples:
            >>> TraitLevel.get_all()
            [TraitLevel(trait_level_name='example_trait_level', id=UUID('...')),
             TraitLevel(trait_level_name='another_trait_level', id=UUID('...'))]

        Returns:
            Optional[List[TraitLevel]]: List of all trait levels, or None if not found.
        """
        try:
            instances = TraitLevelModel.all(limit=limit, offset=offset)
            if not instances or len(instances) == 0:
                logger.info("No trait levels found.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error getting all trait levels: {e}")
            return None

    @classmethod
    def search(
        cls,
        trait_level_name: str = None,
        trait_level_info: dict = None
    ) -> Optional[List["TraitLevel"]]:
        """
        Search for trait levels based on various criteria.

        Examples:
            >>> TraitLevel.search(trait_level_name="example_trait_level")
            [TraitLevel(trait_level_name='example_trait_level', id=UUID('...'))]

        Args:
            trait_level_name (str, optional): The name of the trait level. Defaults to None.
            trait_level_info (dict, optional): Additional information. Defaults to None.
        Returns:
            Optional[List[TraitLevel]]: List of matching trait levels, or None if not found.
        """
        try:
            if not any([trait_level_name, trait_level_info]):
                logger.warning("At least one search parameter must be provided.")
                return None

            instances = TraitLevelModel.search(
                trait_level_name=trait_level_name,
                trait_level_info=trait_level_info
            )
            if not instances or len(instances) == 0:
                logger.info("No trait levels found with the provided search parameters.")
                return None
            instances = [cls.model_validate(instance) for instance in instances]
            return instances
        except Exception as e:
            logger.error(f"Error searching trait levels: {e}")
            return None

    def update(
            self,
            trait_level_name: str = None,
            trait_level_info: dict = None
        ) -> Optional["TraitLevel"]:
        """
        Update the details of the trait level.

        Examples:
            >>> trait_level = TraitLevel.get("example_trait_level")
            >>> updated_trait_level = trait_level.update(trait_level_name="new_name", trait_level_info={"description": "Updated description"})
            >>> print(updated_trait_level)
            TraitLevel(trait_level_name='new_name', id=UUID('...'))

        Args:
            trait_level_name (str, optional): The new name. Defaults to None.
            trait_level_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[TraitLevel]: The updated trait level, or None if an error occurred.
        """
        try:
            if not any([trait_level_name, trait_level_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            trait_level = TraitLevelModel.get(current_id)
            if not trait_level:
                 logger.warning(f"Trait level with ID {current_id} does not exist.")
                 return None

            trait_level = TraitLevelModel.update(
                trait_level,
                trait_level_name=trait_level_name,
                trait_level_info=trait_level_info,
            )
            instance = self.model_validate(trait_level)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating trait level: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the trait level.

        Examples:
            >>> trait_level = TraitLevel.get("example_trait_level")
            >>> deleted = trait_level.delete()
            >>> print(deleted)
            True

        Returns:
            bool: True if the trait level was deleted, False otherwise.
        """
        try:
            current_id = self.id
            trait_level = TraitLevelModel.get(current_id)
            if not trait_level:
                 logger.warning(f"Trait level with ID {current_id} does not exist.")
                 return False
            TraitLevelModel.delete(trait_level)
            return True
        except Exception as e:
            logger.error(f"Error deleting trait level: {e}")
            return False

    def refresh(self) -> Optional["TraitLevel"]:
        """
        Refresh the trait level's data from the database.

        Examples:
            >>> trait_level = TraitLevel.get("example_trait_level")
            >>> refreshed_trait_level = trait_level.refresh()
            >>> print(refreshed_trait_level)
            TraitLevel(trait_level_name='example_trait_level', id=UUID('...'))

        Returns:
            Optional[TraitLevel]: The refreshed trait level, or None if an error occurred.
        """
        try:
            db_instance = TraitLevelModel.get(self.id)
            if not db_instance:
                logger.warning(f"Trait level with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing trait level: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the trait level.

        Examples:
            >>> trait_level = TraitLevel.get("example_trait_level")
            >>> info = trait_level.get_info()
            >>> print(info)
            {'description': 'An example trait level'}

        Returns:
            Optional[dict]: The trait level's info, or None if not found.
        """
        try:
            current_id = self.id
            trait_level = TraitLevelModel.get(current_id)
            if not trait_level:
                logger.warning(f"Trait level with ID {current_id} does not exist.")
                return None
            trait_level_info = trait_level.trait_level_info
            if not trait_level_info:
                logger.info("TraitLevel info is empty.")
                return None
            return trait_level_info
        except Exception as e:
            logger.error(f"Error getting trait level info: {e}")
            return None

    def set_info(self, trait_level_info: dict) -> Optional["TraitLevel"]:
        """
        Set the additional information of the trait level.

        Examples:
            >>> trait_level = TraitLevel.get("example_trait_level")
            >>> updated_trait_level = trait_level.set_info({"description": "Updated description"})
            >>> print(updated_trait_level.get_info())
            {'description': 'Updated description'}

        Args:
            trait_level_info (dict): The new information to set.
        Returns:
            Optional[TraitLevel]: The updated trait level, or None if an error occurred.
        """
        try:
            current_id = self.id
            trait_level = TraitLevelModel.get(current_id)
            if not trait_level:
                logger.warning(f"Trait level with ID {current_id} does not exist.")
                return None
            trait_level = TraitLevelModel.update(
                trait_level,
                trait_level_info=trait_level_info,
            )
            instance = self.model_validate(trait_level)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting trait level info: {e}")
            return None
