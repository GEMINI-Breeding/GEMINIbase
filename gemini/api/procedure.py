"""
This module defines the Procedure class, which represents a procedure entity, including its metadata, associations to experiments, datasets, runs, and records, and related operations.

It includes methods for creating, retrieving, updating, and deleting procedures, as well as methods for checking existence, searching, and managing associations with experiments, datasets, runs, and records.

This module includes the following methods:

- `exists`: Check if a procedure with the given name exists.
- `create`: Create a new procedure.
- `get`: Retrieve a procedure by its name and experiment.
- `get_by_id`: Retrieve a procedure by its ID.
- `get_all`: Retrieve all procedures.
- `search`: Search for procedures based on various criteria.
- `update`: Update the details of a procedure.
- `delete`: Delete a procedure.
- `refresh`: Refresh the procedure's data from the database.
- `get_info`: Get the additional information of the procedure.
- `set_info`: Set the additional information of the procedure.
- Association methods for experiments, datasets, runs, and records.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.dataset import Dataset, GEMINIDatasetType
from gemini.api.procedure_run import ProcedureRun
from gemini.api.procedure_record import ProcedureRecord
from gemini.db.models.procedures import ProcedureModel
from gemini.db.models.associations import ExperimentProcedureModel, ProcedureDatasetModel
from gemini.db.models.views.experiment_views import ExperimentProceduresViewModel
from gemini.db.models.views.dataset_views import ProcedureDatasetsViewModel
from gemini.db.models.views.run_views import ProcedureRunsViewModel

from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.dataset import Dataset
    from gemini.api.procedure_run import ProcedureRun

logger = logging.getLogger(__name__)

class Procedure(APIBase):
    """
    Represents a procedure entity, including its metadata, associations to experiments, datasets, runs, and records, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the procedure.
        procedure_name (str): The name of the procedure.
        procedure_info (Optional[dict]): Additional information about the procedure.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "procedure_id"))

    procedure_name: str
    procedure_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Procedure object."""
        return f"Procedure(procedure_name={self.procedure_name}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Procedure object."""
        return f"Procedure(procedure_name={self.procedure_name}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        procedure_name: str
    ) -> bool:
        """
        Check if a procedure with the given name exists.

        Examples:
            >>> Procedure.exists("MyProcedure")
            True

            >>> Procedure.exists("NonExistentProcedure")
            False

        Args:
            procedure_name (str): The name of the procedure.
        Returns:
            bool: True if the procedure exists, False otherwise.
        """
        try:
            exists = ProcedureModel.exists(procedure_name=procedure_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of procedure: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        procedure_name: str,
        procedure_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Procedure"]:
        """
        Create a new procedure.

        Examples:
            >>> Procedure.create("MyProcedure", {"description": "A sample procedure"})
            Procedure(procedure_name='MyProcedure', id=UUID('...'))

        Args:
            procedure_name (str): The name of the procedure.
            procedure_info (dict, optional): Additional information about the procedure. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[Procedure]: The created procedure, or None if an error occurred.
        """
        try:
            db_instance = ProcedureModel.get_or_create(
                procedure_name=procedure_name,
                procedure_info=procedure_info,
            )
            procedure = cls.model_validate(db_instance)
            if experiment_name:
                procedure.associate_experiment(experiment_name)
            return procedure
        except Exception as e:
            logger.error(f"Error creating procedure: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        procedure_name: str,
        experiment_name: str = None
    ) -> Optional["Procedure"]:
        """
        Retrieve a procedure by its name and experiment.

        Examples:
            >>> Procedure.get("MyProcedure", "MyExperiment")
            Procedure(procedure_name='MyProcedure', id=UUID('...'))

        Args:
            procedure_name (str): The name of the procedure.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Procedure]: The procedure, or None if not found.
        """
        try:
            db_instance = ExperimentProceduresViewModel.get_by_parameters(
                procedure_name=procedure_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Procedure with name {procedure_name} not found.")
                return None
            procedure = cls.model_validate(db_instance)
            return procedure
        except Exception as e:
            logger.error(f"Error getting procedure: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Procedure"]:
        """
        Retrieve a procedure by its ID.

        Examples:
            >>> Procedure.get_by_id(UUID('...'))
            Procedure(procedure_name='MyProcedure', id=UUID('...'))


        Args:
            id (UUID | int | str): The ID of the procedure.
        Returns:
            Optional[Procedure]: The procedure, or None if not found.
        """
        try:
            db_instance = ProcedureModel.get(id)
            if not db_instance:
                logger.warning(f"Procedure with ID {id} does not exist.")
                return None
            procedure = cls.model_validate(db_instance)
            return procedure
        except Exception as e:
            logger.error(f"Error getting procedure by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Procedure"]]:
        """
        Retrieve all procedures.

        Examples:
            >>> procedures = Procedure.get_all()
            >>> for proc in procedures:
            ...     print(proc)
            Procedure(procedure_name='Procedure1', id=UUID('...'))
            Procedure(procedure_name='Procedure2', id=UUID('...'))

        Returns:
            Optional[List[Procedure]]: List of all procedures, or None if not found.
        """
        try:
            procedures = ProcedureModel.all(limit=limit, offset=offset)
            if not procedures or len(procedures) == 0:
                logger.info("No procedures found.")
                return None
            procedures = [cls.model_validate(procedure) for procedure in procedures]
            return procedures
        except Exception as e:
            logger.error(f"Error getting all procedures: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        procedure_name: str = None,
        procedure_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Procedure"]]:
        """
        Search for procedures based on various criteria.

        Examples:
            >>> procedures = Procedure.search(procedure_name="MyProcedure")
            >>> for proc in procedures:
            ...     print(proc)
            Procedure(procedure_name='MyProcedure', id=UUID('...'))


        Args:
            procedure_name (str, optional): The name of the procedure. Defaults to None.
            procedure_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List[Procedure]]: List of matching procedures, or None if not found.
        """
        try:
            if not any([procedure_name, procedure_info, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            procedures = ExperimentProceduresViewModel.search(
                procedure_name=procedure_name,
                procedure_info=procedure_info,
                experiment_name=experiment_name
            )
            if not procedures or len(procedures) == 0:
                logger.info("No procedures found with the provided search parameters.")
                return None
            procedures = [cls.model_validate(procedure) for procedure in procedures]
            return procedures
        except Exception as e:
            logger.error(f"Error searching procedures: {e}")
            return None
        
    def update(
        self,
        procedure_name: str = None,
        procedure_info: dict = None
    ) -> Optional["Procedure"]:
        """
        Update the details of the procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> updated_procedure = procedure.update(procedure_name="UpdatedProcedure")
            >>> print(updated_procedure)
            Procedure(procedure_name='UpdatedProcedure', id=UUID('...'))

        Args:
            procedure_name (str, optional): The new name. Defaults to None.
            procedure_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[Procedure]: The updated procedure, or None if an error occurred.
        """
        try:
            if not any([procedure_name, procedure_info]):
                logger.warning("At least one parameter must be provided.")
                return None
            current_id = self.id
            procedure = ProcedureModel.get(current_id)
            if not procedure:
                logger.warning(f"Procedure with ID {current_id} does not exist.")
                return None
            procedure = ProcedureModel.update(
                procedure,
                procedure_name=procedure_name,
                procedure_info=procedure_info
            )
            procedure = self.model_validate(procedure)
            self.refresh()
            return procedure
        except Exception as e:
            logger.error(f"Error updating procedure: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> success = procedure.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the procedure was deleted, False otherwise.
        """
        try:
            current_id = self.id
            procedure = ProcedureModel.get(current_id)
            if not procedure:
                logger.warning(f"Procedure with ID {current_id} does not exist.")
                return False
            ProcedureModel.delete(procedure)
            return True
        except Exception as e:
            logger.error(f"Error deleting procedure: {e}")
            return False
        
    def refresh(self) -> Optional["Procedure"]:
        """
        Refresh the procedure's data from the database.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> refreshed_procedure = procedure.refresh()
            >>> print(refreshed_procedure)
            Procedure(procedure_name='MyProcedure', id=UUID('...'))

        Returns:
            Optional[Procedure]: The refreshed procedure, or None if an error occurred.
        """
        try:
            db_instance = ProcedureModel.get(self.id)
            if not db_instance:
                logger.warning(f"Procedure with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing procedure: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> info = procedure.get_info()
            >>> print(info)
            {'description': 'A sample procedure', 'version': '1.0'}

        Returns:
            Optional[dict]: The procedure's info, or None if not found.
        """
        try:
            current_id = self.id
            procedure = ProcedureModel.get(current_id)
            if not procedure:
                logger.warning(f"Procedure with ID {current_id} does not exist.")
                return None
            procedure_info = procedure.procedure_info
            if not procedure_info:
                logger.info("Procedure info is empty.")
                return None
            return procedure_info
        except Exception as e:
            logger.error(f"Error getting procedure info: {e}")
            return None

    def set_info(self, procedure_info: dict) -> Optional["Procedure"]:
        """
        Set the additional information of the procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> updated_procedure = procedure.set_info({"description": "Updated description"})
            >>> print(updated_procedure.get_info())
            {'description': 'Updated description'}

        Args:
            procedure_info (dict): The new information to set.
        Returns:
            Optional[Procedure]: The updated procedure, or None if an error occurred.
        """
        try:
            current_id = self.id
            procedure = ProcedureModel.get(current_id)
            if not procedure:
                logger.warning(f"Procedure with ID {current_id} does not exist.")
                return None
            procedure = ProcedureModel.update(
                procedure,
                procedure_info=procedure_info
            )
            procedure = self.model_validate(procedure)
            self.refresh()
            return procedure
        except Exception as e:
            logger.error(f"Error setting procedure info: {e}")
            return None        
    
    def get_associated_runs(self) -> Optional[List["ProcedureRun"]]:
        """
        Get all runs associated with this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> runs = procedure.get_associated_runs()
            >>> for run in runs:
            ...     print(run)
            ProcedureRun(id=UUID('...'), procedure_id=UUID('...'), procedure_run_info={'status': 'completed'})
            ProcedureRun(id=UUID('...'), procedure_id=UUID('...'), procedure_run_info={'status': 'in_progress'})


        Returns:
            Optional[List[ProcedureRun]]: A list of associated runs, or None if not found.
        """
        try:
            from gemini.api.procedure_run import ProcedureRun
            current_id = self.id
            procedure_runs = ProcedureRunsViewModel.search(procedure_id=current_id)
            if not procedure_runs or len(procedure_runs) == 0:
                logger.info("No associated runs found.")
                return None
            procedure_runs = [ProcedureRun.model_validate(run) for run in procedure_runs]
            return procedure_runs
        except Exception as e:
            logger.error(f"Error getting associated runs: {e}")
            return None
        
    def create_new_run(self, procedure_run_info: dict = None) -> Optional["ProcedureRun"]:
        """
        Create and associate a new run with this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> new_run = procedure.create_new_run({"status": "in_progress"})
            >>> print(new_run)
            ProcedureRun(id=UUID('...'), procedure_id=UUID('...'), procedure_run_info={'status': 'in_progress'})

        Args:
            procedure_run_info (dict, optional): The run information for the new run. Defaults to None.
        Returns:
            Optional[ProcedureRun]: The created and associated run, or None if an error occurred.
        """
        try:
            from gemini.api.procedure_run import ProcedureRun
            new_procedure_run = ProcedureRun.create(
                procedure_run_info=procedure_run_info,
                procedure_name=self.procedure_name
            )
            if not new_procedure_run:
                logger.info("Failed to create new procedure run.")
                return None
            return new_procedure_run
        except Exception as e:
            logger.error(f"Error creating procedure run: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> experiments = procedure.get_associated_experiments()
            >>> for exp in experiments:
            ...     print(exp)
            Experiment(experiment_name='Experiment1', experiment_start_date=datetime(2023, 1, 1), experiment_end_date=datetime(2023, 12, 31), id=UUID('...'))
            Experiment(experiment_name='Experiment2', experiment_start_date=datetime(2023, 2, 1), experiment_end_date=datetime(2023, 11, 30), id=UUID('...'))

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment_procedures = ExperimentProceduresViewModel.search(procedure_id=self.id)
            if not experiment_procedures or len(experiment_procedures) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(exp) for exp in experiment_procedures]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this procedure with an experiment.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> experiment = procedure.associate_experiment("MyExperiment")
            >>> print(experiment)
            Experiment(experiment_name='MyExperiment', experiment_start_date=datetime(2023, 1, 1), experiment_end_date=datetime(2023, 12, 31), id=UUID('...'))

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
            existing_association = ExperimentProcedureModel.get_by_parameters(
                experiment_id=experiment.id,
                procedure_id=self.id
            )
            if existing_association:
                logger.info(f"Procedure {self.procedure_name} is already associated with experiment {experiment_name}.")
                return self
            new_association = ExperimentProcedureModel.get_or_create(
                experiment_id=experiment.id,
                procedure_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate procedure {self.procedure_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating experiment: {e}")
            return None 

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this procedure from an experiment.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> experiment = procedure.unassociate_experiment("MyExperiment")
            >>> print(experiment)
            Experiment(experiment_name='MyExperiment', experiment_start_date=datetime(2023, 1, 1), experiment_end_date=datetime(2023, 12, 31), id=UUID('...'))

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
            existing_association = ExperimentProcedureModel.get_by_parameters(
                experiment_id=experiment.id,
                procedure_id=self.id
            )
            if not existing_association:
                logger.info(f"Procedure {self.procedure_name} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentProcedureModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to disassociate procedure {self.procedure_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error disassociating experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this procedure is associated with a specific experiment.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> is_associated = procedure.belongs_to_experiment("MyExperiment")
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
            association_exists = ExperimentProcedureModel.exists(
                experiment_id=experiment.id,
                procedure_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking experiment membership: {e}")
            return False
        
    def get_associated_datasets(self) -> List["Dataset"]:
        """
        Get all datasets associated with this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> datasets = procedure.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name='Dataset1', dataset_type='Procedure', collection_date=date(2023, 1, 1), id=UUID('...'))
            Dataset(dataset_name='Dataset2', dataset_type='Procedure', collection_date=date(2023, 2, 1), id=UUID('...'))


        Returns:
            List[Dataset]: A list of associated datasets, or None if not found.
        """
        try:
            from gemini.api.dataset import Dataset
            datasets = ProcedureDatasetsViewModel.search(procedure_id=self.id)
            if not datasets or len(datasets) == 0:
                logger.info("No associated datasets found.")
                return None
            datasets = [Dataset.model_validate(dataset) for dataset in datasets]
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
        Create and associate a new dataset with this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> dataset = procedure.create_new_dataset("MyDataset", {"description": "A sample dataset"}, date(2023, 1, 1), "MyExperiment")
            >>> print(dataset)
            Dataset(dataset_name='MyDataset', dataset_type='Procedure', collection_date=date(2023, 1, 1), id=UUID('...'))

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
                dataset_type=GEMINIDatasetType.Procedure
            )
            if not dataset:
                logger.info("Failed to create new dataset.")
                return None
            dataset = self.associate_dataset(dataset_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating new dataset: {e}")
            return None
    
    def associate_dataset(self, dataset_name: str) -> Optional["Dataset"]:
        """
        Associate this procedure with a dataset.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> dataset = procedure.associate_dataset("MyDataset")
            >>> print(dataset)
            Dataset(dataset_name='MyDataset', dataset_type='Procedure', collection_date=date(2023, 1, 1), id=UUID('...'))

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
            existing_association = ProcedureDatasetModel.get_by_parameters(
                procedure_id=self.id,
                dataset_id=dataset.id
            )
            if existing_association:
                logger.info(f"Dataset {dataset_name} is already associated with procedure {self.procedure_name}.")
                return self
            new_association = ProcedureDatasetModel.get_or_create(
                procedure_id=self.id,
                dataset_id=dataset.id
            )
            if not new_association:
                logger.info(f"Failed to associate dataset {dataset_name} with procedure {self.procedure_name}.")
                return None
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error associating dataset: {e}")
            return None
        
    def insert_record(
        self,
        timestamp: datetime = None,
        collection_date: date = None,
        procedure_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_file: str = None,
        record_info: dict = None,
    ) -> tuple[bool, List[str]]:
        """
        Insert a single procedure record for this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> success, record_ids = procedure.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date(2023, 1, 1),
            ...     procedure_data={"key": "value"},
            ...     dataset_name="MyDataset",
            ...     experiment_name="MyExperiment",
            ...     season_name="MySeason",
            ...     site_name="MySite",
            ...     record_file="path/to/record/file",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> print(success, record_ids)
        True [UUID('...')]


        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            procedure_data (dict, optional): The procedure data. Defaults to {{}}.
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
            
            if not procedure_data and not record_file:
                raise ValueError("Either procedure_data or record_file must be provided.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            if not dataset_name:
                dataset_name = f"{self.procedure_name} Dataset {collection_date}"
            procedure_name = self.procedure_name
            procedure_record = ProcedureRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                procedure_name=procedure_name,
                procedure_data=procedure_data,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_file=record_file,
                record_info=record_info,
                insert_on_create=False
            )
            success, inserted_record_ids = ProcedureRecord.insert([procedure_record])
            if not success:
                raise Exception("Failed to insert procedure record.")
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting procedure record: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        procedure_data: List[dict] = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_files: List[str] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Insert multiple procedure records for this procedure.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> success, record_ids = procedure.insert_records(
            ...     timestamps=[datetime.now(), datetime.now()],
            ...     collection_date=date(2023, 1, 1),
            ...     procedure_data=[{"key1": "value1"}, {"key2": "value2"}],
            ...     dataset_name="MyDataset",
            ...     experiment_name="MyExperiment",
            ...     season_name="MySeason",
            ...     site_name="MySite",
            ...     record_files=["path/to/record1", "path/to/record2"],
            ...     record_info=[{"info_key1": "info_value1"}, {"info_key2": "info_value2"}]
            ... )
            >>> print(success, record_ids)
        True [UUID('...'), UUID('...')]

        Args:
            timestamps (List[datetime], optional): List of timestamps. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            procedure_data (List[dict], optional): List of procedure data. Defaults to [].
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
            
            if procedure_data and len(procedure_data) != len(timestamps):
                raise ValueError("procedure_data must have the same length as timestamps.")
            
            if record_files and len(record_files) != len(timestamps):
                raise ValueError("record_files must have the same length as timestamps.")
            
            collection_date = collection_date if collection_date else timestamps[0].date()
            
            if not dataset_name:
                dataset_name = f"{self.procedure_name} Dataset {collection_date}"
            
            procedure_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Procedure " + self.procedure_name):
                procedure_record = ProcedureRecord.create(
                    timestamp = timestamps[i],
                    collection_date = collection_date,
                    procedure_name= self.procedure_name,
                    procedure_data = procedure_data[i]  if procedure_data else {},
                    dataset_name = dataset_name,
                    experiment_name = experiment_name,
                    season_name = season_name,
                    site_name = site_name,
                    record_file= record_files[i] if record_files else None,
                    record_info = record_info[i] if record_info else {},
                    insert_on_create=False
                )
                procedure_records.append(procedure_record)

            success, inserted_record_ids = ProcedureRecord.insert(procedure_records)
            if not success:
                logger.info("Failed to insert procedure records.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting procedure records: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_info: dict = None
    ) -> List[ProcedureRecord]:
        """
        Search for procedure records associated with this procedure based on search parameters.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> records = procedure.search_records(
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="MyDataset",
            ...     experiment_name="MyExperiment",
            ...     season_name="MySeason",
            ...     site_name="MySite",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 1, 1, 12, 0), procedure_name='MyProcedure', dataset_name='MyDataset', experiment_name='MyExperiment', season_name='MySeason', site_name='MySite')
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 1, 2, 12, 0), procedure_name='MyProcedure', dataset_name='MyDataset', experiment_name='MyExperiment', season_name='MySeason', site_name='MySite')

        Args:
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Returns:
            List[ProcedureRecord]: List of matching procedure records, or empty list if not found.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = ProcedureRecord.search(
                collection_date=collection_date,
                dataset_name=dataset_name,
                procedure_name=self.procedure_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching procedure records: {e}")
            return []
        
    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> List[ProcedureRecord]:
        """
        Filter procedure records associated with this procedure using a custom filter function.

        Examples:
            >>> procedure = Procedure.get("MyProcedure")
            >>> records = procedure.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 1, 31),
            ...     dataset_names=["MyDataset"],
            ...     experiment_names=["MyExperiment"],
            ...     season_names=["MySeason"],
            ...     site_names=["MySite"]
            ... )
            >>> for record in records:
            ...     print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 1, 1, 12, 0), procedure_name='MyProcedure', dataset_name='MyDataset', experiment_name='MyExperiment', season_name='MySeason', site_name='MySite')
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 1, 2, 12, 0), procedure_name='MyProcedure', dataset_name='MyDataset', experiment_name='MyExperiment', season_name='MySeason', site_name='MySite')

        Args:
            start_timestamp (Optional[datetime], optional): Start of timestamp range. Defaults to None.
            end_timestamp (Optional[datetime], optional): End of timestamp range. Defaults to None.
            dataset_names (Optional[List[str]], optional): List of dataset names. Defaults to None.
            experiment_names (Optional[List[str]], optional): List of experiment names. Defaults to None.
            season_names (Optional[List[str]], optional): List of season names. Defaults to None.
            site_names (Optional[List[str]], optional): List of site names. Defaults to None.
        Returns:
            List[ProcedureRecord]: List of filtered procedure records, or empty list if not found.
        """
        try:
            records = ProcedureRecord.filter(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                procedure_names= [self.procedure_name],
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering procedure records: {e}")
            return []