"""
This module defines the Model class, which represents a model entity, including its metadata, associations to runs, experiments, datasets, and records.

It includes methods for creating, retrieving, updating, and deleting models, as well as methods for checking existence, searching, and managing associations with related entities and records.

This module includes the following methods:

- `exists`: Check if a model with the given name exists.
- `create`: Create a new model.
- `get`: Retrieve a model by its name.
- `get_by_id`: Retrieve a model by its ID.
- `get_all`: Retrieve all models.
- `search`: Search for models based on various criteria.
- `update`: Update the details of a model.
- `delete`: Delete a model.
- `refresh`: Refresh the model's data from the database.
- `get_info`: Get the additional information of the model.
- `set_info`: Set the additional information of the model.
- Association methods for runs, experiments, datasets, and records.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.dataset import Dataset, GEMINIDatasetType
from gemini.api.model_run import ModelRun
from gemini.api.model_record import ModelRecord
from gemini.db.models.models import ModelModel
from gemini.db.models.associations import ExperimentModelModel, ModelDatasetModel
from gemini.db.models.views.experiment_views import ExperimentModelsViewModel
from gemini.db.models.views.dataset_views import ModelDatasetsViewModel
from gemini.db.models.views.run_views import ModelRunsViewModel

from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.dataset import Dataset
    from gemini.api.model_run import ModelRun

logger = logging.getLogger(__name__)

class Model(APIBase):
    """
    Represents a model entity, including its metadata, associations to runs, experiments, datasets, and records.

    Attributes:
        id (Optional[ID]): The unique identifier of the model.
        model_name (str): The name of the model.
        model_url (Optional[str]): The URL of the model.
        model_info (Optional[dict]): Additional information about the model.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "model_id"))

    model_name: str
    model_url: Optional[str] = None
    model_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Model object."""
        return f"Model(model_name={self.model_name}, model_url={self.model_url}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Model object."""
        return f"Model(model_name={self.model_name}, model_url={self.model_url}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        model_name: str
    ) -> bool:
        """
        Check if a model with the given name exists.

        Examples:
            >>> Model.exists("example_model")
            True
            >>> Model.exists("non_existent_model")
            False

        Args:
            model_name (str): The name of the model.
        Returns:
            bool: True if the model exists, False otherwise.
        """
        try:
            exists = ModelModel.exists(model_name=model_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of model: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        model_name: str,
        model_url: str = None,
        model_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Model"]:
        """
        Create a new model.

        If the model already exists, it will return the existing model.

        Examples:
            >>> model = Model.create("example_model", "http://example.com/model")
            >>> print(model)
            Model(model_name=example_model, model_url=http://example.com/model, id=123e456-e789-12d3-a456-426614174000)

        Args:
            model_name (str): The name of the model.
            model_url (str, optional): The URL of the model. Defaults to None.
            model_info (dict, optional): Additional information about the model. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional["Model"]: The created model, or None if an error occurred.
        """
        try:
            db_instance = ModelModel.get_or_create(
                model_name=model_name,
                model_url=model_url,
                model_info=model_info,
            )
            model = cls.model_validate(db_instance)
            if experiment_name:
                model.associate_experiment(experiment_name=experiment_name)
            return model
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        model_name: str,
        experiment_name: str = None
    ) -> Optional["Model"]:
        """
        Retrieve a model by its name.

        Examples:
            >>> model = Model.get("example_model")
            >>> print(model)
            Model(model_name=example_model, model_url=http://example.com/model, id=UUID('...'))

        Args:
            model_name (str): The name of the model.
        Returns:
            Optional["Model"]: The model, or None if not found.
        """
        try:
            db_instance = ExperimentModelsViewModel.get_by_parameters(
                model_name=model_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Model with name {model_name} not found.")
                return None
            model = cls.model_validate(db_instance)
            return model
        except Exception as e:
            logger.error(f"Error getting model: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Model"]:
        """
        Retrieve a model by its ID.

        Examples:
            >>> model = Model.get_by_id(UUID('...'))
            Model(model_name=example_model, model_url=http://example.com/model, id=UUID('...'))

        Args:
            id (UUID | int | str): The ID of the model.
        Returns:
            Optional["Model"]: The model, or None if not found.
        """
        try:
            db_instance = ModelModel.get(id)
            if not db_instance:
                logger.warning(f"Model with ID {id} does not exist.")
                return None
            model = cls.model_validate(db_instance)
            return model
        except Exception as e:
            logger.error(f"Error getting model by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Model"]]:
        """
        Retrieve all models.

        Examples:
            >>> models = Model.get_all()
            >>> for model in models:
            ...     print(model)
            Model(model_name=example_model1, model_url=http://example.com/model1, id=UUID('...'))
            Model(model_name=example_model2, model_url=http://example.com/model2, id=UUID('...'))

        Returns:
            Optional[List["Model"]]: List of all models, or None if not found.
        """
        try:
            models = ModelModel.all(limit=limit, offset=offset)
            if not models or len(models) == 0:
                logger.info("No models found.")
                return None
            models = [cls.model_validate(model) for model in models]
            return models
        except Exception as e:
            logger.error(f"Error getting all models: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        model_name: str = None,
        model_info: dict = None,
        model_url: str = None,
        experiment_name: str = None
    ) -> Optional[List["Model"]]:
        """
        Search for models based on various criteria.

        Examples:
            >>> models = Model.search(model_name="example_model")
            >>> for model in models:
            ...     print(model)
            Model(model_name=example_model, model_url=http://example.com/model, id=UUID('...'))

        Args:
            model_name (str, optional): The name of the model. Defaults to None.
            model_url (str, optional): The URL of the model. Defaults to None.
            model_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment to filter by. Defaults to None.
        Returns:
            Optional[List["Model"]]: List of matching models, or None if not found.
        """
        try:
            if not any([model_name, model_info, model_url, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            models = ExperimentModelsViewModel.search(
                model_name=model_name,
                model_info=model_info,
                model_url=model_url,
                experiment_name=experiment_name
            )
            if not models or len(models) == 0:
                logger.info("No models found with the provided search parameters.")
                return None
            models = [cls.model_validate(model) for model in models]
            return models
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return None
        
    def update(
        self,
        model_name: str = None,
        model_url: str = None,
        model_info: dict = None
    ) -> Optional["Model"]:
        """
        Update the details of the model.

        Examples:
            >>> model = Model.get("example_model")
            >>> updated_model = model.update(model_name="new_example_model")
            >>> print(updated_model)
            Model(model_name=new_example_model, model_url=http://example.com/model, id=UUID('...'))
        Args:
            model_name (str, optional): The new name. Defaults to None.
            model_url (str, optional): The new URL. Defaults to None.
            model_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional["Model"]: The updated model, or None if an error occurred.
        """
        try:
            if not any([model_name, model_url, model_info]):
                logger.warning("At least one update parameter must be provided.")
                return None
            current_id = self.id
            model = ModelModel.get(current_id)
            if not model:
                logger.warning(f"Model with ID {current_id} does not exist.")
                return None
            model = ModelModel.update(
                model,
                model_name=model_name,
                model_url=model_url,
                model_info=model_info
            )
            model = self.model_validate(model)
            self.refresh()
            return model
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the model.

        Examples:
            >>> model = Model.get("example_model")
            >>> success = model.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the model was deleted, False otherwise.
        """
        try:
            current_id = self.id
            model = ModelModel.get(current_id)
            if not model:
                logger.warning(f"Model with ID {current_id} does not exist.")
                return False
            ModelModel.delete(model)
            return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return False
        
    def refresh(self) -> Optional["Model"]:
        """
        Refresh the model's data from the database.

        Examples:
            >>> model = Model.get("example_model")
            >>> refreshed_model = model.refresh()
            >>> print(refreshed_model)
            Model(model_name=example_model, model_url=http://example.com/model, id=UUID('...'))

        Returns:
            Optional["Model"]: The refreshed model, or None if an error occurred.
        """
        try:
            db_instance = ModelModel.get(self.id)
            if not db_instance:
                logger.warning(f"Model with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing model: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the model.

        Examples:
            >>> model = Model.get("example_model")
            >>> info = model.get_info()
            >>> print(info)
            {'key1': 'value1', 'key2': 'value2'}

        Returns:
            Optional[dict]: The model's info, or None if not found.
        """
        try:
            current_id = self.id
            model = ModelModel.get(current_id)
            if not model:
                logger.warning(f"Model with ID {current_id} does not exist.")
                return None
            model_info = model.model_info
            if not model_info:
                logger.info("Model info is empty.")
                return None
            return model_info
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
        
    def set_info(self, model_info: dict) -> Optional["Model"]:
        """
        Set the additional information of the model.

        Examples:
            >>> model = Model.get("example_model")
            >>> updated_model = model.set_info({"key1": "new_value1", "key2": "new_value2"})
            >>> print(updated_model.get_info())
            {'key1': 'new_value1', 'key2': 'new_value2'}
        
        Args:
            model_info (dict): The new information to set.
        Returns:
            Optional["Model"]: The updated model, or None if an error occurred.
        """
        try:
            current_id = self.id
            model = ModelModel.get(current_id)
            if not model:
                logger.warning(f"Model with ID {current_id} does not exist.")
                return None
            model = ModelModel.update(
                model,
                model_info=model_info
            )
            model = self.model_validate(model)
            self.refresh()
            return model
        except Exception as e:
            logger.error(f"Error setting model info: {e}")
            return None
        
    def get_associated_runs(self) -> Optional[List["ModelRun"]]:
        """
        Get all runs associated with this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> runs = model.get_associated_runs()
            >>> for run in runs:
            ...     print(run)
            ModelRun(id=UUID(...), model_id=UUID(...), model_run_info={...})
            ModelRun(id=UUID(...), model_id=UUID(...), model_run_info={...})

        Returns:
            Optional[List["ModelRun"]]: A list of associated runs, or None if not found.
        """
        try:
            from gemini.api.model_run import ModelRun
            current_id = self.id
            model_runs = ModelRunsViewModel.search(model_id=current_id)
            if not model_runs or len(model_runs) == 0:
                logger.info(f"No runs associated with model {self.model_name}.")
                return None
            runs = [ModelRun.model_validate(model_run) for model_run in model_runs]
            return runs
        except Exception as e:
            logger.error(f"Error getting associated runs: {e}")
            return None

    def create_new_run(self, model_run_info: dict) -> Optional["ModelRun"]:
        """
        Create and associate a new run with this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> run_info = {"run_name": "example_run", "run_parameters": {"param1": "value1"}}
            >>> new_run = model.create_new_run(run_info)
            >>> print(new_run)
            ModelRun(id=UUID(...), model_id=UUID(...), model_run_info={...})

        Args:
            model_run_info (dict): The run information for the new run.
        Returns:
            Optional["ModelRun"]: The created and associated run, or None if an error occurred.
        """
        try:
            from gemini.api.model_run import ModelRun
            current_name = self.model_name
            model_run = ModelRun.create(
                model_run_info=model_run_info,
                model_name=current_name
            )
            if not model_run:
                logger.info(f"Failed to create run for model {self.model_name}.")
                return None
            return model_run
        except Exception as e:
            logger.error(f"Error creating run: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> experiments = model.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(id=UUID(...), experiment_name="example_experiment", experiment_start_date="2023-10-01", experiment_end_date="2023-10-31")
            Experiment(id=UUID(...), experiment_name="another_experiment", experiment_start_date="2023-11-01", experiment_end_date="2023-11-30")

        Returns:
            Optional[List["Experiment"]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            current_id = self.id
            experiment_models = ExperimentModelsViewModel.search(model_id=current_id)
            if not experiment_models or len(experiment_models) == 0:
                logger.info(f"No experiments associated with model {self.model_name}.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiment_models]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this model with an experiment.

        Examples:
            >>> model = Model.get("example_model")
            >>> experiment = model.associate_experiment("example_experiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name="example_experiment", experiment_start_date="2023-10-01", experiment_end_date="2023-10-31")

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional["Experiment"]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentModelModel.exists(
                experiment_id=experiment.id,
                model_id=self.id
            )
            if existing_association:
                logger.info(f"Model {self.model_name} is already associated with experiment {experiment_name}.")
                return experiment
            new_association = ExperimentModelModel.get_or_create(
                experiment_id=experiment.id,
                model_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate model {self.model_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this model from an experiment.

        Examples:
            >>> model = Model.get("example_model")
            >>> experiment = model.unassociate_experiment("example_experiment")
            >>> print(experiment)
            Experiment(id=UUID(...), experiment_name="example_experiment", experiment_start_date="2023-10-01", experiment_end_date="2023-10-31")

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional["Experiment"]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentModelModel.get_by_parameters(
                experiment_id=experiment.id,
                model_id=self.id
            )
            if not existing_association:
                logger.info(f"Model {self.model_name} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentModelModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to disassociate model {self.model_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error disassociating experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this model is associated with a specific experiment.

        Examples:
            >>> model = Model.get("example_model")
            >>> is_associated = model.belongs_to_experiment("example_experiment")
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
            association_exists = ExperimentModelModel.exists(
                experiment_id=experiment.id,
                model_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking experiment membership: {e}")
            return False
        
    def get_associated_datasets(self) -> Optional[List["Dataset"]]:
        """
        Get all datasets associated with this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> datasets = model.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name="example_dataset", collection_date="2023-10-01", dataset_type=Model, id=UUID('...'))
            Dataset(dataset_name="another_dataset", collection_date="2023-11-01", dataset_type=Model, id=UUID('...'))

        Returns:
            Optional[List["Dataset"]]: A list of associated datasets, or None if not found.
        """
        try:
            from gemini.api.dataset import Dataset
            current_id = self.id
            model_datasets = ModelDatasetsViewModel.search(model_id=current_id)
            if not model_datasets or len(model_datasets) == 0:
                logger.info(f"No datasets associated with model {self.model_name}.")
                return None
            datasets = [Dataset.model_validate(model_dataset) for model_dataset in model_datasets]
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
        Create and associate a new dataset with this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> dataset = model.create_new_dataset("example_dataset", {"key": "value"})
            >>> print(dataset)
            Dataset(dataset_name="example_dataset", collection_date="2023-10-01", dataset_type=Model, id=UUID('...'))

        Args:
            dataset_name (str): The name of the new dataset.
            dataset_info (dict, optional): Additional information about the dataset. Defaults to {{}}.
            collection_date (date, optional): The collection date. Defaults to today.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional["Dataset"]: The created and associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.create(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                collection_date=collection_date,
                experiment_name=experiment_name,
                dataset_type=GEMINIDatasetType.Model
            )
            if not dataset:
                logger.info(f"Failed to create dataset for model {self.model_name}.")
                return None
            dataset = self.associate_dataset(dataset_name=dataset_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            return None
        
    def associate_dataset(self, dataset_name: str) -> Optional["Dataset"]:
        """
        Associate this model with a dataset.

        Examples:
            >>> model = Model.get("example_model")
            >>> dataset = model.associate_dataset("example_dataset")
            >>> print(dataset)
            Dataset(dataset_name="example_dataset", collection_date="2023-10-01", dataset_type=Model, id=UUID('...'))

        Args:
            dataset_name (str): The name of the dataset to associate.
        Returns:
            Optional["Dataset"]: The associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name=dataset_name)
            if not dataset:
                logger.warning(f"Dataset {dataset_name} does not exist.")
                return None
            existing_association = ModelDatasetModel.exists(
                dataset_id=dataset.id,
                model_id=self.id
            )
            if existing_association:
                logger.info(f"Model {self.model_name} is already associated with dataset {dataset_name}.")
                return dataset
            new_association = ModelDatasetModel.get_or_create(
                dataset_id=dataset.id,
                model_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate model {self.model_name} with dataset {dataset_name}.")
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
        model_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_file: str = None,
        record_info: dict = None,
    ) -> tuple[bool, List[str]]:
        """
        Insert a single model record for this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> success, record_ids = model.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date.today(),
            ...     model_data={"key": "value"},
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_file="path/to/record/file",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> print(success, record_ids)
            True [UUID('...')]

        Args:
            timestamp (datetime, optional): The timestamp for the record. Defaults to now.
            collection_date (date, optional): The collection date for the record. Defaults to today.
            model_data (dict, optional): The model data dictionary. Defaults to {}.
            dataset_name (str, optional): The dataset name. Defaults to None.
            experiment_name (str, optional): The experiment name. Defaults to None.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
            record_file (str, optional): The record file path. Defaults to None.
            record_info (dict, optional): Additional record information dictionary. Defaults to {}.
        Returns:
            Optional[ModelRecord]: The inserted model record, or None if an error occurred.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("At least one of experiment_name, season_name, or site_name must be provided.")
            
            if not model_data and not record_file:
                raise ValueError("Either model_data or record_file must be provided.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            if not dataset_name:
                dataset_name = f"{self.model_name} Dataset {collection_date}"
            model_name = self.model_name
            model_record = ModelRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                model_name=model_name,
                model_data=model_data,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_file=record_file,
                record_info=record_info,
                insert_on_create=False
            )
            success, inserted_record_ids = ModelRecord.insert([model_record])
            if not success:
                raise Exception("Failed to insert model record.")
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting model record: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        model_data: List[dict] = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_files: List[str] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Insert multiple model records for this model.

        Examples:
            >>> model = Model.get("example_model")
            >>> timestamps = [datetime.now(), datetime.now()]
            >>> model_data = [{"key1": "value1"}, {"key2": "value2"}]
            >>> success, record_ids = model.insert_records(
            ...     timestamps=timestamps,
            ...     collection_date=date.today(),
            ...     model_data=model_data,
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_files=["path/to/record1", "path/to/record2"],
            ...     record_info=[{"info_key1": "info_value1"}, {"info_key2": "info_value2"}]
            ... )
            >>> print(success, record_ids)
            True [UUID('...'), UUID('...')]

        Args:
            timestamps (List[datetime]): List of timestamps for the records.
            collection_date (date, optional): The collection date for the records. Defaults to None.
            model_data (List[dict], optional): List of model data dictionaries. Defaults to [].
            dataset_name (str, optional): The dataset name. Defaults to None.
            experiment_name (str, optional): The experiment name. Defaults to None.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
            record_files (List[str], optional): List of record file paths. Defaults to [].
            record_info (List[dict], optional): List of additional record information dictionaries. Defaults to [].
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name and not season_name and not site_name:
                raise ValueError("At least one of experiment_name, season_name, or site_name must be provided.")
            
            if len(timestamps) == 0:
                raise ValueError("At least one timestamp must be provided.")
            
            if len(model_data) != len(timestamps):
                raise ValueError("model_data must have the same length as timestamps.")
            
            if record_files and len(record_files) != len(timestamps):
                raise ValueError("record_files must have the same length as timestamps.")
            
            collection_date = collection_date if collection_date else timestamps[0].date()
            
            if not dataset_name:
                dataset_name = f"{self.model_name} Dataset {collection_date}"
            
            model_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Model " + self.model_name):
                model_record = ModelRecord.create(
                    timestamp = timestamps[i],
                    collection_date = collection_date,
                    model_name= self.model_name,
                    model_data = model_data[i]  if model_data else {},
                    dataset_name = dataset_name,
                    experiment_name = experiment_name,
                    season_name = season_name,
                    site_name = site_name,
                    record_file= record_files[i] if record_files else None,
                    record_info = record_info[i] if record_info else {},
                    insert_on_create=False
                )
                model_records.append(model_record)

            success, inserted_record_ids = ModelRecord.insert(model_records)
            if not success:
                logger.info("Failed to insert model records.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting model records: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        record_info: dict = None
    ) -> List[ModelRecord]:
        """
        Search for model records associated with this model based on search parameters.

        Examples:
            >>> model = Model.get("example_model")
            >>> records = model.search_records(
            ...     collection_date=date.today(),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            ModelRecord(id=UUID(...), model_name='example_model', dataset_name='example_dataset', timestamp='2023-10-01T12:00:00', model_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            collection_date (date, optional): The collection date to filter by. Defaults to None.
            dataset_name (str, optional): The dataset name to filter by. Defaults to None.
            experiment_name (str, optional): The experiment name to filter by. Defaults to None.
            season_name (str, optional): The season name to filter by. Defaults to None.
            site_name (str, optional): The site name to filter by. Defaults to None.
            record_info (dict, optional): Additional record information to filter by. Defaults to None.
        Returns:
            Optional[List[ModelRecord]]: List of matching model records, or None if not found.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = ModelRecord.search(
                collection_date=collection_date,
                dataset_name=dataset_name,
                model_name=self.model_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching model records: {e}")
            return []
        
    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> List[ModelRecord]:
        """
        Filter model records associated with this model using a custom filter function.

        Examples:
            >>> model = Model.get("example_model")
            >>> records = model.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     dataset_names=["example_dataset"],
            ...     experiment_names=["example_experiment"],
            ...     season_names=["example_season"],
            ...     site_names=["example_site"]
            ... )
            >>> for record in records:
            ...     print(record)
            ModelRecord(id=UUID(...), model_name='example_model', dataset_name='example_dataset', timestamp='2023-10-01T12:00:00, model_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            
        Args:
            start_timestamp (Optional[datetime], optional): The start timestamp for filtering. Defaults to None.
            end_timestamp (Optional[datetime], optional): The end timestamp for filtering. Defaults to None
            dataset_names (Optional[List[str]], optional): List of dataset names to filter by. Defaults to None.
            experiment_names (Optional[List[str]], optional): List of experiment names to filter by. Defaults
            season_names (Optional[List[str]], optional): List of season names to filter by. Defaults to None.
            site_names (Optional[List[str]], optional): List of site names to filter by. Defaults to None.
        Returns:
            Optional[List[ModelRecord]]: List of filtered model records, or None if not found.
        """
        try:
            records = ModelRecord.filter(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                model_names=[self.model_name],
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering model records: {e}")
            return []

