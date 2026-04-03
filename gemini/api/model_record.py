"""
This module defines the ModelRecord class, which represents a record of a model, including metadata, associations to datasets and experiments, and file handling capabilities.

It includes methods for creating, retrieving, updating, and deleting model records, as well as methods for checking existence, searching, and managing file handling for records.

This module includes the following methods:

- `exists`: Check if a model record with the given parameters exists.
- `create`: Create a new model record.
- `get_by_id`: Retrieve a model record by its ID.
- `get_all`: Retrieve all model records.
- `search`: Search for model records based on various criteria.
- `update`: Update the details of a model record.
- `delete`: Delete a model record.
- `refresh`: Refresh the model record's data from the database.
- `get_info`: Get the additional information of the model record.
- `set_info`: Set the additional information of the model record.
- File handling methods from FileHandlerMixin for managing record files.

"""

from typing import Optional, List, Generator
import os, mimetypes
from uuid import UUID
from tqdm import tqdm

import logging
from gemini.api.types import ID
from pydantic import Field, AliasChoices
from gemini.api.base import APIBase, FileHandlerMixin
from gemini.db.models.columnar.model_records import ModelRecordModel
from gemini.db.models.views.model_records_immv import ModelRecordsIMMVModel

from datetime import date, datetime

logger = logging.getLogger(__name__)

