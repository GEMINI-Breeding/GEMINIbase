"""
This module defines the ScriptRun class, which represents a run of a script, including metadata, associations to scripts, and run information.

It includes methods for creating, retrieving, updating, and deleting script runs, as well as methods for checking existence, searching, and managing associations with scripts.

This module includes the following methods:

- `exists`: Check if a script run with the given parameters exists.
- `create`: Create a new script run.
- `get`: Retrieve a script run by its info and name.
- `get_by_id`: Retrieve a script run by its ID.
- `get_all`: Retrieve all script runs.
- `search`: Search for script runs based on various criteria.
- `update`: Update the details of a script run.
- `delete`: Delete a script run.
- `refresh`: Refresh the script run's data from the database.
- `get_info`: Get the additional information of the script run.
- `set_info`: Set the additional information of the script run.
- Association methods for scripts.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.script_runs import ScriptRunModel
from gemini.db.models.views.run_views import ScriptRunsViewModel

if TYPE_CHECKING:
    from gemini.api.script import Script

logger = logging.getLogger(__name__)

class ScriptRun(APIBase):
    """
    Represents a run of a script, including metadata, associations to scripts, and run information.

    Attributes:
        id (Optional[ID]): The unique identifier of the script run.
        script_id (Optional[ID]): The ID of the associated script.
        script_run_info (Optional[dict]): Additional information about the script run.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "script_run_id"))

    script_id : Optional[ID] 
    script_run_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the ScriptRun object."""
        return f"ScriptRun(id={self.id}, script_id={self.script_id}, script_run_info={self.script_run_info})"

    def __repr__(self):
        """Return a detailed string representation of the ScriptRun object."""
        return f"ScriptRun(id={self.id}, script_id={self.script_id}, script_run_info={self.script_run_info})"

    @classmethod
    def exists(
        cls,
        script_run_info: dict,
        script_name: str = None
    ) -> bool:
        """
        Check if a script run with the given parameters exists.

        Examples:
            >>> ScriptRun.exists(script_run_info={"status": "completed"}, script_name="example_script")
            True
            >>> ScriptRun.exists(script_run_info={"status": "running"})
            False

        Args:
            script_run_info (dict): The run information to check.
            script_name (str, optional): The name of the script. Defaults to None.
        Returns:
            bool: True if the script run exists, False otherwise.
        """
        try:
            exists = ScriptRunsViewModel.exists(
                script_name=script_name,
                script_run_info=script_run_info
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of script run: {e}")
            return False

    @classmethod
    def create(
        cls,
        script_run_info: dict = None,
        script_name: str = None
    ) -> Optional["ScriptRun"]:
        """
        Create a new script run.

        Examples:
            >>> script_run = ScriptRun.create(script_run_info={"status": "running"}, script_name="example_script")
            >>> print(script_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'running'})

        Args:
            script_run_info (dict, optional): The run information for the new script run. Defaults to {{}}.
            script_name (str, optional): The name of the script. Defaults to None.
        Returns:
            Optional[ScriptRun]: The created script run, or None if an error occurred.
        """
        try:
            db_instance = ScriptRunModel.get_or_create(
                script_run_info=script_run_info,
            )
            script_run = cls.model_validate(db_instance)
            if script_name:
                script_run.associate_script(script_name)
            return script_run
        except Exception as e:
            logger.error(f"Error creating script run: {e}")
            return None

    @classmethod
    def get(cls, script_run_info: dict, script_name: str = None) -> Optional["ScriptRun"]:
        """
        Retrieve a script run by its info and name.

        Examples:
            >>> script_run = ScriptRun.get(script_run_info={"status": "completed"}, script_name="example_script")
            >>> print(script_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})

        Args:
            script_run_info (dict): The run information to search for.
            script_name (str, optional): The name of the script. Defaults to None.
        Returns:
            Optional[ScriptRun]: The script run, or None if not found.
        """
        try:
            db_instance = ScriptRunsViewModel.get_by_parameters(
                script_run_info=script_run_info,
                script_name=script_name
            )
            if not db_instance:
                logger.debug(f"Script run with info {script_run_info} and script name {script_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting script run: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ScriptRun"]:
        """
        Retrieve a script run by its ID.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> print(script_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})

        Args:
            id (UUID | int | str): The ID of the script run.
        Returns:
            Optional[ScriptRun]: The script run, or None if not found.
        """
        try:
            db_instance = ScriptRunModel.get(id)
            if not db_instance:
                logger.debug(f"Script run with id {id} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting script run by id: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["ScriptRun"]]:
        """
        Retrieve all script runs.

        Examples:
            >>> script_runs = ScriptRun.get_all()
            >>> for run in script_runs:
            ...     print(run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'running'})

        Returns:
            Optional[List[ScriptRun]]: List of all script runs, or None if not found.
        """
        try:
            script_runs = ScriptRunModel.all(limit=limit, offset=offset)
            if not script_runs or len(script_runs) == 0:
                logger.info("No script runs found.")
                return None
            script_runs = [cls.model_validate(script_run) for script_run in script_runs]
            return script_runs
        except Exception as e:
            logger.error(f"Error getting all script runs: {e}")
            return None

    @classmethod
    def search(
        cls,
        script_run_info: dict = None,
        script_name: str = None
    ) -> Optional[List["ScriptRun"]]:
        """
        Search for script runs based on various criteria.

        Examples:
            >>> script_runs = ScriptRun.search(script_run_info={"status": "completed"}, script_name="example_script")
            >>> for run in script_runs:
            ...     print(run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'running'})

        Args:
            script_run_info (dict, optional): The run information to search for. Defaults to None.
            script_name (str, optional): The name of the script. Defaults to None.
        Returns:
            Optional[List[ScriptRun]]: List of matching script runs, or None if not found.
        """
        try:
            if not any([script_name, script_run_info]):
                logger.warning("At least one of script_name or script_run_info must be provided.")
                return None
            script_runs = ScriptRunsViewModel.search(
                script_run_info=script_run_info,
                script_name=script_name
            )
            if not script_runs or len(script_runs) == 0:
                logger.info("No script runs found for the given search criteria.")
                return None
            script_runs = [cls.model_validate(script_run) for script_run in script_runs]
            return script_runs
        except Exception as e:
            logger.error(f"Error searching script runs: {e}")
            return None

    def update(self, script_run_info: dict = None) -> Optional["ScriptRun"]:
        """
        Update the details of the script run.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> updated_run = script_run.update(script_run_info={"status": "completed"})
            >>> print(updated_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})

        Args:
            script_run_info (dict, optional): The new run information. Defaults to None.
        Returns:
            Optional[ScriptRun]: The updated script run, or None if an error occurred.
        """
        try:
            if not script_run_info:
                logger.info("Model run info cannot be empty.")
                return None
            current_id = self.id
            script_run = ScriptRunModel.get(current_id)
            if not script_run:
                logger.warning(f"Script run with id {current_id} does not exist.")
                return None
            script_run = ScriptRunModel.update(
                script_run,
                script_run_info=script_run_info
            )
            instance = self.model_validate(script_run)
            self.refresh()
            return instance
        except Exception as e:
            logger.error(f"Error updating script run: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the script run.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> success = script_run.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the script run was deleted, False otherwise.
        """
        try:
            current_id = self.id
            script_run = ScriptRunModel.get(current_id)
            if not script_run:
                logger.warning(f"Script run with id {current_id} does not exist.")
                return False
            ScriptRunModel.delete(script_run)
            return True
        except Exception as e:
            logger.error(f"Error deleting script run: {e}")
            return False

    def refresh(self) -> Optional["ScriptRun"]:
        """
        Refresh the script run's data from the database.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> refreshed_run = script_run.refresh()
            >>> print(refreshed_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'running'})

        Returns:
            Optional[ScriptRun]: The refreshed script run, or None if an error occurred.
        """
        try:
            db_instance = ScriptRunModel.get(self.id)
            if not db_instance:
                logger.debug(f"Script run with id {self.id} not found.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and getattr(self, key) != value:
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing script run: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the script run.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> info = script_run.get_info()
            >>> print(info)
            {'status': 'running', 'start_time': '2023-10-01T12:00:00Z'}

        Returns:
            Optional[dict]: The script run's info, or None if not found.
        """
        try:
            current_id = self.id
            script_run = ScriptRunModel.get(current_id)
            if not script_run:
                logger.warning(f"Script run with id {current_id} does not exist.")
                return None
            script_run_info = script_run.script_run_info
            if not script_run_info:
                logger.info("ScriptRun info is empty.")
                return {}
            return script_run_info
        except Exception as e:
            logger.error(f"Error getting script run info: {e}")
            return None

    def set_info(self, script_run_info: dict) -> Optional["ScriptRun"]:
        """
        Set the additional information of the script run.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> updated_run = script_run.set_info(script_run_info={"status": "completed"})
            >>> print(updated_run)
            ScriptRun(id=UUID('...'), script_id=UUID('...') script_run_info={'status': 'completed'})

        Args:
            script_run_info (dict): The new run information to set.
        Returns:
            Optional[ScriptRun]: The updated script run, or None if an error occurred.
        """
        try:
            current_id = self.id
            script_run = ScriptRunModel.get(current_id)
            if not script_run:
                logger.warning(f"Script run with id {current_id} does not exist.")
                return None
            script_run = ScriptRunModel.update(
                script_run,
                script_run_info=script_run_info,
            )
            self.script_run_info = script_run.script_run_info
            return self
        except Exception as e:
            logger.error(f"Error setting script run info: {e}")
            return None
        
    def get_associated_script(self) -> Optional["Script"]:
        """
        Get the script associated with this script run.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> script = script_run.get_associated_script()
            >>> print(script)
            Script(script_name='example_script', script_url='https://example.com/script.py', script_extension='py', id=UUID('...'))
            Script(script_name='example_script', script_url='https://example.com/script.py', script_extension='py', id=UUID('...'))

        Returns:
            Optional[Script]: The associated script, or None if not found.
        """
        try:
            from gemini.api.script import Script
            current_id = self.script_id
            script_run_model = ScriptRunsViewModel.get_by_parameters(
                script_id=current_id
            )
            script_id = script_run_model.script_id
            if not script_id:
                logger.info(f"No script found for script run with id {self.id}.")
                return None
            script = Script.get_by_id(script_id)
            if not script:
                logger.warning(f"Script with id {script_id} does not exist.")
                return None
            return script
        except Exception as e:
            logger.error(f"Error getting script for script run: {e}")
            return None

    def associate_script(self, script_name: str) -> Optional["Script"]:
        """
        Associate this script run with a script.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> script = script_run.associate_script(script_name="example_script")
            >>> print(script)
            Script(script_name='example_script', script_url='https://example.com/script.py', script_extension='py', id=UUID('...'))

        Args:
            script_name (str): The name of the script to associate.
        Returns:
            Optional[Script]: The associated script, or None if an error occurred.
        """
        try:
            from gemini.api.script import Script
            script = Script.get(script_name=script_name)
            if not script:
                logger.warning(f"Script with name {script_name} does not exist.")
                return None
            existing_association = ScriptRunModel.get_by_parameters(
                id=script.id,
                script_run_id=self.id
            )
            if existing_association:
                logger.info(f"Script run with id {self.id} is already associated with script {script_name}.")
                return self
            db_script_run = ScriptRunModel.get(self.id)
            db_script_run = ScriptRunModel.update_parameter(
                db_script_run,
                "script_id",
                script.id
            )
            self.refresh()
            return script
        except Exception as e:
            logger.error(f"Error assigning script to script run: {e}")
            return None

    def unassociate_script(self) -> Optional["Script"]:
        """
        Unassociate this script run from its script.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> script = script_run.unassociate_script()
            >>> print(script)
            Script(script_name='example_script', script_url='https://example.com/script.py', script_extension='py', id=UUID('...'))

        Returns:
            Optional[Script]: The unassociated script, or None if an error occurred.
        """
        try:
            from gemini.api.script import Script
            script_run = ScriptRunModel.get(self.id)
            if not script_run:
                logger.warning(f"Script run with id {self.id} does not exist.")
                return None
            script = Script.get_by_id(script_run.script_id)
            script_run = ScriptRunModel.update_parameter(
                script_run,
                "script_id",
                None
            )
            self.refresh()
            return script
        except Exception as e:
            logger.error(f"Error unassigning script from script run: {e}")
            return None

    def belongs_to_script(self, script_name: str) -> bool:
        """
        Check if this script run is associated with a specific script.

        Examples:
            >>> script_run = ScriptRun.get_by_id(UUID('...'))
            >>> is_associated = script_run.belongs_to_script("example_script")
            >>> print(is_associated)
            True

        Args:
            script_name (str): The name of the script to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.script import Script
            script = Script.get(script_name=script_name)
            if not script:
                logger.warning(f"Script with name {script_name} does not exist.")
                return False
            assignment_exists = ScriptRunModel.exists(
                script_run_id=self.id,
                script_id=script.id
            )
            return assignment_exists
        except Exception as e:
            logger.error(f"Error checking if script run belongs to script: {e}")
            return False

