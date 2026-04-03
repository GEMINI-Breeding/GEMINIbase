"""
This module defines the Dataset class, which represents a dataset entity, including its metadata, type, and associations to experiments and records.

It includes methods for creating, retrieving, updating, and deleting datasets, as well as methods for checking existence, searching, and managing associations with experiments and dataset records.

This module includes the following methods:

- `exists`: Check if a dataset with the given name exists.
- `create`: Create a new dataset.
- `get`: Retrieve a dataset by its name.
- `get_by_id`: Retrieve a dataset by its ID.
- `get_all`: Retrieve all datasets.
- `search`: Search for datasets based on various criteria.
- `update`: Update the details of a dataset.
- `delete`: Delete a dataset.
- `refresh`: Refresh the dataset's data from the database.
- `get_info`: Get the additional information of the dataset.
- `set_info`: Set the additional information of the dataset.
- `associate_experiment`: Associate the dataset with an experiment.
- `unassociate_experiment`: Unassociate the dataset from an experiment.
- `get_associated_experiments`: Get all experiments associated with the dataset.
- `get_records`: Get all records associated with the dataset.
- `add_record`: Add a new record to the dataset.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.enums import GEMINIDatasetType
from gemini.api.dataset_type import DatasetType
from gemini.api.dataset_record import DatasetRecord
from gemini.db.models.datasets import DatasetModel
from gemini.db.models.dataset_types import DatasetTypeModel
from gemini.db.models.associations import ExperimentDatasetModel
from gemini.db.models.views.experiment_views import ExperimentDatasetsViewModel

from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment  # Avoid circular import issues

logger = logging.getLogger(__name__)

class Dataset(APIBase):
    """
    Represents a dataset entity, including its metadata, type, and associations to experiments and records.

    Attributes:
        id (Optional[ID]): The unique identifier of the dataset.
        collection_date (date): The collection date of the dataset.
        dataset_name (str): The name of the dataset.
        dataset_info (Optional[dict]): Additional information about the dataset.
        dataset_type_id (int): The ID of the dataset type.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "dataset_id"))

    collection_date: date
    dataset_name: str
    dataset_info: Optional[dict] = None
    dataset_type_id: int

    def __str__(self):
        """Return a string representation of the Dataset object."""
        return f"Dataset(dataset_name={self.dataset_name}, collection_date={self.collection_date}, dataset_type={GEMINIDatasetType(self.dataset_type_id).name}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Dataset object."""
        return f"Dataset(dataset_name={self.dataset_name}, collection_date={self.collection_date}, dataset_type={GEMINIDatasetType(self.dataset_type_id).name}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        dataset_name: str,
    ) -> bool:
        """
        Check if a dataset with the given name exists.

        Examples:
            >>> Dataset.exists("my_dataset")
            True
            >>> Dataset.exists("non_existent_dataset")
            False

        Args:
            dataset_name (str): The name of the dataset.
        Returns:
            bool: True if the dataset exists, False otherwise.
        """
        try:
            exists = DatasetModel.exists(
                dataset_name=dataset_name,
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of dataset: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        dataset_name: str,
        dataset_info: dict = None,
        dataset_type: GEMINIDatasetType = GEMINIDatasetType.Default,
        collection_date: date = date.today(),
        experiment_name: str = None
    ) -> Optional["Dataset"]:
        """
        Create a new dataset. If the dataset already exists, it will return the existing dataset.

        Examples:
            >>> dataset = Dataset.create("my_dataset", {"description": "Test dataset"})
            >>> print(dataset)
            Dataset(dataset_name=my_dataset, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Args:
            dataset_name (str): The name of the dataset.
            dataset_info (dict, optional): Additional information about the dataset. Defaults to {{}}.
            dataset_type (GEMINIDatasetType, optional): The type of the dataset. Defaults to Default.
            collection_date (date, optional): The collection date. Defaults to today.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional["Dataset"]: The created dataset, or None if an error occurred.
        """
        try:
            db_instance = DatasetModel.get_or_create(
                collection_date=collection_date,
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                dataset_type_id=dataset_type.value,
            )
            dataset = cls.model_validate(db_instance)
            if experiment_name:
                dataset.associate_experiment(experiment_name=experiment_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        dataset_name: str,
        experiment_name: str = None
    ) -> Optional["Dataset"]:
        """
        Retrieve a dataset by its name.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> print(dataset)
            Dataset(dataset_name=my_dataset, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Args:
            dataset_name (str): The name of the dataset.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional["Dataset"]: The retrieved dataset, or None if not found.
        """
        try:
            db_instance = ExperimentDatasetsViewModel.get_by_parameters(
                dataset_name=dataset_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Dataset with name {dataset_name} not found.")
                return None
            dataset = cls.model_validate(db_instance)
            return dataset
        except Exception as e:
            logger.error(f"Error getting dataset: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Dataset"]:
        """
        Retrieve a dataset by its ID.

        Examples:
            >>> dataset = Dataset.get_by_id(UUID('...'))
            >>> print(dataset)
            Dataset(dataset_name=my_dataset, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Args:
            id (UUID | int | str): The ID of the dataset.
        Returns:
            Optional["Dataset"]: The retrieved dataset, or None if not found.
        """
        try:
            db_instance = DatasetModel.get(id)
            if not db_instance:
                logger.warning(f"Dataset with ID {id} does not exist.")
                return None
            dataset = cls.model_validate(db_instance)
            return dataset
        except Exception as e:
            logger.error(f"Error getting dataset by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Dataset"]]:
        """
        Retrieve all datasets.

        Examples:
            >>> datasets = Dataset.get_all()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name=my_dataset1, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))
            Dataset(dataset_name=my_dataset2, collection_date=2023-10-02, dataset_type=Sensor, id=UUID('...'))

        Returns:
            Optional[List["Dataset"]]: A list of all datasets, or None if an error occurred.
        """
        try:
            datasets = DatasetModel.all(limit=limit, offset=offset)
            if not datasets or len(datasets) == 0:
                logger.info("No datasets found.")
                return None
            datasets = [cls.model_validate(dataset) for dataset in datasets]
            return datasets
        except Exception as e:
            logger.error(f"Error getting all datasets: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        dataset_name: str = None,
        dataset_info: dict = None,
        dataset_type: GEMINIDatasetType = None,
        collection_date: date = None,
        experiment_name: str = None,
    ) -> Optional[List["Dataset"]]:
        """
        Search for datasets based on various criteria.

        Examples:
            >>> datasets = Dataset.search(dataset_name="my_dataset")
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name=my_dataset, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Args:
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            dataset_info (dict, optional): Additional information about the dataset. Defaults to None.
            dataset_type (GEMINIDatasetType, optional): The type of the dataset. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List["Dataset"]]: A list of datasets matching the search criteria, or None if an error occurred.
        """
        try:
            if not any([dataset_name, dataset_info, dataset_type, collection_date, experiment_name]):
                logger.warning("At least one parameter must be provided.")
                return None
            datasets = ExperimentDatasetsViewModel.search(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                dataset_type=dataset_type,
                collection_date=collection_date,
                experiment_name=experiment_name
            )
            if not datasets or len(datasets) == 0:
                logger.info("No datasets found with the provided search parameters.")
                return None
            datasets = [cls.model_validate(dataset) for dataset in datasets]
            return datasets
        except Exception as e:
            logger.error(f"Error searching datasets: {e}")
            return None
        
    def update(
        self,
        dataset_name: str = None,
        dataset_info: dict = None,
        dataset_type: GEMINIDatasetType = None,
        collection_date: date = None
    ) -> Optional["Dataset"]:
        """
        Update the details of a dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> updated_dataset = dataset.update(dataset_name="new_dataset_name", dataset_info={"description": "Updated dataset"})
            >>> print(updated_dataset)
            Dataset(dataset_name=new_dataset_name, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Args:
            dataset_name (str, optional): The new name of the dataset. Defaults to None.
            dataset_info (dict, optional): The new additional information about the dataset. Defaults to None.
            dataset_type (GEMINIDatasetType, optional): The new type of the dataset. Defaults to None.
            collection_date (date, optional): The new collection date. Defaults to None.
        Returns:
            Optional["Dataset"]: The updated dataset, or None if an error occurred.
        """
        try:
            if not any([dataset_name, dataset_info, dataset_type, collection_date]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            current_id = self.id
            dataset = DatasetModel.get(current_id)
            if not dataset:
                logger.warning(f"Dataset with ID {current_id} does not exist.")
                return None
            dataset = DatasetModel.update(
                dataset,
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                dataset_type_id=dataset_type.value if dataset_type else None,
                collection_date=collection_date
            )
            dataset = self.model_validate(dataset)
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error updating dataset: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete a dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> success = dataset.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the dataset was deleted successfully, False otherwise.
        """
        try:
            current_id = self.id
            dataset = DatasetModel.get(current_id)
            if not dataset:
                logger.warning(f"Dataset with ID {current_id} does not exist.")
                return False
            DatasetModel.delete(dataset)
            return True
        except Exception as e:
            logger.error(f"Error deleting dataset: {e}")
            return False
        
    def refresh(self) -> Optional["Dataset"]:
        """
        Refresh the dataset's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> refreshed_dataset = dataset.refresh()
            >>> print(refreshed_dataset)
            Dataset(dataset_name=my_dataset, collection_date=2023-10-01, dataset_type=Default, id=UUID('...'))

        Returns:
            Optional["Dataset"]: The refreshed dataset, or None if an error occurred.
        """
        try:
            db_instance = DatasetModel.get(self.id)
            if not db_instance:
                logger.warning(f"Dataset with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing dataset: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> dataset_info = dataset.get_info()
            >>> print(dataset_info)
            {'description': 'Test dataset', 'created_by': 'user1'}

        Returns:
            Optional[dict]: The additional information of the dataset, or None if an error occurred.
        """
        try:
            current_id = self.id
            dataset = DatasetModel.get(current_id)
            if not dataset:
                logger.warning(f"Dataset with ID {current_id} does not exist.")
                return None
            dataset_info = dataset.dataset_info
            if not dataset_info:
                logger.info("Dataset info is empty.")
                return None
            return dataset_info
        except Exception as e:
            logger.error(f"Error getting dataset info: {e}")
            return None
        
    def set_info(self, dataset_info: dict) -> Optional["Dataset"]:
        """
        Set the additional information of the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> updated_dataset = dataset.set_info({"description": "Updated dataset", "created_by": "user1"})
            >>> print(updated_dataset.get_info())
            {'description': 'Updated dataset', 'created_by': 'user1'}

        Args:
            dataset_info (dict): The additional information to set.
        Returns:
            Optional["Dataset"]: The updated dataset, or None if an error occurred.
        """
        try:
            current_id = self.id
            dataset = DatasetModel.get(current_id)
            if not dataset:
                logger.warning(f"Dataset with ID {current_id} does not exist.")
                return None
            dataset = DatasetModel.update(
                dataset,
                dataset_info=dataset_info,
            )
            dataset = self.model_validate(dataset)
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error setting dataset info: {e}")
            return None
        
    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> experiments = dataset.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=experiment1, experiment_start_date='2023-10-01', experiment_end_date='2023-10-31', id=UUID('...'))


        Returns:
            Optional[List["Experiment"]]: A list of experiments associated with the dataset, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            current_id = self.id
            experiment_datasets = ExperimentDatasetsViewModel.search(dataset_id=current_id)
            if not experiment_datasets or len(experiment_datasets) == 0:
                logger.info(f"No experiments associated with dataset ID {current_id}.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiment_datasets]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate the dataset with an experiment.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> experiment = dataset.associate_experiment("experiment1")
            >>> print(experiment)
            Experiment(experiment_name=experiment1, experiment_start_date='2023-10-01', experiment_end_date='2023-10-31', id=UUID('...'))

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional["Experiment"]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentDatasetModel.get_by_parameters(
                experiment_id=experiment.id,
                dataset_id=self.id
            )
            if existing_association:
                logger.info(f"Dataset {self.dataset_name} is already associated with experiment {experiment_name}.")
                return experiment
            association = ExperimentDatasetModel.get_or_create(
                experiment_id=experiment.id,
                dataset_id=self.id
            )
            if not association:
                logger.info(f"Failed to associate dataset {self.dataset_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating dataset with experiment: {e}")
            return None 

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate the dataset from an experiment.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> experiment = dataset.unassociate_experiment("experiment1")
            >>> print(experiment)
            Experiment(experiment_name=experiment1, experiment_start_date='2023-10-01', experiment_end_date='2023-10-31', id=UUID('...'))

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional["Experiment"]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentDatasetModel.get_by_parameters(
                experiment_id=experiment.id,
                dataset_id=self.id
            )
            if not existing_association:
                logger.info(f"Dataset {self.dataset_name} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentDatasetModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate dataset {self.dataset_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating dataset from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if the dataset belongs to an experiment.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> belongs = dataset.belongs_to_experiment("experiment1")
            >>> print(belongs)
            True

        Args:
            experiment_name (str): The name of the experiment.
        Returns:
            bool: True if the dataset belongs to the experiment, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentDatasetModel.exists(
                experiment_id=experiment.id,
                dataset_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if dataset belongs to experiment: {e}")
            return False
        

    def insert_record(
        self,
        timestamp: datetime = None,
        collection_date: date = None,
        dataset_data: dict = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_file: str = None,
        record_info: dict = None,
    ) -> tuple[bool, List[str]]:
        """
        Add a new record to the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> success, record_ids = dataset.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date.today(),
            ...     dataset_data={"key": "value"},
            ...     experiment_name="experiment1",
            ...     season_name="season1",
            ...     site_name="site1",
            ...     record_file="path/to/file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> print(success, record_ids)
            True [UUID(...)]


        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to None.
            collection_date (date, optional): The collection date of the record. Defaults to None.
            dataset_data (dict, optional): The data of the record. Defaults to {}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_file (str, optional): The file associated with the record. Defaults to None.
            record_info (dict, optional): Additional information about the record. Defaults to {}.
        Returns:
            tuple[bool, List[str]]: A tuple containing a success flag and a list of inserted record IDs.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("Please provide at least one of the following: experiment_name, season_name, site_name.")

            if not dataset_data and not record_file:
                raise ValueError("Please provide either dataset_data or record_file.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            dataset_name = self.dataset_name
            dataset_record = DatasetRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                dataset_data=dataset_data,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_file=record_file if record_file else None,
                record_info=record_info if record_info else {},
                insert_on_create=False
            )
            success, inserted_record_ids = DatasetRecord.insert([dataset_record])
            if not success:
                logger.info(f"Failed to add record for dataset {self.dataset_name}.")
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error adding record to dataset {self.dataset_name}: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        dataset_data: List[dict] = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_files: List[str] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Add new records to the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> success, record_ids = dataset.insert_records(
            ...     timestamps=[datetime.now(), datetime.now()],
            ...     collection_date=date.today(),
            ...     dataset_data=[{"key1": "value1"}, {"key2": "value2"}],
            ...     experiment_name="experiment1",
            ...     season_name="season1",
            ...     site_name="site1",
            ...     record_files=["path/to/file1.txt", "path/to/file2.txt"],
            ...     record_info=[{"info_key1": "info_value1"}, {"info_key2": "info_value2"}]
            ... )
            >>> print(success, record_ids)
            True [UUID(...), UUID(...)]

        Args:
            timestamps (List[datetime], optional): The timestamps of the records. Defaults to None.
            collection_date (date, optional): The collection date of the records. Defaults to None.
            dataset_data (List[dict], optional): The data of the records. Defaults to [].
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_files (List[str], optional): The files associated with the records. Defaults to None.
            record_info (List[dict], optional): Additional information about the records. Defaults to [].
        Returns:
            tuple[bool, List[str]]: A tuple containing a success flag and a list of inserted record IDs.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("Please provide at least one of the following: experiment_name, season_name, site_name.")
            
            if len(timestamps) == 0:
                raise ValueError("Please provide at least one timestamp.")
            
            if len(dataset_data) != len(timestamps):
                raise ValueError("dataset_data length must match timestamps length.")
            
            if record_files and len(record_files) != len(timestamps):
                raise ValueError("record_files length must match timestamps length.")
            
            collection_date = collection_date if collection_date else timestamps[0].date()
            dataset_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Dataset: " + self.dataset_name):
                dataset_record = DatasetRecord.create(
                    timestamp=timestamps[i],
                    collection_date=collection_date,
                    dataset_name=self.dataset_name,
                    dataset_data=dataset_data[i] if dataset_data else {},
                    experiment_name=experiment_name,
                    season_name=season_name,
                    site_name=site_name,
                    record_file=record_files[i] if record_files else None,
                    record_info=record_info[i] if record_info else {},
                    insert_on_create=False
                )
                dataset_records.append(dataset_record)
            success, inserted_record_ids = DatasetRecord.insert(dataset_records)
            if not success:
                logger.info(f"Failed to add records for dataset {self.dataset_name}.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error adding records to dataset {self.dataset_name}: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_info: dict = None,
    ) -> List[DatasetRecord]:
        """
        Search for records in the dataset.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> records = dataset.search_records(
            ...     collection_date=date.today(),
            ...     experiment_name="experiment1",
            ...     season_name="season1",
            ...     site_name="site1",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            DatasetRecord(id=UUID(...), dataset_name='my_dataset', timestamp='2023-10-01T12:00:00', dataset_data={...}, experiment_name='experiment1', season_name='season1', site_name='site1')

        Args:
            collection_date (date, optional): The collection date of the records. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            record_info (dict, optional): Additional information about the records. Defaults to None.
        Returns:
            List[DatasetRecord]: A list of records matching the search criteria.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = DatasetRecord.search(
                collection_date=collection_date,
                dataset_name=self.dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching records in dataset {self.dataset_name}: {e}")
            return []
        

    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> List[DatasetRecord]:
        """
        Filter records in the dataset based on criteria.

        Examples:
            >>> dataset = Dataset.get("my_dataset")
            >>> records = dataset.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     experiment_names=["experiment1", "experiment2"],
            ...     season_names=["season1"],
            ...     site_names=["site1"]
            ... )
            >>> for record in records:
            ...     print(record)
            DatasetRecord(record_id=UUID(...), dataset_name='my_dataset', timestamp='2023-10-01T12:00:00', dataset_data={...}, experiment_name='experiment1', season_name='season1', site_name='site1')


        Args:
            start_timestamp (Optional[datetime], optional): The start timestamp for filtering. Defaults to None.
            end_timestamp (Optional[datetime], optional): The end timestamp for filtering. Defaults to None.
            experiment_names (Optional[List[str]], optional): The names of the experiments. Defaults to None.
            season_names (Optional[List[str]], optional): The names of the seasons. Defaults to None.
            site_names (Optional[List[str]], optional): The names of the sites. Defaults to None.
        Returns:
            List[DatasetRecord]: A list of filtered records.
        """
        try:
            records = DatasetRecord.filter(
                dataset_names=[self.dataset_name],
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering records in dataset {self.dataset_name}: {e}")
            return []
