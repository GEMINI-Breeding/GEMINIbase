"""
This module defines the ModelRun class, which represents a run of a model, including metadata, associations to models, and run information.

It includes methods for creating, retrieving, updating, and deleting model runs, as well as methods for checking existence, searching, and managing associations with models.

This module includes the following methods:

- `exists`: Check if a model run with the given parameters exists.
- `create`: Create a new model run.
- `get`: Retrieve a model run by its info and name.
- `get_by_id`: Retrieve a model run by its ID.
- `get_all`: Retrieve all model runs.
- `search`: Search for model runs based on various criteria.
- `update`: Update the details of a model run.
- `delete`: Delete a model run.
- `refresh`: Refresh the model run's data from the database.
- `get_info`: Get the additional information of the model run.
- `set_info`: Set the additional information of the model run.
- Association methods for models.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.model_runs import ModelRunModel
from gemini.db.models.views.run_views import ModelRunsViewModel


if TYPE_CHECKING:
    from gemini.api.model import Model

logger = logging.getLogger(__name__)

class ModelRun(APIBase):
    """
    Represents a run of a model, including metadata, associations to models, and run information.

    Attributes:
        id (Optional[ID]): The unique identifier of the model run.
        model_id (Optional[ID]): The ID of the associated model.
        model_run_info (Optional[dict]): Additional information about the model run.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "model_run_id"))

    model_id : Optional[ID] = None
    model_run_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the ModelRun object."""
        return f"ModelRun(id={self.id}, model_id={self.model_id}, model_run_info={self.model_run_info})"
    
    def __repr__(self):
        """Return a detailed string representation of the ModelRun object."""
        return f"ModelRun(id={self.id}, model_id={self.model_id}, model_run_info={self.model_run_info})"

    @classmethod
    def exists(
        cls,
        model_run_info: dict,
        model_name: str = None
    ) -> bool:
        """
        Check if a model run with the given parameters exists.

        Examples:
            >>> ModelRun.exists(model_run_info={"run_id": "12345"}, model_name="example_model")
            True
            >>> ModelRun.exists(model_run_info={"run_id": "67890"}, model_name="non_existent_model")
            False

        Args:
            model_run_info (dict): The run information to check.
            model_name (str, optional): The name of the model. Defaults to None.
        Returns:
            bool: True if the model run exists, False otherwise.
        """
        try:
            exists = ModelRunsViewModel.exists(
                model_name=model_name,
                model_run_info=model_run_info
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of model run: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        model_run_info: dict = None,
        model_name: str = None
    ) -> Optional["ModelRun"]:
        """
        Create a new model run.

        Examples:
            >>> model_run = ModelRun.create(model_run_info={"run_id": "12345"}, model_name="example_model")
            >>> print(model_run)
            ModelRun(id=UUID('...'), model_id=None, model_run_info={'run_id': '12345'})

        Args:
            model_run_info (dict): The run information for the new model run.
            model_name (str, optional): The name of the model. Defaults to None.
        Returns:
            Optional["ModelRun"]: The created model run, or None if an error occurred.
        """
        try:
            db_instance = ModelRunModel.get_or_create(
                model_run_info=model_run_info
            )
            model_run = cls.model_validate(db_instance)
            if model_name:
                model_run.associate_model(model_name=model_name)
            return model_run
        except Exception as e:
            logger.error(f"Error creating model run: {e}")
            return None
        
    @classmethod
    def get(cls, model_run_info: dict, model_name: str = None) -> Optional["ModelRun"]:
        """
        Retrieve a model run by its info and name.

        Examples:
            >>> model_run = ModelRun.get(model_run_info={"run_id": "12345"}, model_name="example_model")
            >>> print(model_run)
            ModelRun(id=UUID('...'), model_id=None, model_run_info={'run_id': '12345'})

        Args:
            model_run_info (dict): The run information to search for.
            model_name (str, optional): The name of the model. Defaults to None.
        Returns:
            Optional["ModelRun"]: The model run, or None if not found.
        """
        try:
            db_instance = ModelRunsViewModel.get_by_parameters(
                model_run_info=model_run_info,
                model_name=model_name
            )
            if not db_instance:
                logger.debug(f"Model run with info {model_run_info} and model name {model_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting model run: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ModelRun"]:
        """
        Retrieve a model run by its ID.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> print(model_run)
            ModelRun(id=UUID('12345678-1234-1234-1234-123456789012'), model_id=None, model_run_info={})

        Args:
            id (UUID | int | str): The ID of the model run.
        Returns:
            Optional["ModelRun"]: The model run, or None if not found.
        """
        try:
            db_instance = ModelRunModel.get(id)
            if not db_instance:
                logger.debug(f"Model run with id {id} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting model run by id: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["ModelRun"]]:
        """
        Retrieve all model runs.

        Examples:
            >>> model_runs = ModelRun.get_all()
            >>> print(model_runs)
            [ModelRun(id=UUID('...'), model_id=None, model_run_info={}), ModelRun(id=UUID('...'), model_id=None, model_run_info={})]

        Returns:
            Optional[List["ModelRun"]]: List of all model runs, or None if not found.
        """
        try:
            model_runs = ModelRunModel.all(limit=limit, offset=offset)
            if not model_runs or len(model_runs) == 0:
                logger.info("No model runs found.")
                return None
            model_runs = [cls.model_validate(model_run) for model_run in model_runs]
            return model_runs
        except Exception as e:
            logger.error(f"Error getting all model runs: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        model_run_info: dict = None,
        model_name: str = None
    ) -> Optional[List["ModelRun"]]:
        """
        Search for model runs based on various criteria.

        Examples:
            >>> model_runs = ModelRun.search(model_run_info={"run_id": "12345"}, model_name="example_model")
            >>> print(model_runs)
            [ModelRun(id=UUID('...'), model_id=None, model_run_info={'run_id': '12345'})]

        Args:
            model_run_info (dict, optional): The run information to search for. Defaults to None.
            model_name (str, optional): The name of the model. Defaults to None.
        Returns:
            Optional[List["ModelRun"]]: List of matching model runs, or None if not found.
        """
        try:
            if not any([model_name, model_run_info]):
                logger.warning("At least one of model_name or model_run_info must be provided.")
                return None
            model_runs = ModelRunsViewModel.search(
                model_run_info=model_run_info,
                model_name=model_name
            )
            if not model_runs or len(model_runs) == 0:
                logger.info("No model runs found for the given search criteria.")
                return None
            model_runs = [cls.model_validate(model_run) for model_run in model_runs]
            return model_runs
        except Exception as e:
            logger.error(f"Error searching model runs: {e}")
            return None
        
    def update(self, model_run_info: dict = None) -> Optional["ModelRun"]:
        """
        Update the details of the model run.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> updated_run = model_run.update(model_run_info={"run_id": "67890"})
            >>> print(updated_run)
            ModelRun(id=UUID('12345678-1234-1234-1234-123456789012'), model_id=None, model_run_info={'run_id': '67890'})

        Args:
            model_run_info (dict, optional): The new run information. Defaults to None.
        Returns:
            Optional["ModelRun"]: The updated model run, or None if an error occurred.
        """
        try:
            if not model_run_info:
                logger.info("Model run info cannot be empty.")
                return None
            current_id = self.id
            model_run = ModelRunModel.get(current_id)
            if not model_run:
                logger.warning(f"Model run with id {current_id} does not exist.")
                return None
            model_run = ModelRunModel.update(
                model_run,
                model_run_info=model_run_info   
            )
            instance = self.model_validate(model_run)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating model run: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the model run.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> success = model_run.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the model run was deleted, False otherwise.
        """
        try:
            current_id = self.id
            model_run = ModelRunModel.get(current_id)
            if not model_run:
                logger.warning(f"Model run with id {current_id} does not exist.")
                return False
            ModelRunModel.delete(model_run)
            return True
        except Exception as e:
            logger.error(f"Error deleting model run: {e}")
            return False
        
    def refresh(self) -> Optional["ModelRun"]:
        """
        Refresh the model run's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> refreshed_run = model_run.refresh()
            >>> print(refreshed_run)
            ModelRun(id=UUID('12345678-1234-1234-1234-123456789012'), model_id=None, model_run_info={})

        Returns:
            Optional["ModelRun"]: The refreshed model run, or None if an error occurred.
        """
        try:
            db_instance = ModelRunModel.get(self.id)
            if not db_instance:
                logger.debug(f"Model run with id {self.id} not found.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing model run: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the model run.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> info = model_run.get_info()
            >>> print(info)
            {'run_id': '12345', 'start_time': '2023-10-01T12:00:00Z'}

        Returns:
            Optional[dict]: The model run's info, or None if not found.
        """
        try:
            current_id = self.id
            model_run = ModelRunModel.get(current_id)
            if not model_run:
                logger.warning(f"Model run with id {current_id} does not exist.")
                return None
            model_run_info = model_run.model_run_info
            if not model_run_info:
                logger.info("ModelRun info is empty.")
                return None
            return model_run_info
        except Exception as e:
            logger.error(f"Error getting model run info: {e}")
            return None

    def set_info(self, model_run_info: dict) -> Optional["ModelRun"]:
        """
        Set the additional information of the model run.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> updated_run = model_run.set_info(model_run_info={"run_id": "67890", "start_time": "2023-10-01T12:00:00Z"})
            >>> print(updated_run)
            ModelRun(id=UUID('12345678-1234-1234-1234-123456789012'), model_id=None, model_run_info={'run_id': '67890', 'start_time': '2023-10-01T12:00:00Z'})

        Args:
            model_run_info (dict): The new run information to set.
        Returns:
            Optional["ModelRun"]: The updated model run, or None if an error occurred.
        """
        try:
            current_id = self.id
            model_run = ModelRunModel.get(current_id)
            if not model_run:
                logger.warning(f"Model run with id {current_id} does not exist.")
                return None
            model_run = ModelRunModel.update(
                model_run,
                model_run_info=model_run_info,
            )
            instance = self.model_validate(model_run)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting model run info: {e}")
            return None

    def get_associated_model(self) -> Optional["Model"]:
        """
        Get the model associated with this model run.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> model = model_run.get_associated_model()
            >>> print(model)
            Model(id=UUID('...'), model_name='example_model', ...)

        Returns:
            Optional["Model"]: The associated model, or None if not found.
        """
        try:
            from gemini.api.model import Model
            if self.model_id is None:
                logger.info("Model run does not have an associated model.")
                return None
            model = Model.get_by_id(self.model_id)
            if not model:
                logger.warning(f"Model with id {self.model_id} does not exist.")
                return None
            return model
        except Exception as e:
            logger.error(f"Error getting model for model run: {e}")
            return None

    def associate_model(self, model_name: str) -> Optional["Model"]:
        """
        Associate this model run with a model.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> model = model_run.associate_model(model_name="example_model")
            >>> print(model)
            Model(id=UUID('...'), model_name='example_model', ...)

        Args:
            model_name (str): The name of the model to associate.
        Returns:
            Optional["Model"]: The associated model, or None if an error occurred.
        """
        try:
            from gemini.api.model import Model
            model = Model.get(model_name=model_name)
            if not model:
                logger.warning(f"Model with name {model_name} does not exist.")
                return None
            existing_association = ModelRunModel.get_by_parameters(
                model_id=model.id,
                id=self.id
            )
            if existing_association:
                logger.info(f"Model run with id {self.id} is already associated with model {model_name}.")
                return None
            # Assign the model to the model run
            db_model_run = ModelRunModel.get(self.id)
            if not db_model_run:
                logger.warning(f"Model run with id {self.id} does not exist.")
                return None
            db_model_run = ModelRunModel.update_parameter(
                db_model_run,
                "model_id",
                model.id
            )
            self.refresh()
            return model
        except Exception as e:
            logger.error(f"Error assigning model to model run: {e}")
            return None

    def belongs_to_model(self, model_name: str) -> bool:
        """
        Check if this model run is associated with a specific model.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> is_associated = model_run.belongs_to_model(model_name="example_model")
            >>> print(is_associated)
            True        

        Args:
            model_name (str): The name of the model to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.model import Model
            model = Model.get(model_name=model_name)
            if not model:
                logger.warning(f"Model with name {model_name} does not exist.")
                return False
            association_exists = ModelRunModel.exists(
                id=self.id,
                model_id=model.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if model run belongs to model: {e}")
            return False

    def unassociate_model(self) -> Optional["Model"]:
        """
        Unassociate this model run from its model.

        Examples:
            >>> model_run = ModelRun.get_by_id(UUID('12345678-1234-1234-1234-123456789012'))
            >>> model = model_run.unassociate_model()
            >>> print(model)
            Model(id=UUID('...'), model_name='example_model', ...)

        Returns:
            Optional["Model"]: The unassociated model, or None if an error occurred.
        """
        try:
            from gemini.api.model import Model
            model_run = ModelRunModel.get(self.id)
            if not model_run:
                logger.warning(f"Model run with id {self.id} does not exist.")
                return None
            model = Model.get_by_id(model_run.model_id)
            model_run = ModelRunModel.update_parameter(
                model_run,
                "model_id",
                None
            )
            self.refresh()
            return model
        except Exception as e:
            logger.error(f"Error unassigning model from model run: {e}")
            return None