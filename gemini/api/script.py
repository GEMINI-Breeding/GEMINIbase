"""
This module defines the Script class, which represents a script entity, including its metadata, associations to experiments, datasets, runs, and records, and related operations.

It includes methods for creating, retrieving, updating, and deleting scripts, as well as methods for checking existence, searching, and managing associations with related entities and records.

This module includes the following methods:

- `exists`: Check if a script with the given name exists.
- `create`: Create a new script.
- `get`: Retrieve a script by its name and experiment.
- `get_by_id`: Retrieve a script by its ID.
- `get_all`: Retrieve all scripts.
- `search`: Search for scripts based on various criteria.
- `update`: Update the details of a script.
- `delete`: Delete a script.
- `refresh`: Refresh the script's data from the database.
- `get_info`: Get the additional information of the script.
- `set_info`: Set the additional information of the script.
- Association methods for experiments, datasets, runs, and records.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.script_run import ScriptRun
from gemini.api.script_record import ScriptRecord
from gemini.api.dataset import Dataset, GEMINIDatasetType
from gemini.db.models.scripts import ScriptModel
from gemini.db.models.script_runs import ScriptRunModel
from gemini.db.models.experiments import ExperimentModel
from gemini.db.models.associations import ExperimentScriptModel, ScriptDatasetModel
from gemini.db.models.views.experiment_views import ExperimentScriptsViewModel
from gemini.db.models.views.dataset_views import ScriptDatasetsViewModel
from gemini.db.models.views.run_views import ScriptRunsViewModel
from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.dataset import Dataset
    from gemini.api.script_run import ScriptRun


logger = logging.getLogger(__name__)

class Script(APIBase):
    """
    Represents a script entity, including its metadata, associations to experiments, datasets, runs, and records, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the script.
        script_name (str): The name of the script.
        script_url (Optional[str]): The URL of the script.
        script_extension (Optional[str]): The file extension of the script.
        script_info (Optional[dict]): Additional information about the script.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "script_id"))

    script_name: str
    script_url: Optional[str] = None
    script_extension: Optional[str] = None
    script_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Script object."""
        return f"Script(script_name={self.script_name}, script_url={self.script_url}, script_extension={self.script_extension}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Script object."""
        return f"Script(script_name={self.script_name}, script_url={self.script_url}, script_extension={self.script_extension}, id={self.id})"

    @classmethod
    def exists(
        cls,
        script_name: str
    ) -> bool:
        """
        Check if a script with the given name exists.

        Examples:
            >>> Script.exists(script_name="example_script")
            True
            >>> Script.exists(script_name="non_existent_script")
            False

        Args:
            script_name (str): The name of the script.
        Returns:
            bool: True if the script exists, False otherwise.
        """
        try:
            exists = ScriptModel.exists(script_name=script_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of script: {e}")
            return False

    @classmethod
    def create(
        cls,
        script_name: str,
        script_url: str = None,
        script_extension: str = None,
        script_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Script"]:
        """
        Create a new script.

        Examples:
            >>> script = Script.create(script_name="example_script", script_url="http://example.com/script.py")
            >>> print(script)
            Script(script_name=example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))

        Args:
            script_name (str): The name of the script.
            script_url (str, optional): The URL of the script. Defaults to None.
            script_extension (str, optional): The file extension. Defaults to None.
            script_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[Script]: The created script, or None if an error occurred.
        """
        try:
            db_instance = ScriptModel.get_or_create(
                script_name=script_name,
                script_url=script_url,
                script_extension=script_extension,
                script_info=script_info,
            )
            script = cls.model_validate(db_instance)
            if experiment_name:
                script.associate_experiment(experiment_name=experiment_name)
            return script
        except Exception as e:
            logger.error(f"Error creating script: {e}")
            return None

    @classmethod
    def get(
        cls,
        script_name: str,
        experiment_name: str = None
    ) -> Optional["Script"]:
        """
        Retrieve a script by its name and experiment.

        Examples:
            >>> script = Script.get(script_name="example_script", experiment_name="example_experiment")
            >>> print(script)
            Script(script_name=example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))

        Args:
            script_name (str): The name of the script.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Script]: The script, or None if not found.
        """
        try:
            db_instance = ExperimentScriptsViewModel.get_by_parameters(
                script_name=script_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Script with name {script_name} not found.")
                return None
            script = cls.model_validate(db_instance)
            return script
        except Exception as e:
            logger.error(f"Error getting script: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Script"]:
        """
        Retrieve a script by its ID.

        Examples:
            >>> script = Script.get_by_id(UUID('...'))
            >>> print(script)
            Script(script_name=example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the script.
        Returns:
            Optional[Script]: The script, or None if not found.
        """
        try:
            db_instance = ScriptModel.get(id)
            if not db_instance:
                logger.warning(f"Script with ID {id} does not exist.")
                return None
            script = cls.model_validate(db_instance)
            return script
        except Exception as e:
            logger.error(f"Error getting script by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Script"]]:
        """
        Retrieve all scripts.

        Examples:
            >>> scripts = Script.get_all()
            >>> for script in scripts:
            ...     print(script)
            Script(script_name=example_script1, script_url=http://example.com/script1.py, script_extension=.py, id=UUID(...))
            Script(script_name=example_script2, script_url=http://example.com/script2.py, script_extension=.py, id=UUID(...))

        Returns:
            Optional[List[Script]]: List of all scripts, or None if not found.
        """
        try:
            scripts = ScriptModel.all(limit=limit, offset=offset)
            if not scripts or len(scripts) == 0:
                logger.info("No scripts found.")
                return None
            scripts = [cls.model_validate(script) for script in scripts]
            return scripts
        except Exception as e:
            logger.error(f"Error getting all scripts: {e}")
            return None

    @classmethod
    def search(
        cls,
        script_name: str = None,
        script_url: str = None,
        script_extension: str = None,
        script_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Script"]]:
        """
        Search for scripts based on various criteria.

        Examples:
            >>> scripts = Script.search(script_name="example_script")
            >>> for script in scripts:
            ...     print(script)
            Script(script_name=example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))


        Args:
            script_name (str, optional): The name of the script. Defaults to None.
            script_url (str, optional): The URL of the script. Defaults to None.
            script_extension (str, optional): The file extension. Defaults to None.
            script_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List[Script]]: List of matching scripts, or None if not found.
        """
        try:
            if not any([script_name, script_info, script_url, script_extension, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            scripts = ExperimentScriptsViewModel.search(
                script_name=script_name,
                script_info=script_info,
                script_url=script_url,
                script_extension=script_extension,
                experiment_name=experiment_name
            )
            if not scripts or len(scripts) == 0:
                logger.info("No scripts found with the provided search parameters.")
                return None
            scripts = [cls.model_validate(script) for script in scripts]
            return scripts
        except Exception as e:
            logger.error(f"Error searching scripts: {e}")
            return None

    def update(
        self,
        script_name: str = None,
        script_url: str = None,
        script_extension: str = None,
        script_info: dict = None
    ) -> Optional["Script"]:
        """
        Update the details of the script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> updated_script = script.update(script_name="new_example_script")
            >>> print(updated_script)
            Script(script_name=new_example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))

        Args:
            script_name (str, optional): The new name. Defaults to None.
            script_url (str, optional): The new URL. Defaults to None.
            script_extension (str, optional): The new file extension. Defaults to None.
            script_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[Script]: The updated script, or None if an error occurred.
        """
        try:
            if not any([script_name, script_url, script_extension, script_info]):
                logger.warning("At least one update parameter must be provided.")
                return None
            current_id = self.id
            script = ScriptModel.get(current_id)
            if not script:
                logger.warning(f"Script with ID {current_id} does not exist.")
                return None
            rename = script_name is not None and script_name != script.script_name
            script = ScriptModel.update(
                script,
                script_name=script_name,
                script_url=script_url,
                script_extension=script_extension,
                script_info=script_info
            )
            if rename:
                from gemini.api._rename_cascade import cascade_rename
                cascade_rename(current_id, "script_id", "script_name", script_name)
            script = self.model_validate(script)
            self.refresh()
            return script
        except Exception as e:
            logger.error(f"Error updating script: {e}")
            return None

    def delete(self) -> bool:
        """
        Delete the script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> success = script.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the script was deleted, False otherwise.
        """
        try:
            current_id = self.id
            script = ScriptModel.get(current_id)
            if not script:
                logger.warning(f"Script with ID {current_id} does not exist.")
                return False

            experiments = self.get_associated_experiments() or []
            prefixes = [
                f"script_data/{exp.experiment_name}/{self.script_name}/"
                for exp in experiments
                if getattr(exp, "experiment_name", None)
            ]

            ScriptModel.delete(script)

            from gemini.api.base import sweep_minio_prefixes
            sweep_minio_prefixes(prefixes)
            return True
        except Exception as e:
            logger.error(f"Error deleting script: {e}")
            return False

    def refresh(self) -> Optional["Script"]:
        """
        Refresh the script's data from the database.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> refreshed_script = script.refresh()
            >>> print(refreshed_script)
            Script(script_name=example_script, script_url=http://example.com/script.py, script_extension=.py, id=UUID(...))

        Returns:
            Optional[Script]: The refreshed script, or None if an error occurred.
        """
        try:
            db_instance = ScriptModel.get(self.id)
            if not db_instance:
                logger.warning(f"Script with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing script: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> script_info = script.get_info()
            >>> print(script_info)
            {'key1': 'value1', 'key2': 'value2'}

        Returns:
            Optional[dict]: The script's info, or None if not found.
        """
        try:
            current_id = self.id
            script = ScriptModel.get(current_id)
            if not script:
                logger.warning(f"Script with ID {current_id} does not exist.")
                return None
            script_info = script.script_info
            if not script_info:
                logger.info("Script info is empty.")
                return None
            return script_info
        except Exception as e:
            logger.error(f"Error getting script info: {e}")
            return None

    def set_info(self, script_info: dict) -> Optional["Script"]:
        """
        Set the additional information of the script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> updated_script = script.set_info(script_info={"key1": "new_value1", "key2": "new_value2"})
            >>> print(updated_script.get_info())
            {'key1': 'new_value1', 'key2': 'new_value2'}

        Args:
            script_info (dict): The new information to set.
        Returns:
            Optional[Script]: The updated script, or None if an error occurred.
        """
        try:
            current_id = self.id
            script = ScriptModel.get(current_id)
            if not script:
                logger.warning(f"Script with ID {current_id} does not exist.")
                return None
            script = ScriptModel.update(
                script,
                script_info=script_info
            )
            script = self.model_validate(script)
            self.refresh()
            return script
        except Exception as e:
            logger.error(f"Error setting script info: {e}")
            return None

    def get_associated_runs(self) -> Optional[List["ScriptRun"]]:
        """
        Get all runs associated with this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> runs = script.get_associated_runs()
            >>> for run in runs:
            ...     print(run)
            ScriptRun(id=UUID(...), script_id=UUID(...), script_run_info={'key': 'value'})
            ScriptRun(id=UUID(...), script_id=UUID(...), script_run_info={'key': 'value'})

        Returns:
            Optional[List[ScriptRun]]: A list of associated runs, or None if not found.
        """
        try:
            from gemini.api.script_run import ScriptRun
            current_id = self.id
            script_runs = ScriptRunsViewModel.search(script_id=current_id)
            if not script_runs or len(script_runs) == 0:
                logger.info("No associated runs found.")
                return None
            runs = [ScriptRun.model_validate(script_run) for script_run in script_runs]
            return runs
        except Exception as e:
            logger.error(f"Error getting associated runs: {e}")
            return None

    def create_new_run(self, script_run_info: dict = None) -> Optional["ScriptRun"]:
        """
        Create and associate a new run with this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> new_run = script.create_new_run(script_run_info={"key": "value"})
            >>> print(new_run)
            ScriptRun(id=UUID(...), script_id=UUID(...), script_run_info={'key': 'value'})

        Args:
            script_run_info (dict, optional): The run information for the new run. Defaults to None.
        Returns:
            Optional[ScriptRun]: The created and associated run, or None if an error occurred.
        """
        try:
            from gemini.api.script_run import ScriptRun
            new_script_run = ScriptRun.create(
                script_run_info=script_run_info,
                script_name=self.script_name
            )
            if not new_script_run:
                logger.info("Failed to create new script run.")
                return None
            return new_script_run
        except Exception as e:
            logger.error(f"Error creating script run: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> experiments = script.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(id=UUID(...), experiment_name='example_experiment', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31')

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            current_id = self.id
            experiment_scripts = ExperimentScriptsViewModel.search(script_id=current_id)
            if not experiment_scripts or len(experiment_scripts) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiment_scripts]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this script with an experiment.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> experiment = script.associate_experiment(experiment_name="example_experiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name='example_experiment', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31')

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
            existing_association = ExperimentScriptModel.get_by_parameters(
                experiment_id=experiment.id,
                script_id=self.id
            )
            if existing_association:
                logger.info(f"Script {self.script_name} is already associated with experiment {experiment_name}.")
                return self
            new_association = ExperimentScriptModel.get_or_create(
                experiment_id=experiment.id,
                script_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate script {self.script_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating script with experiment: {e}")
            return None


    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this script from an experiment.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> experiment = script.unassociate_experiment(experiment_name="example_experiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name='example_experiment', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31')

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
            existing_association = ExperimentScriptModel.get_by_parameters(
                experiment_id=experiment.id,
                script_id=self.id
            )
            if not existing_association:
                logger.info(f"Script {self.script_name} is not associated with experiment {experiment_name}.")
                return self
            is_deleted = ExperimentScriptModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate script {self.script_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating script from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this script is associated with a specific experiment.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> is_associated = script.belongs_to_experiment(experiment_name="example_experiment")
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
            association_exists = ExperimentScriptModel.exists(
                experiment_id=experiment.id,
                script_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if script belongs to experiment: {e}")
            return

    def get_associated_datasets(self) -> Optional[List["Dataset"]]:
        """
        Get all datasets associated with this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> datasets = script.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(id=UUID(...), dataset_name='example_dataset', dataset_type='Script', collection_date='2023-01-01')
            Dataset(id=UUID(...), dataset_name='another_dataset', dataset_type='Script', collection_date='2023-01-02')

        Returns:
            Optional[List[Dataset]]: A list of associated datasets, or None if not found.
        """
        try:
            from gemini.api.dataset import Dataset
            current_id = self.id
            script_datasets = ScriptDatasetsViewModel.search(script_id=current_id)
            if not script_datasets or len(script_datasets) == 0:
                logger.info("No associated datasets found.")
                return None
            datasets = [Dataset.model_validate(script_dataset) for script_dataset in script_datasets]
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
        Create and associate a new dataset with this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> dataset = script.create_new_dataset(dataset_name="example_dataset", dataset_info={"key": "value"}, collection_date=date(2023, 1, 1), experiment_name="example_experiment")
            >>> print(dataset)
            Dataset(id=UUID(...), dataset_name='example_dataset', dataset_type='Script', collection_date='2023-01-01')

        Args:
            dataset_name (str): The name of the new dataset.
            dataset_info (dict, optional): Additional information about the dataset. Defaults to {{}}.
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
                dataset_type=GEMINIDatasetType.Script
            )
            if not dataset:
                logger.info("Failed to create new dataset.")
                return None
            dataset = self.associate_dataset(dataset_name=dataset_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating new dataset: {e}")
            return None

    def associate_dataset(self, dataset_name: str) -> Optional["Dataset"]:
        """
        Associate this script with a dataset.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> dataset = script.associate_dataset(dataset_name="example_dataset")
            >>> print(dataset)
            Dataset(id=UUID(...), dataset_name='example_dataset', dataset_type='Script', collection_date='2023-01-01')

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
            existing_association = ScriptDatasetModel.get_by_parameters(
                script_id=self.id,
                dataset_id=dataset.id
            )
            if existing_association:
                logger.info(f"Script {self.script_name} is already associated with dataset {dataset_name}.")
                return self
            new_association = ScriptDatasetModel.get_or_create(
                script_id=self.id,
                dataset_id=dataset.id
            )
            if not new_association:
                logger.info(f"Failed to associate script {self.script_name} with dataset {dataset_name}.")
                return None
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error associating script with dataset: {e}")
            return None

    def insert_record(
        self,
        timestamp: datetime = None,
        collection_date: date = None,
        script_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_file: str = None,
        record_info: dict = None,
    ) -> tuple[bool, List[str]]:
        """
        Insert a single script record for this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> success, record_ids = script.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date(2023, 1, 1),
            ...     script_data={"key": "value"},
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_file="/path/to/record/file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> print(success, record_ids)
            True [UUID(...)]

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            script_data (dict, optional): The script data. Defaults to {{}}.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_file (str, optional): The file path or URI. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("At least one of experiment_name, season_name, or site_name must be provided.")
            
            if not script_data and not record_file:
                raise ValueError("Either script_data or record_file must be provided.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            if not dataset_name:
                dataset_name = f"{self.script_name} Dataset {collection_date}"
            script_name = self.script_name
            script_record = ScriptRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                script_name=script_name,
                script_data=script_data,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_file=record_file,
                record_info=record_info,
                insert_on_create=False
            )
            success, inserted_record_ids = ScriptRecord.insert([script_record])
            if not success:
                raise Exception("Failed to insert script record.")
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting script record: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        script_data: List[dict] = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_files: List[str] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Insert multiple script records for this script.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> success, record_ids = script.insert_records(
            ...     timestamps=[datetime.now(), datetime.now()],
            ...     collection_date=date(2023, 1, 1),
            ...     script_data=[{"key": "value1"}, {"key": "value2"}],
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_files=["/path/to/record1.txt", "/path/to/record2.txt"],
            ...     record_info=[{"info_key": "info_value1"}, {"info_key": "info_value2"}]
            ... )
            >>> print(success, record_ids)
            True [UUID(...), UUID(...)]

        Args:
            timestamps (List[datetime], optional): List of timestamps. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            script_data (List[dict], optional): List of script data. Defaults to [].
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_files (List[str], optional): List of file paths or URIs. Defaults to [].
            record_info (List[dict], optional): List of additional info. Defaults to [].
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("At least one of experiment_name, season_name, or site_name must be provided.")
            
            if len(timestamps) == 0:
                raise ValueError("At least one timestamp must be provided.")
            
            if len(script_data) != len(timestamps):
                raise ValueError("script_data must have the same length as timestamps.")
            
            if record_files and len(record_files) != len(timestamps):
                raise ValueError("record_files must have the same length as timestamps.")
            
            collection_date = collection_date if collection_date else timestamps[0].date()
            
            if not dataset_name:
                dataset_name = f"{self.script_name} Dataset {collection_date}"
            
            script_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Script " + self.script_name):
                script_record = ScriptRecord.create(
                    timestamp = timestamps[i],
                    collection_date = collection_date,
                    script_name= self.script_name,
                    script_data = script_data[i]  if script_data else {},
                    dataset_name = dataset_name,
                    experiment_name = experiment_name,
                    season_name = season_name,
                    site_name = site_name,
                    record_file= record_files[i] if record_files else None,
                    record_info = record_info[i] if record_info else {},
                    insert_on_create=False
                )
                script_records.append(script_record)

            success, inserted_record_ids = ScriptRecord.insert(script_records)
            if not success:
                logger.info("Failed to insert script records.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting script records: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_info: dict = None
    ) -> Optional[List[ScriptRecord]]:
        """
        Search for script records associated with this script based on search parameters.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> records = script.search_records(
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            ScriptRecord(id=UUID(...), script_name='example_script', timestamp='2023-01-01T00:00:00', dataset_name='example_dataset', experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            ScriptRecord(id=UUID(...), script_name='example_script', timestamp='2023-01-02T00:00:00', dataset_name='example_dataset', experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Returns:
            Optional[List[ScriptRecord]]: List of matching script records, or None if not found.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = ScriptRecord.search(
                collection_date=collection_date,
                dataset_name=dataset_name,
                script_name=self.script_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching script records: {e}")
            return []
        
    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> Optional[List[ScriptRecord]]:
        """
        Filter script records associated with this script using a custom filter function.

        Examples:
            >>> script = Script.get(script_name="example_script")
            >>> records = script.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     dataset_names=["example_dataset"],
            ...     experiment_names=["example_experiment"],
            ...     season_names=["example_season"],
            ...     site_names=["example_site"]
            ... )
            >>> for record in records:
            ...     print(record)
            ScriptRecord(id=UUID(...), script_name='example_script', timestamp='2023-01-01T00:00:00', dataset_name='example_dataset', experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            ScriptRecord(id=UUID(...), script_name='example_script', timestamp='2023-01-02T00:00:00', dataset_name='example_dataset', experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            start_timestamp (Optional[datetime], optional): Start of timestamp range. Defaults to None.
            end_timestamp (Optional[datetime], optional): End of timestamp range. Defaults to None.
            dataset_names (Optional[List[str]], optional): List of dataset names. Defaults to None.
            experiment_names (Optional[List[str]], optional): List of experiment names. Defaults to None.
            season_names (Optional[List[str]], optional): List of season names. Defaults to None.
            site_names (Optional[List[str]], optional): List of site names. Defaults to None.
        Returns:
            Optional[List[ScriptRecord]]: List of filtered script records, or None if not found.
        """
        try:
            records = ScriptRecord.filter(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                script_names=[self.script_name],
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering script records: {e}")
            return []