class ModelRecord(APIBase, FileHandlerMixin):
    """
    Represents a record of a model, including metadata, associations to datasets and experiments, and file handling capabilities.

    Attributes:
        id (Optional[ID]): The unique identifier of the model record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        model_id (Optional[ID]): The ID of the associated model.
        model_name (Optional[str]): The name of the associated model.
        model_data (Optional[dict]): The data content of the model record.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        experiment_name : Optional[str] = None
        season_id: Optional[ID] = None
        season_name: Optional[str] = None
        site_id: Optional[ID] = None
        site_name: Optional[str] = None
        record_file: Optional[str] = None
        record_info: Optional[dict] = None

    """
    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "model_record_id"))

    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    model_id: Optional[ID] = None
    model_name: Optional[str] = None
    model_data: Optional[dict] = None
    experiment_id: Optional[ID] = None
    experiment_name : Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the ModelRecord object."""
        return f"ModelRecord(id={self.id}, timestamp={self.timestamp}, model_data={self.model_data}, model_name={self.model_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    def __repr__(self):
        """Return a detailed string representation of the ModelRecord object."""
        return f"ModelRecord(id={self.id}, timestamp={self.timestamp}, model_data={self.model_data}, model_name={self.model_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        model_name: str,
        dataset_name: str,
        experiment_name: str,
        season_name: str,
        site_name: str
    ) -> bool:
        """
        Check if a model record with the given parameters exists.

        Examples:
            >>> ModelRecord.exists(
            ...     timestamp=datetime.now(),
            ...     model_name="example_model",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site"
            ... )
            True
        
        Args:
            timestamp (datetime): The timestamp of the model record.
            model_name (str): The name of the model.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.

        Returns:
            bool: True if the model record exists, False otherwise.
        """
        try:
            exists = ModelRecordModel.exists(
                timestamp=timestamp,
                model_name=model_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of ModelRecord: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        model_name: str = None,
        model_data: dict = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        record_file: str = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["ModelRecord"]:
        """
        Create a new model record.

        Examples:
            >>> model_record = ModelRecord.create(
            ...     timestamp=datetime.now(),
            ...     collection_date=date.today(),
            ...     dataset_name="example_dataset",
            ...     model_name="example_model",
            ...     model_data={"key": "value"},
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="path/to/record_file.txt",
            ...     record_info={"info_key": "info_value"},
            ...     insert_on_create=True
            ... )
            >>> print(model_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Args:
            timestamp (datetime): The timestamp of the model record. Defaults to the current time.
            collection_date (date): The collection date of the model record. Defaults to the timestamp's date.
            dataset_name (str): The name of the associated dataset. Required.
            model_name (str): The name of the associated model. Required.
            model_data (dict): The data content of the model record. Defaults to an empty dictionary
            experiment_name (str): The name of the associated experiment. Optional.
            site_name (str): The name of the associated site. Optional.
            season_name (str): The name of the associated season. Optional.
            record_file (str): The file path of the model record. Optional.
            record_info (dict): Additional information about the model record. Defaults to an empty dictionary.
            insert_on_create (bool): Whether to insert the record into the database upon creation. Defaults to True.

        Returns:
            Optional["ModelRecord"]: The created model record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, site_name, season_name]):
                raise ValueError("At least one of experiment_name, site_name, or season_name must be provided.")
            if not model_name:
                raise ValueError("Model name is required.")
            if not dataset_name:
                raise ValueError("Dataset name is required.")
            if not timestamp:
                raise ValueError("Timestamp is required.")
            if not collection_date:
                collection_date = timestamp.date()
            if not model_data and not record_file:
                raise ValueError("At least one of model_data or record_file must be provided.")
            model_record = ModelRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                model_name=model_name,
                model_data=model_data,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                record_file=record_file,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([model_record])
                if not insert_success:
                    logger.info(f"Failed to insert ModelRecord: {model_record}")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info(f"No new ModelRecord was inserted.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                model_record = cls.get_by_id(inserted_record_id)
            return model_record
        except Exception as e:
            logger.error(f"Error creating ModelRecord: {e}")
            raise None
        
    @classmethod
    def insert(cls, records: List["ModelRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of model records into the database.

        Args:
            records (List[ModelRecord]): List of model records to insert.
    

        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not records or len(records) == 0:
                logger.info(f"No records provided for insertion.")
                return False, []
            records = [cls.process_record(record) for record in tqdm(records, desc="Processing ModelRecords")]
            records_to_insert = []
            for record in records:
                record_dict = record.model_dump()
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                records_to_insert.append(record_dict)
            logger.info(f"Inserting {len(records_to_insert)} records.")
            inserted_record_ids = ModelRecordModel.insert_bulk('model_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_record_ids)} records.")
            return True, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting ModelRecords: {e}")
            return False, []
        
    @classmethod
    def get(
        cls,
        timestamp: datetime,
        model_name: str,
        dataset_name: str,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> Optional["ModelRecord"]:
        """
        Retrieve model records based on provided parameters.

        Examples:
            >>> model_record = ModelRecord.get(
            ...     timestamp=datetime.now(),
            ...     model_name="example_model",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season"
            ...     site_name="example_site"
            ... )
            >>> print(model_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Args:
            timestamp (datetime): The timestamp of the model record.
            model_name (str): The name of the model.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment. Optional.
            season_name (str): The name of the season. Optional.
            site_name (str): The name of the site. Optional.


        Returns:
            Optional[List["ModelRecord"]]: List of matching model records, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning(f"Timestamp is required to get ModelRecord.")
                return None
            if not dataset_name:
                logger.warning(f"Dataset name is required to get ModelRecord.")
                return None
            if not model_name:
                logger.warning(f"Model name is required to get ModelRecord.")
                return None
            if not experiment_name and not season_name and not site_name:
                logger.warning(f"At least one of experiment_name, season_name, or site_name is required to get ModelRecord.")
                return None
            model_record = ModelRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                model_name=model_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not model_record:
                logger.info(f"No ModelRecord found for the given parameters.")
                return None
            model_record = cls.model_validate(model_record)
            return model_record
        except Exception as e:
            logger.error(f"Error getting ModelRecord: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ModelRecord"]:
        """
        Retrieve a model record by its ID

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> print(model_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)
            
        Args:
            id (UUID | int | str): The unique identifier of the model record.

        Returns:
            Optional["ModelRecord"]: The model record, or None if not found.
        """
        try:
            db_instance = ModelRecordModel.get(id)
            if not db_instance:
                logger.info(f"No ModelRecord found with ID: {id}")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting ModelRecord by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["ModelRecord"]]:
        """
        Retrieve all model records, up to a specified limit.

        Examples:
            >>> model_records = ModelRecord.get_all(limit=10)
            >>> for record in model_records:
            ...     print(record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)
            ModelRecord(id=UUID(...), timestamp=2023-10-02 12:00:00, model_name=example_model2, model_data={...}, dataset_name=example_dataset2, experiment_name=example_experiment2, site_name=example_site2, season_name=example_season2)

        Args:
            limit (int): The maximum number of model records to retrieve. Defaults to 100.

        Returns:
            Optional[List["ModelRecord"]]: List of model records, or None if not found.
        """
        try:
            records = ModelRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info(f"No ModelRecords found.")
                return None
            records = [cls.model_validate(record) for record in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all ModelRecords: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        model_name: str = None,
        model_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        collection_date: date = None,
        record_info: dict = None
    ) -> Generator["ModelRecord", None, None]:
        """
        Search for model records based on various criteria.

        Examples:
            >>> for record in ModelRecord.search(
            ...     model_name="example_model",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     collection_date=date.today(),
            ...     record_info={"info_key": "info_value"}
            ... ):
            ...     print(record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Args:
            model_name (str): The name of the model. Optional.
            model_data (dict): The data content of the model record. Optional.
            dataset_name (str): The name of the associated dataset. Optional.
            experiment_name (str): The name of the associated experiment. Optional.
            site_name (str): The name of the associated site. Optional.
            season_name (str): The name of the associated season. Optional.
            collection_date (date): The collection date of the model record. Optional.
            record_info (dict): Additional information about the model record. Optional.


        Returns:
            Optional[List["ModelRecord"]]: List of matching model records, or None if not found.
        """
        try:
            if not any([model_name, dataset_name, experiment_name, site_name, season_name, collection_date, record_info]):
                logger.warning(f"At least one parameter must be provided for search.")
                return
            records = ModelRecordsIMMVModel.stream(
                model_name=model_name,
                model_data=model_data,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                collection_date=collection_date,
                record_info=record_info
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error searching ModelRecords: {e}")
            yield None

    @classmethod
    def filter(
        cls,
        model_names: List[str] = None,
        dataset_names: List[str] = None,
        start_timestamp: datetime = None,
        end_timestamp: datetime = None,
        experiment_names: List[str] = None,
        site_names: List[str] = None,
        season_names: List[str] = None
    ) -> Generator["ModelRecord", None, None]:
        """
        Filter model records based on custom logic.

        Examples:
            >>> for record in ModelRecord.filter(
            ...     model_names=["example_model"],
            ...     dataset_names=["example_dataset"],
            ...     start_timestamp=datetime(2023, 1, 1),
            ...     end_timestamp=datetime(2023, 12, 31),
            ...     experiment_names=["example_experiment"],
            ...     site_names=["example_site"],
            ...     season_names=["example_season"]
            ... ):
            ...     print(record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Args:
            model_names (List[str]): List of model names to filter by. Optional.
            dataset_names (List[str]): List of dataset names to filter by. Optional.
            start_timestamp (datetime): Start timestamp for filtering. Optional.
            end_timestamp (datetime): End timestamp for filtering. Optional.
            experiment_names (List[str]): List of experiment names to filter by. Optional.
            site_names (List[str]): List of site names to filter by. Optional.
            season_names (List[str]): List of season names to filter by. Optional.

        Returns:
            Optional[List["ModelRecord"]]: List of filtered model records, or None if not found.
        """
        try:
            if not any([model_names, dataset_names, start_timestamp, end_timestamp, experiment_names, site_names, season_names]):
                logger.warning(f"At least one parameter must be provided for filter.")
                return
            records = ModelRecordModel.filter_records(
                model_names=model_names,
                dataset_names=dataset_names,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                experiment_names=experiment_names,
                site_names=site_names,
                season_names=season_names
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error filtering ModelRecords: {e}")
            yield None

    def update(
        self,
        model_data: dict = None,
        record_info: dict = None
    ) -> Optional["ModelRecord"]:
        """
        Update the details of the model record.

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> updated_record = model_record.update(
            ...     model_data={"new_key": "new_value"},
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Returns:
            Optional["ModelRecord"]: The updated model record, or None if an error occurred.
        """
        try:
            if not any([model_data, record_info]):
                logger.warning(f"At least one parameter must be provided for update.")
                return None
            current_id = self.id
            model_record = ModelRecordModel.get(current_id)
            if not model_record:
                logger.info(f"No ModelRecord found with ID: {current_id}")
                return None
            model_record = ModelRecordModel.update(
                model_record,
                model_data=model_data,
                record_info=record_info
            )
            model_record = self.model_validate(model_record)
            self.refresh()
            return model_record
        except Exception as e:
            logger.error(f"Error updating ModelRecord: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the model record.

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> deleted = model_record.delete()
            >>> print(deleted)
            True

        Returns:
            bool: True if the model record was deleted, False otherwise.
        """
        try:
            current_id = self.id
            model_record = ModelRecordModel.get(current_id)
            if not model_record:
                logger.info(f"No ModelRecord found with ID: {current_id}")
                return False
            ModelRecordModel.delete(model_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting ModelRecord: {e}")
            return False
        
    def refresh(self) -> Optional["ModelRecord"]:
        """
        Refresh the model record's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> refreshed_record = model_record.refresh()
            >>> print(refreshed_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)

        Returns:
            Optional["ModelRecord"]: The refreshed model record, or None if an error occurred.
        """
        try:
            db_instance = ModelRecordModel.get(self.id)
            if not db_instance:
                logger.info(f"No ModelRecord found with ID: {self.id}")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing ModelRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the model record.

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> record_info = model_record.get_info()
            >>> print(record_info)
            {'info_key': 'info_value'}

        Returns:
            Optional[dict]: The model record's info, or None if not found.
        """
        try:
            current_id = self.id
            model_record = ModelRecordModel.get(current_id)
            if not model_record:
                logger.info(f"No ModelRecord found with ID: {current_id}")
                return None
            record_info = model_record.record_info
            if not record_info:
                logger.info(f"No record info found for ModelRecord with ID: {current_id}")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting record info: {e}")
            return None
        
    def set_info(self, record_info: dict) -> Optional["ModelRecord"]:
        """
        Set the additional information of the model record.

        Examples:
            >>> model_record = ModelRecord.get_by_id(UUID('...'))
            >>> record_info = model_record.get_info()
            >>> print(record_info)
            {'info_key': 'info_value'}

        Returns:
            Optional["ModelRecord"]: The updated model record, or None if an error occurred.
        """
        try:
            current_id = self.id
            model_record = ModelRecordModel.get(current_id)
            if not model_record:
                logger.info(f"No ModelRecord found with ID: {current_id}")
                return None
            ModelRecordModel.update(
                model_record,
                record_info=record_info
            )
            model_record = self.model_validate(model_record)
            self.refresh()
            return model_record
        except Exception as e:
            logger.error(f"Error setting record info: {e}")
            return None
        
    @classmethod
    def create_file_uri(cls, record: "ModelRecord") -> Optional[str]:
        """
        Create a file URI for the given model record.

        Examples:
            >>> record = ModelRecord(
            ...     timestamp=datetime.now(),
            ...     collection_date=date.today(),
            ...     dataset_name="example_dataset",
            ...     model_name="example_model",
            ...     model_data={"key": "value"},
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="path/to/record_file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> file_uri = ModelRecord.create_file_uri(record)
            >>> print(file_uri)
            model_data/example_experiment/example_model/example_dataset/2023-10-01/example_site/example_season/1700000000000.txt

        Returns:
            Optional[str]: The file URI, or None if creation failed.
        """
        try:
            original_file_path = record.record_file
            if not original_file_path:
                logger.warning(f"record_file is required to create file URI.")
                return None
            if not os.path.exists(original_file_path):
                logger.warning(f"File {original_file_path} does not exist.")
                return None
            collection_date = record.collection_date.strftime("%Y-%m-%d")
            model_name = record.model_name
            dataset_name = record.dataset_name
            experiment_name = record.experiment_name
            season_name = record.season_name
            site_name = record.site_name
            file_extension = os.path.splitext(original_file_path)[1]
            file_timestamp = str(int(record.timestamp.timestamp() * 1000))
            file_key = f"model_data/{experiment_name}/{model_name}/{dataset_name}/{collection_date}/{site_name}/{season_name}/{file_timestamp}{file_extension}"
            return file_key
        except Exception as e:
            logger.error(f"Error creating file URI: {e}")
            return None


    @classmethod
    def process_record(cls, record: "ModelRecord") -> "ModelRecord":
        """
        Process a model record (custom logic).

        This method handles the file upload to the storage provider and updates the record's file URI.

        Examples:
            >>> record = ModelRecord(
            ...     timestamp=datetime.now(),
            ...     collection_date=date.today(),
            ...     dataset_name="example_dataset",
            ...     model_name="example_model",
            ...     model_data={"key": "value"},
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="path/to/record_file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> processed_record = ModelRecord.process_record(record)
            >>> print(processed_record)
            ModelRecord(id=UUID(...), timestamp=2023-10-01 12:00:00, model_name=example_model, model_data={...}, dataset_name=example_dataset, experiment_name=example_experiment, site_name=example_site, season_name=example_season)
        Args:
            record (ModelRecord): The model record to process.

        Returns:
            ModelRecord: The processed model record.
        """
        try:
            file = record.record_file
            if not file:
                logger.warning(f"record_file is required to process ModelRecord.")
                return record
            file_key = cls.create_file_uri(record)
            if not file_key:
                logger.info(f"Failed to create file URI for ModelRecord: {record}")
                return record
            content_type, _ = mimetypes.guess_type(file)
            # Generate Metadata for upload
            file_metadata = {
                "Model-Name": record.model_name,
                "Dataset-Name": record.dataset_name,
                "Experiment-Name": record.experiment_name,
                "Site-Name": record.site_name,
                "Season-Name": record.season_name,
                "Collection-Date": record.collection_date.isoformat() if record.collection_date else None,
                "Timestamp": record.timestamp.isoformat() if record.timestamp else None,
            }
            cls.minio_storage_provider.upload_file(
                object_name=file_key,
                input_file_path=file,
                bucket_name="gemini",
                content_type=content_type,
                metadata=file_metadata
            )
            record.record_file = file_key
            return record
        except Exception as e:
            logger.error(f"Error processing ModelRecord: {e}")
            return record

