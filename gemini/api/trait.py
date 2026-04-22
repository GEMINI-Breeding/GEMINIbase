"""
This module defines the Trait class, which represents a trait entity, including its metadata, associations to experiments, datasets, and records, and related operations.

It includes methods for creating, retrieving, updating, and deleting traits, as well as methods for checking existence, searching, and managing associations with related entities and records.

This module includes the following methods:

- `exists`: Check if a trait with the given name exists.
- `create`: Create a new trait.
- `get`: Retrieve a trait by its name and experiment.
- `get_by_id`: Retrieve a trait by its ID.
- `get_all`: Retrieve all traits.
- `search`: Search for traits based on various criteria.
- `update`: Update the details of a trait.
- `delete`: Delete a trait.
- `refresh`: Refresh the trait's data from the database.
- `get_info`: Get the additional information of the trait.
- `set_info`: Set the additional information of the trait.
- Association methods for experiments, datasets, and records.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from tqdm import tqdm

from pydantic import Field, AliasChoices
from sqlalchemy.exc import DBAPIError
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.dataset import Dataset
from gemini.api.trait_record import TraitRecord
from gemini.api.enums import GEMINITraitLevel, GEMINIDatasetType
from gemini.db.models.traits import TraitModel
from gemini.db.models.columnar.trait_records import TraitRecordModel
from gemini.db.models.views.experiment_views import ExperimentTraitsViewModel
from gemini.db.models.views.dataset_views import TraitDatasetsViewModel
from gemini.db.models.associations import ExperimentTraitModel, TraitDatasetModel
from datetime import date, datetime

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.dataset import Dataset

logger = logging.getLogger(__name__)

class Trait(APIBase):
    """
    Represents a trait entity, including its metadata, associations to experiments, datasets, and records, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the trait.
        trait_name (str): The name of the trait.
        trait_units (str): The units of the trait.
        trait_level_id (Optional[int]): The ID of the trait level.
        trait_info (Optional[dict]): Additional information about the trait.
        trait_metrics (Optional[dict]): Metrics associated with the trait.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "trait_id"))

    trait_name: str
    trait_units: str
    trait_level_id: Optional[int] = None
    trait_info: Optional[dict] = None
    trait_metrics: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Trait object."""
        return f"Trait(trait_name={self.trait_name}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Trait object."""
        return f"Trait(trait_name={self.trait_name}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        trait_name: str
    ) -> bool:
        """
        Check if a trait with the given name exists.

        Examples:
            >>> Trait.exists("Leaf Area Index")
            True

            >>> Trait.exists("Nonexistent Trait")
            False

        Args:
            trait_name (str): The name of the trait.
        Returns:
            bool: True if the trait exists, False otherwise.
        """
        try:
            exists = TraitModel.exists(trait_name=trait_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of trait: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        trait_name: str,
        trait_units: str = None,
        trait_level: GEMINITraitLevel = GEMINITraitLevel.Plot,
        trait_info: dict = None,
        trait_metrics: dict = None,
        experiment_name: str = None
    ) -> Optional["Trait"]:
        """
        Create a new trait and associate it with an experiment if provided.

        Examples:
            >>> Trait.create("Leaf Area Index", "cm^2", GEMINITraitLevel.Plot, {"description": "Leaf area index"}, {"mean": 5.0}, "Experiment 1")
            Trait(trait_name=Leaf Area Index, id=UUID(...))

        Args:
            trait_name (str): The name of the trait.
            trait_units (str, optional): The units of the trait. Defaults to None.
            trait_level (GEMINITraitLevel, optional): The level of the trait. Defaults to Plot.
            trait_info (dict, optional): Additional information. Defaults to {{}}.
            trait_metrics (dict, optional): Metrics associated with the trait. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[Trait]: The created trait, or None if an error occurred.
        """
        try:
            trait_level_id = trait_level.value if isinstance(trait_level, GEMINITraitLevel) else trait_level
            trait = TraitModel.get_or_create(
                trait_name=trait_name,
                trait_units=trait_units,
                trait_level_id=trait_level_id,
                trait_metrics=trait_metrics,
                trait_info=trait_info,
            )
            trait = cls.model_validate(trait)
            if experiment_name:
                trait.associate_experiment(experiment_name)
            return trait
        except Exception as e:
            logger.error(f"Error creating trait: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        trait_name: str,
        experiment_name: str = None
    ) -> Optional["Trait"]:
        """
        Retrieve a trait by its name and experiment.

        Examples:
            >>> Trait.get("Leaf Area Index", "Experiment 1")
            Trait(trait_name=Leaf Area Index, id=UUID(...))

        Args:
            trait_name (str): The name of the trait.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Trait]: The trait, or None if not found.
        """
        try:
            trait = ExperimentTraitsViewModel.get_by_parameters(
                trait_name=trait_name,
                experiment_name=experiment_name   
            )
            if not trait:
                logger.debug(f"Trait with name {trait_name} not found.")
                return None
            trait = cls.model_validate(trait)
            return trait
        except Exception as e:
            logger.error(f"Error getting trait: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Trait"]:
        """
        Retrieve a trait by its ID.

        Examples:
            >>> Trait.get_by_id(UUID('...'))
            Trait(trait_name=Leaf Area Index, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the trait.
        Returns:
            Optional[Trait]: The trait, or None if not found.
        """
        try:
            trait = TraitModel.get(id)
            if not trait:
                logger.warning(f"Trait with ID {id} does not exist.")
                return None
            trait = cls.model_validate(trait)
            return trait
        except Exception as e:
            logger.error(f"Error getting trait by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Trait"]]:
        """
        Retrieve all traits.

        Examples:
            >>> Trait.get_all()
            [Trait(trait_name=Leaf Area Index, id=UUID(...)), Trait(trait_name=Plant Height, id=UUID(...))]

        Returns:
            Optional[List[Trait]]: List of all traits, or None if not found.
        """
        try:
            traits = TraitModel.all(limit=limit, offset=offset)
            if not traits or len(traits) == 0:
                logger.info("No traits found.")
                return None
            traits = [cls.model_validate(trait) for trait in traits]
            return traits
        except Exception as e:
            logger.error(f"Error getting all traits: {e}")
            return None
        
    @classmethod
    def search(
        cls, 
        trait_name: str = None,
        trait_units: str = None,
        trait_level: GEMINITraitLevel = None,
        trait_info: dict = None,
        trait_metrics: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Trait"]]:
        """
        Search for traits based on various criteria.

        Examples:
            >>> Trait.search(trait_name="Leaf Area Index")
            [Trait(trait_name=Leaf Area Index, id=UUID(...))]

        Args:
            trait_name (str, optional): The name of the trait. Defaults to None.
            trait_units (str, optional): The units of the trait. Defaults to None.
            trait_level (GEMINITraitLevel, optional): The level of the trait. Defaults to None.
            trait_info (dict, optional): Additional information. Defaults to None.
            trait_metrics (dict, optional): Metrics associated with the trait. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List[Trait]]: List of matching traits, or None if not found.
        """
        try:
            if not any([experiment_name, trait_name, trait_units, trait_level, trait_info, trait_metrics]):
                logger.warning("At least one search parameter must be provided.")
                return None
            
            traits = ExperimentTraitsViewModel.search(
                experiment_name=experiment_name,
                trait_name=trait_name,
                trait_units=trait_units,
                trait_level_id=trait_level.value if trait_level else None,
                trait_info=trait_info,
                trait_metrics=trait_metrics
            )
            if not traits or len(traits) == 0:
                logger.info("No traits found with the provided search parameters.")
                return None
            traits = [cls.model_validate(trait) for trait in traits]
            return traits if traits else None
        except Exception as e:
            logger.error(f"Error searching traits: {e}")
            return None
            
    def update(
        self,
        trait_name: str = None, 
        trait_units: str = None,
        trait_level: GEMINITraitLevel = None,
        trait_info: dict = None,
        trait_metrics: dict = None,
    ) -> Optional["Trait"]:
        """
        Update the details of the trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> updated_trait = trait.update(trait_name="New Leaf Area Index", trait_units="m^2")
            >>> print(updated_trait)
            Trait(trait_name=New Leaf Area Index, id=UUID(...))

        Args:
            trait_name (str, optional): The new name. Defaults to None.
            trait_units (str, optional): The new units. Defaults to None.
            trait_level (GEMINITraitLevel, optional): The new level. Defaults to None.
            trait_info (dict, optional): The new information. Defaults to None.
            trait_metrics (dict, optional): The new metrics. Defaults to None.
        Returns:
            Optional[Trait]: The updated trait, or None if an error occurred.
        """
        try:
            if not any([trait_units, trait_level, trait_info, trait_metrics, trait_name]):
                logger.warning("At least one update parameter must be provided.")
                return None

            current_id = self.id
            trait = TraitModel.get(current_id)
            if not trait:
                logger.warning(f"Trait with ID {current_id} does not exist.")
                return None

            rename = trait_name is not None and trait_name != trait.trait_name

            trait = TraitModel.update(
                trait,
                trait_name=trait_name,
                trait_units=trait_units,
                trait_level_id=trait_level.value if trait_level else None,
                trait_info=trait_info,
                trait_metrics=trait_metrics
            )
            if rename:
                from gemini.api._rename_cascade import cascade_rename
                cascade_rename(current_id, "trait_id", "trait_name", trait_name)
            trait = self.model_validate(trait)
            self.refresh()
            return trait
        except Exception as e:
            logger.error(f"Error updating trait: {e}")
            return None
    
    def delete(self) -> bool:
        """
        Delete the trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> success = trait.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the trait was deleted, False otherwise.
        """
        try:
            current_id = self.id
            trait = TraitModel.get(current_id)
            if not trait:
                logger.warning(f"Trait with ID {current_id} does not exist.")
                return False
            TraitRecordModel.delete_by_trait(self.trait_name)
            TraitModel.delete(trait)
            return True
        except Exception as e:
            logger.error(f"Error deleting trait: {e}")
            return False
        
    def refresh(self) -> Optional["Trait"]:
        """
        Refresh the trait's data from the database.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> refreshed_trait = trait.refresh()
            >>> print(refreshed_trait)
            Trait(trait_name=Leaf Area Index, id=UUID(...))

        Returns:
            Optional[Trait]: The refreshed trait, or None if an error occurred.
        """
        try:
            db_instance = TraitModel.get(self.id)
            if not db_instance:
                logger.warning(f"Trait with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing trait: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> trait_info = trait.get_info()
            >>> print(trait_info)
            {'description': 'Leaf area index', 'source': 'Field measurements'}

        Returns:
            Optional[dict]: The trait's info, or None if not found.
        """
        try:
            current_id = self.id
            trait = TraitModel.get(current_id)
            if not trait:
                logger.warning(f"Trait with ID {current_id} does not exist.")
                return None
            trait_info = trait.trait_info
            if not trait_info:
                logger.info("Trait info is empty.")
                return None
            return trait_info
        except Exception as e:
            logger.error(f"Error getting trait info: {e}")
            return None
        
    def set_info(self, trait_info: dict) -> Optional["Trait"]:
        """
        Set the additional information of the trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> updated_trait = trait.set_info({"description": "Updated leaf area index", "source": "New measurements"})
            >>> print(updated_trait.get_info())
            {'description': 'Updated leaf area index', 'source': 'New measurements'}

        Args:
            trait_info (dict): The new information to set.
        Returns:
            Optional[Trait]: The updated trait, or None if an error occurred.
        """
        try:
            current_id = self.id
            trait = TraitModel.get(current_id)
            if not trait:
                logger.warning(f"Trait with ID {current_id} does not exist.")
                return None
            trait = TraitModel.update(
                trait,
                trait_info=trait_info
            )
            trait = self.model_validate(trait)
            self.refresh()
            return self
        except Exception as e:
            logger.error(f"Error setting trait info: {e}")
            return None
        
    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> experiments = trait.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))
            Experiment(experiment_name=Experiment 2, experiment_start_date=2023-02-01, experiment_end_date=2023-11-30, id=UUID(...))

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment_traits = ExperimentTraitsViewModel.search(trait_id=self.id)
            if not experiment_traits or len(experiment_traits) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiment_traits]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this trait with an experiment.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> experiment = trait.associate_experiment("Experiment 1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional[Experiment]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentTraitModel.get_by_parameters(
                experiment_id=experiment.id,
                trait_id=self.id
            )
            if existing_association:
                logger.info(f"Trait {self.trait_name} is already associated with experiment {experiment_name}.")
                return True
            new_association = ExperimentTraitModel.get_or_create(
                experiment_id=experiment.id,
                trait_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate trait {self.trait_name} with experiment {experiment_name}.")
                return False
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this trait from an experiment.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> experiment = trait.unassociate_experiment("Experiment 1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment 1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentTraitModel.get_by_parameters(
                experiment_id=experiment.id,
                trait_id=self.id
            )
            if not existing_association:
                logger.info(f"Trait {self.trait_name} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentTraitModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate trait {self.trait_name} from experiment {experiment_name}.")
                return False
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this trait is associated with a specific experiment.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> is_associated = trait.belongs_to_experiment("Experiment 1")
            >>> print(is_associated)
            True

        Args:
            experiment_name (str): The name of the experiment to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentTraitModel.exists(
                experiment_id=experiment.id,
                trait_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if trait belongs to experiment: {e}")
            return

    def get_associated_datasets(self) -> Optional[List["Dataset"]]:
        """
        Get all datasets associated with this trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> datasets = trait.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name=Leaf Area Index Dataset 2023-01-01, dataset_type=Trait, collection_date=2023-01-01, id=UUID(...))
            Dataset(dataset_name=Leaf Area Index Dataset 2023-02-01, dataset_type=Trait, collection_date=2023-02-01, id=UUID(...))

        Returns:
            Optional[List[Dataset]]: A list of associated datasets, or None if not found.
        """
        try:
            from gemini.api.dataset import Dataset
            datasets = TraitDatasetsViewModel.search(trait_id=self.id)
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
        Create and associate a new dataset with this trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> dataset = trait.create_new_dataset("Leaf Area Index Dataset 2023-01-01", {"description": "Dataset for leaf area index"}, date(2023, 1, 1), "Experiment 1")
            >>> print(dataset)
            Dataset(dataset_name=Leaf Area Index Dataset 2023-01-01, dataset_type=Trait, collection_date=2023-01-01, id=UUID(...))

        Args:
            dataset_name (str): The name of the new dataset.
            dataset_info (dict, optional): Additional information. Defaults to {{}}.
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
                dataset_type=GEMINIDatasetType.Trait,
                collection_date=collection_date,
                experiment_name=experiment_name
            )
            if not dataset:
                logger.info(f"Failed to create dataset {dataset_name}.")
                return None
            dataset = self.associate_dataset(dataset_name)
            return dataset
        except Exception as e:
            logger.error(f"Error creating new dataset: {e}")
            return None

    def associate_dataset(self, dataset_name: str) -> Optional["Dataset"]:
        """
        Associate this trait with a dataset.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> dataset = trait.associate_dataset("Leaf Area Index Dataset 2023-01-01")
            >>> print(dataset)
            Dataset(dataset_name=Leaf Area Index Dataset 2023-01-01, dataset_type=Trait, collection_date=2023-01-01, id=UUID(...))

        Args:
            dataset_name (str): The name of the dataset to associate.
        Returns:
            Optional[Dataset]: The associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name)
            if not dataset:
                logger.warning(f"Dataset {dataset_name} does not exist.")
                return None
            existing_association = TraitDatasetModel.get_by_parameters(
                trait_id=self.id,
                dataset_id=dataset.id
            )
            if existing_association:
                logger.info(f"Trait {self.trait_name} is already associated with dataset {dataset_name}.")
                return True
            new_association = TraitDatasetModel.get_or_create(
                trait_id=self.id,
                dataset_id=dataset.id
            )
            if not new_association:
                logger.info(f"Failed to associate trait {self.trait_name} with dataset {dataset_name}.")
                return False
            self.refresh()
            return dataset
        except Exception as e:
            logger.error(f"Error associating dataset: {e}")
            return None

    def insert_record(
        self,
        timestamp: date = None,
        collection_date: date = None,
        dataset_name: str = None,
        trait_value: float = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = -1,
        plot_row_number: int = -1,
        plot_column_number: int = -1,
        record_info: dict = None
    ) -> tuple[bool, List[str]]:
        """
        Insert a single trait record for this trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> success, record_ids = trait.insert_record(
            ...     timestamp=datetime.now(),
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="Leaf Area Index Dataset 2023-01-01",
            ...     trait_value=5.0,
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring 2023",
            ...     site_name="Field Site A",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_info={"description": "Leaf area index measurement"}
            ... )
            >>> print(success, record_ids)
            True [UUID(...)]

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            trait_value (float, optional): The value of the trait. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to -1.
            plot_row_number (int, optional): The plot row number. Defaults to -1.
            plot_column_number (int, optional): The plot column number. Defaults to -1.
            record_info (dict, optional): Additional info. Defaults to {{}}.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name or not season_name or not site_name:
                raise ValueError("Experiment name, season name, and site name must be provided.")
            
            if not trait_value:
                raise ValueError("Trait value must be provided.")
            
            timestamp = timestamp if timestamp else datetime.now()
            collection_date = collection_date if collection_date else timestamp.date()
            trait_name = self.trait_name
            if not dataset_name:
                dataset_name = f"{trait_name} Dataset {collection_date}"
            trait_record = TraitRecord.create(
                timestamp=timestamp,
                collection_date=collection_date,
                trait_name=trait_name,
                dataset_name=dataset_name,
                trait_value=trait_value,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number if plot_number != -1 else None,
                plot_row_number=plot_row_number if plot_row_number != -1 else None,
                plot_column_number=plot_column_number if plot_column_number != -1 else None,
                record_info=record_info if record_info else {},
                insert_on_create=False
            )
            success, inserted_record_ids = TraitRecord.insert([trait_record])
            if not success:
                logger.info(f"Failed to insert record for trait {trait_name}.")
                return False, []
            return success, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting record: {e}")
            return False, []
        
    def insert_records(
        self,
        timestamps: List[datetime] = None,
        collection_date: date = None,
        trait_values: List[float] = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_numbers: List[int] = None,
        plot_row_numbers: List[int] = None,
        plot_column_numbers: List[int] = None,
        record_info: List[dict] = None
    ) -> tuple[bool, List[str]]:
        """
        Insert multiple trait records for this trait.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> success, record_ids = trait.insert_records(
            ...     timestamps=[datetime.now(), datetime.now()],
            ...     collection_date=date(2023, 1, 1),
            ...     trait_values=[5.0, 6.0],
            ...     dataset_name="Leaf Area Index Dataset 2023-01-01",
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring 2023",
            ...     site_name="Field Site A",
            ...     plot_numbers=[1, 2],
            ...     plot_row_numbers=[1, 2],
            ...     plot_column_numbers=[1, 2],
            ...     record_info=[{"description": "Leaf area index measurement 1"}, {"description": "Leaf area index measurement 2"}]
            ... )
            >>> print(success, record_ids)
            True [UUID(...), UUID(...)]

        Args:
            timestamps (List[datetime], optional): List of timestamps. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            trait_values (List[float], optional): List of trait values. Defaults to [].
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_numbers (List[int], optional): List of plot numbers. Defaults to None.
            plot_row_numbers (List[int], optional): List of plot row numbers. Defaults to None.
            plot_column_numbers (List[int], optional): List of plot column numbers. Defaults to None.
            record_info (List[dict], optional): List of additional info. Defaults to [].
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not experiment_name or not season_name or not site_name:
                raise ValueError("Experiment name, season name, and site name must be provided.")
            
            if len(timestamps) == 0:
                raise ValueError("At least one timestamp must be provided.")
            
            if not dataset_name:
                dataset_name = f"{self.trait_name} Dataset {collection_date}"
            
            collection_date = collection_date if collection_date else timestamps[0].date()
            trait_records = []
            timestamps_length = len(timestamps)

            for i in tqdm(range(timestamps_length), desc="Arranging Records for Trait: " + self.trait_name):
                trait_record = TraitRecord.create(
                    timestamp=timestamps[i],
                    collection_date=collection_date,
                    trait_name=self.trait_name,
                    trait_value=trait_values[i] if trait_values else None,
                    dataset_name=dataset_name if dataset_name else f"{self.trait_name} Dataset {collection_date}",
                    experiment_name=experiment_name,
                    season_name=season_name,
                    site_name=site_name,
                    plot_number=plot_numbers[i] if plot_numbers else None,
                    plot_row_number=plot_row_numbers[i] if plot_row_numbers else None,
                    plot_column_number=plot_column_numbers[i] if plot_column_numbers else None,
                    record_info=record_info[i] if record_info else {},
                    insert_on_create=False
                )
                trait_records.append(trait_record)

            success, inserted_record_ids = TraitRecord.insert(trait_records)
            return success, inserted_record_ids
        except ValueError:
            raise
        except DBAPIError:
            # Let database errors (trigger RAISEs, constraint violations)
            # propagate so the REST layer can surface the real cause.
            raise
        except Exception as e:
            logger.error(f"Error inserting records: {e}")
            return False, []
        
    def search_records(
        self,
        collection_date: date = None,
        dataset_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        record_info: dict = None
    ) -> List[TraitRecord]:
        """
        Search for trait records associated with this trait based on search parameters.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> records = trait.search_records(
            ...     collection_date=date(2023, 1, 1),
            ...     dataset_name="Leaf Area Index Dataset 2023-01-01",
            ...     experiment_name="Experiment 1",
            ...     season_name="Spring 2023",
            ...     site_name="Field Site A",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_info={"description": "Leaf area index measurement"}
            ... )
            >>> for record in records:
            ...     print(record)
            TraitRecord(id=UUID(...), trait_name=Leaf Area Index, collection_date=2023-01-01, dataset_name=Leaf Area Index Dataset 2023-01-01, experiment_name=Experiment 1, season_name=Spring 2023, site_name=Field Site A, plot_number=1, plot_row_number=1, plot_column_number=1)
            TraitRecord(id=UUID(...), trait_name=Leaf Area Index, collection_date=2023-01-01, dataset_name=Leaf Area Index Dataset 2023-01-01, experiment_name=Experiment 1, season_name=Spring 2023, site_name=Field Site A, plot_number=2, plot_row_number=2, plot_column_number=2)

        Args:
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Returns:
            List[TraitRecord]: List of matching trait records, or empty list if not found.
        """
        try:
            record_info = record_info if record_info else {}
            record_info = {k: v for k, v in record_info.items() if v is not None}

            records = TraitRecord.search(
                trait_name=self.trait_name,
                collection_date=collection_date,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                record_info=record_info
            )
            return records
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            return []
        
    def filter_records(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> List[TraitRecord]:
        """
        Filter trait records associated with this trait using a custom filter function.

        Examples:
            >>> trait = Trait.get("Leaf Area Index")
            >>> records = trait.filter_records(
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     dataset_names=["Leaf Area Index Dataset 2023-01-01"],
            ...     experiment_names=["Experiment 1"],
            ...     season_names=["Spring 2023"],
            ...     site_names=["Field Site A"]
            ... )
            >>> for record in records:
            ...     print(record)
            TraitRecord(id=UUID(...), trait_name=Leaf Area Index, collection_date=2023-01-01, dataset_name=Leaf Area Index Dataset 2023-01-01, experiment_name=Experiment 1, season_name=Spring 2023, site_name=Field Site A, plot_number=1, plot_row_number=1, plot_column_number=1)
            TraitRecord(id=UUID(...), trait_name=Leaf Area Index, collection_date=2023-01-01, dataset_name=Leaf Area Index Dataset 2023-01-01, experiment_name=Experiment 1, season_name=Spring 2023, site_name=Field Site A, plot_number=2, plot_row_number=2, plot_column_number=2)

        Args:
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
        Returns:
            List[TraitRecord]: List of filtered trait records, or empty list if not found.
        """
        try:
            records = TraitRecord.filter(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                trait_names=[self.trait_name],
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return records
        except Exception as e:
            logger.error(f"Error filtering trait records: {e}")
            return []