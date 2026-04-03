"""
This module defines the ProcedureRun class, which represents a run of a procedure, including metadata, associations to procedures, and run information.

It includes methods for creating, retrieving, updating, and deleting procedure runs, as well as methods for checking existence, searching, and managing associations with procedures.

This module includes the following methods:

- `exists`: Check if a procedure run with the given parameters exists.
- `create`: Create a new procedure run.
- `get`: Retrieve a procedure run by its info and name.
- `get_by_id`: Retrieve a procedure run by its ID.
- `get_all`: Retrieve all procedure runs.
- `search`: Search for procedure runs based on various criteria.
- `update`: Update the details of a procedure run.
- `delete`: Delete a procedure run.
- `refresh`: Refresh the procedure run's data from the database.
- `get_info`: Get the additional information of the procedure run.
- `set_info`: Set the additional information of the procedure run.
- Association methods for procedures.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.procedure_runs import ProcedureRunModel
from gemini.db.models.views.run_views import ProcedureRunsViewModel

if TYPE_CHECKING:
    from gemini.api.procedure import Procedure


logger = logging.getLogger(__name__)

class ProcedureRun(APIBase):
    """
    Represents a run of a procedure, including metadata, associations to procedures, and run information.

    Attributes:
        id (Optional[ID]): The unique identifier of the procedure run.
        procedure_id (Optional[ID]): The ID of the associated procedure.
        procedure_run_info (Optional[dict]): Additional information about the procedure run.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "procedure_run_id"))

    procedure_id : Optional[ID]
    procedure_run_info: Optional[dict] = None

    def __str__(self) -> str:
        """Return a string representation of the ProcedureRun object."""
        return f"ProcedureRun(id={self.id}, procedure_id={self.procedure_id}, procedure_run_info={self.procedure_run_info})"
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the ProcedureRun object."""
        return f"ProcedureRun(id={self.id}, procedure_id={self.procedure_id}, procedure_run_info={self.procedure_run_info})"
    
    @classmethod
    def exists(
        cls,
        procedure_run_info: dict,
        procedure_name: str = None
    ) -> bool:
        """
        Check if a procedure run with the given parameters exists.

        Examples:
            >>> ProcedureRun.exists({"status": "completed"}, "DataProcessing")
            True
            >>> ProcedureRun.exists({"status": "failed"})
            False

        Args:
            procedure_run_info (dict): The run information to check.
            procedure_name (str, optional): The name of the procedure. Defaults to None.
        Returns:
            bool: True if the procedure run exists, False otherwise.
        """
        try:
            exists = ProcedureRunsViewModel.exists(
                procedure_run_info=procedure_run_info,
                procedure_name=procedure_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of ProcedureRun: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        procedure_run_info: dict = None,
        procedure_name: str = None,
    ) -> Optional["ProcedureRun"]:
        """
        Create a new procedure run.

        Examples:
            >>> ProcedureRun.create({"status": "in_progress"}, "DataProcessing")
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "in_progress"})


        Args:
            procedure_run_info (dict, optional): The run information for the new procedure run. Defaults to {{}}.
            procedure_name (str, optional): The name of the procedure. Defaults to None.
        Returns:
            Optional[ProcedureRun]: The created procedure run, or None if an error occurred.
        """
        try:
            db_instance = ProcedureRunModel.get_or_create(
                procedure_run_info=procedure_run_info,
            )
            procedure_run = cls.model_validate(db_instance)
            if procedure_name:
                procedure_run.associate_procedure(procedure_name)
            return procedure_run
        except Exception as e:
            logger.error(f"Error creating ProcedureRun: {e}")
            return None
        
    @classmethod
    def get(cls, procedure_run_info: dict, procedure_name: str = None) -> Optional["ProcedureRun"]:
        """
        Retrieve a procedure run by its info and name.

        Examples:
            >>> ProcedureRun.get({"status": "completed"}, "DataProcessing")
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"})

        Args:
            procedure_run_info (dict): The run information to search for.
            procedure_name (str, optional): The name of the procedure. Defaults to None.
        Returns:
            Optional[ProcedureRun]: The procedure run, or None if not found.
        """
        try:
            db_instance = ProcedureRunsViewModel.get_by_parameters(
                procedure_run_info=procedure_run_info,
                procedure_name=procedure_name
            )
            if not db_instance:
                logger.debug(f"ProcedureRun with info {procedure_run_info} and name {procedure_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting ProcedureRun: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ProcedureRun"]:
        """
        Retrieve a procedure run by its ID.

        Examples:
            >>> ProcedureRun.get_by_id(UUID(...))
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"})

        Args:
            id (UUID | int | str): The ID of the procedure run.
        Returns:
            Optional[ProcedureRun]: The procedure run, or None if not found.
        """
        try:
            db_instance = ProcedureRunModel.get(id)
            if not db_instance:
                logger.warning(f"ProcedureRun with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting ProcedureRun by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["ProcedureRun"]]:
        """
        Retrieve all procedure runs.

        Examples:
            >>> ProcedureRun.get_all()
            [ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"}), ...]

        Returns:
            Optional[List[ProcedureRun]]: List of all procedure runs, or None if not found.
        """
        try:
            procedure_runs = ProcedureRunModel.all(limit=limit, offset=offset)
            if not procedure_runs or len(procedure_runs) == 0:
                logger.info("No ProcedureRuns found.")
                return None
            procedure_runs = [cls.model_validate(procedure_run) for procedure_run in procedure_runs]
            return procedure_runs
        except Exception as e:
            logger.error(f"Error getting all ProcedureRuns: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        procedure_run_info: dict = None,
        procedure_name: str = None
    ) -> Optional[List["ProcedureRun"]]:
        """
        Search for procedure runs based on various criteria.

        Examples:
            >>> ProcedureRun.search({"status": "completed"}, "DataProcessing")
            [ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"}), ...]

        Args:
            procedure_run_info (dict, optional): The run information to search for. Defaults to None.
            procedure_name (str, optional): The name of the procedure. Defaults to None.
        Returns:
            Optional[List[ProcedureRun]]: List of matching procedure runs, or None if not found.
        """
        try:
            if not any([procedure_name, procedure_run_info]):
                logger.info("Either procedure_name or procedure_run_info must be provided.")
                return None
            procedure_runs = ProcedureRunsViewModel.search(
                procedure_run_info=procedure_run_info,
                procedure_name=procedure_name
            )
            if not procedure_runs or len(procedure_runs) == 0:
                logger.info("No ProcedureRuns found with the provided search parameters.")
                return None
            procedure_runs = [cls.model_validate(procedure_run) for procedure_run in procedure_runs]
            return procedure_runs
        except Exception as e:
            logger.error(f"Error searching ProcedureRuns: {e}")
            return None
        
    def update(self, procedure_run_info: dict = None) -> Optional["ProcedureRun"]:
        """
        Update the details of the procedure run.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> updated_run = procedure_run.update({"status": "completed"})
            >>> print(updated_run)
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"})

        Args:
            procedure_run_info (dict, optional): The new run information. Defaults to None.
        Returns:
            Optional[ProcedureRun]: The updated procedure run, or None if an error occurred.
        """
        try:
            if not procedure_run_info:
                logger.info("procedure_run_info must be provided.")
                return None
            current_id = self.id
            procedure_run = ProcedureRunModel.get(id=current_id)
            if not procedure_run:
                logger.warning(f"ProcedureRun with ID {current_id} does not exist.")
                return None
            procedure_run = ProcedureRunModel.update(
                procedure_run,
                procedure_run_info=procedure_run_info
            )
            instance = self.model_validate(procedure_run)
            self.refresh()
            return instance 
        except Exception as e:
            logger.error(f"Error updating ProcedureRun: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the procedure run.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> success = procedure_run.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the procedure run was deleted, False otherwise.
        """
        try:
            current_id = self.id
            procedure_run = ProcedureRunModel.get(current_id)
            if not procedure_run:
                logger.warning(f"ProcedureRun with ID {current_id} does not exist.")
                return False
            ProcedureRunModel.delete(procedure_run)
            return True
        except Exception as e:
            logger.error(f"Error deleting ProcedureRun: {e}")
            return False
        
    def refresh(self) -> Optional["ProcedureRun"]:
        """
        Refresh the procedure run's data from the database.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> refreshed_run = procedure_run.refresh()
            >>> print(refreshed_run)
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "in_progress"})

        Returns:
            Optional[ProcedureRun]: The refreshed procedure run, or None if an error occurred.
        """
        try:
            db_instance = ProcedureRunModel.get(self.id)
            if not db_instance:
                logger.warning(f"ProcedureRun with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing ProcedureRun: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the procedure run.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> info = procedure_run.get_info()
            >>> print(info)
            {"status": "in_progress", "start_time": "2023-10-01T12:00:00Z"}

        Returns:
            Optional[dict]: The procedure run's info, or None if not found.
        """
        try:
            current_id = self.id
            procedure_run = ProcedureRunModel.get(current_id)
            if not procedure_run:
                logger.warning(f"ProcedureRun with ID {current_id} does not exist.")
                return None
            procedure_run_info = procedure_run.procedure_run_info
            if not procedure_run_info:
                logger.info("ProcedureRun info is empty.")
                return None  # Return None if info is empty/None
            return procedure_run_info
        except Exception as e:
            logger.error(f"Error getting ProcedureRun info: {e}")
            return None
        
    def set_info(self, procedure_run_info: dict) -> Optional["ProcedureRun"]:
        """
        Set the additional information of the procedure run.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> updated_run = procedure_run.set_info({"status": "completed"})
            >>> print(updated_run)
            ProcedureRun(id=UUID(...), procedure_id=UUID(...), procedure_run_info={"status": "completed"})

        Args:
            procedure_run_info (dict): The new run information to set.
        Returns:
            Optional[ProcedureRun]: The updated procedure run, or None if an error occurred.
        """
        try:
            current_id = self.id
            procedure_run = ProcedureRunModel.get(current_id)
            if not procedure_run:
                logger.warning(f"ProcedureRun with ID {current_id} does not exist.")
                return None
            procedure_run = ProcedureRunModel.update(
                procedure_run,
                procedure_run_info=procedure_run_info,
            )
            instance = self.model_validate(procedure_run)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error setting ProcedureRun info: {e}")
            return None
        
    def get_associated_procedure(self) -> Optional["Procedure"]:
        """
        Get the procedure associated with this procedure run.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> procedure = procedure_run.get_associated_procedure()
            >>> print(procedure)
            Procedure(id=UUID(...), procedure_name="DataProcessing")


        Returns:
            Optional[Procedure]: The associated procedure, or None if not found.
        """
        try:
            from gemini.api.procedure import Procedure
            if not self.procedure_id:
                logger.info("Procedure ID is not set.")
                return None
            procedure = Procedure.get_by_id(self.procedure_id)
            if not procedure:
                logger.warning(f"Procedure with ID {self.procedure_id} does not exist.")
                return None
            return procedure
        except Exception as e:
            logger.error(f"Error getting associated Procedure: {e}")
            return None

    def associate_procedure(self, procedure_name: str) -> Optional["Procedure"]:
        """
        Associate this procedure run with a procedure.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> procedure = procedure_run.associate_procedure("DataProcessing")
            >>> print(procedure)
            Procedure(id=UUID(...), procedure_name="DataProcessing")

        Args:
            procedure_name (str): The name of the procedure to associate.
        Returns:
            Optional[Procedure]: The associated procedure, or None if an error occurred.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure = Procedure.get(procedure_name=procedure_name)
            if not procedure:
                logger.warning(f"Procedure with name {procedure_name} does not exist.")
                return None
            existing_association = ProcedureRunModel.get_by_parameters(
                procedure_id=procedure.id,
                id=self.id
            )
            if existing_association:
                logger.info(f"ProcedureRun with ID {self.id} is already associated with Procedure {procedure_name}.")
                return self
            db_procedure_run = ProcedureRunModel.get(self.id)
            db_procedure_run = ProcedureRunModel.update_parameter(
                db_procedure_run,
                "procedure_id",
                procedure.id
            )
            self.refresh()
            return procedure
        except Exception as e:
            logger.error(f"Error associating Procedure with ProcedureRun: {e}")
            return None
    
    def belongs_to_procedure(self, procedure_name: str) -> bool:
        """
        Check if this procedure run is associated with a specific procedure.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> is_associated = procedure_run.belongs_to_procedure("DataProcessing")
            >>> print(is_associated)
            True

        Args:
            procedure_name (str): The name of the procedure to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure = Procedure.get(procedure_name=procedure_name)
            if not procedure:
                logger.warning(f"Procedure with name {procedure_name} does not exist.")
                return False
            assignment_exists = ProcedureRunModel.exists(
                id=self.id,
                procedure_id=procedure.id
            )
            return assignment_exists
        except Exception as e:
            logger.error(f"Error checking if ProcedureRun belongs to Procedure: {e}")
            return False

    def unassociate_procedure(self) -> Optional["Procedure"]:
        """
        Unassociate this procedure run from its procedure.

        Examples:
            >>> procedure_run = ProcedureRun.get_by_id(UUID(...))
            >>> procedure = procedure_run.unassociate_procedure()
            >>> print(procedure)
            Procedure(id=UUID(...), procedure_name="DataProcessing")

        Returns:
            Optional[Procedure]: The unassociated procedure, or None if an error occurred.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure_run = ProcedureRunModel.get(self.id)
            if not procedure_run:
                logger.warning(f"ProcedureRun with ID {self.id} does not exist.")
                return None
            procedure = Procedure.get_by_id(procedure_run.procedure_id)
            procedure_run = ProcedureRunModel.update_parameter(
                procedure_run,
                "procedure_id",
                None
            )
            self.refresh()
            return procedure
        except Exception as e:
            logger.error(f"Error unassociating Procedure from ProcedureRun: {e}")
            return None
