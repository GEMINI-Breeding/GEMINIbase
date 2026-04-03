"""
This module defines the DatasetRecord class, which represents a record within a dataset, including metadata and associations to experiments, seasons, and sites.

It includes methods for creating, retrieving, updating, and deleting dataset records, as well as methods for checking existence, searching, and managing file handling for records.

This module includes the following methods:

- `exists`: Check if a dataset record with the given parameters exists.
- `create`: Create a new dataset record.
- `get_by_id`: Retrieve a dataset record by its ID.
- `get_all`: Retrieve all dataset records.
- `search`: Search for dataset records based on various criteria.
- `update`: Update the details of a dataset record.
- `delete`: Delete a dataset record.
- `refresh`: Refresh the dataset record's data from the database.
- `get_info`: Get the additional information of the dataset record.
- `set_info`: Set the additional information of the dataset record.
- File handling methods from FileHandlerMixin for managing record files.

"""

from typing import Optional, List, Generator
from uuid import UUID
import os, mimetypes
from tqdm import tqdm

import logging
from gemini.api.types import ID
from pydantic import Field, AliasChoices
from gemini.api.base import APIBase, FileHandlerMixin
from gemini.db.models.columnar.dataset_records import DatasetRecordModel
from gemini.db.models.views.dataset_records_immv import DatasetRecordsIMMVModel

from datetime import date, datetime

logger = logging.getLogger(__name__)

class DatasetRecord(APIBase, FileHandlerMixin):
    """
    Represents a record within a dataset, including metadata and associations to experiments, seasons, and sites.

    Attributes:
        id (Optional[ID]): The unique identifier of the dataset record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        dataset_data (Optional[dict]): The data content of the record.
        experiment_name (Optional[str]): The name of the associated experiment.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        season_name (Optional[str]): The name of the associated season.
        season_id (Optional[ID]): The ID of the associated season.
        site_name (Optional[str]): The name of the associated site.
        site_id (Optional[ID]): The ID of the associated site.
        record_file (Optional[str]): The file path for the record data.
        record_info (Optional[dict]): Additional information about the record.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "dataset_record_id"))

    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    dataset_data: Optional[dict] = None
    experiment_name: Optional[str] = None
    experiment_id: Optional[ID] = None
    season_name: Optional[str] = None
    season_id: Optional[ID] = None
    site_name: Optional[str] = None
    site_id: Optional[ID] = None
    record_file: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the DatasetRecord object."""
        return f"DatasetRecord(id={self.id}, timestamp={self.timestamp}, dataset_name={self.dataset_name}, dataset_data={self.dataset_data}, experiment_name={self.experiment_name}, season_name={self.season_name}, site_name={self.site_name})"
    
    def __repr__(self):
        """Return a detailed string representation of the DatasetRecord object."""
        return f"DatasetRecord(id={self.id}, timestamp={self.timestamp}, dataset_name={self.dataset_name}, dataset_data={self.dataset_data}, experiment_name={self.experiment_name}, season_name={self.season_name}, site_name={self.site_name})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        dataset_name: str,
        experiment_name: str,
        season_name: str,
        site_name: str,
    ) -> bool:
        """
        Check if a dataset record with the given parameters exists.

        Examples:
            >>> DatasetRecord.exists(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site"
            ... )
            True

        Args:
            timestamp (datetime): The timestamp of the record.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.
        Returns:
            bool: True if the dataset record exists, False otherwise.
        """
        try:
            exists = DatasetRecordModel.exists(
                timestamp=timestamp,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        dataset_data: dict = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        record_file: str = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["DatasetRecord"]:
        """
        Create a new dataset record.

        Examples:
            >>> record = DatasetRecord.create(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     dataset_data={"key": "value"},
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="/path/to/record/file.txt",
            ...     record_info={"info_key": "info_value"},
            ...     insert_on_create=True
            ... )
            >>> print(record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to now.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Required.
            dataset_data (dict, optional): The data content. Defaults to {{}}.
            experiment_name (str, optional): The experiment name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
            season_name (str, optional): The season name. Defaults to None.
            record_file (str, optional): The file path for the record data. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
            insert_on_create (bool, optional): Whether to insert on creation. Defaults to True.
        Returns:
            Optional["DatasetRecord"]: The created dataset record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, site_name, season_name]):
                raise ValueError("At least one of experiment_name, site_name, or season_name is required.")
            if not dataset_name:
                raise ValueError("dataset_name is required.")
            if not timestamp:
                raise ValueError("timestamp is required.")
            if not collection_date:
                collection_date = timestamp.date()
            if not dataset_data and not record_file:
                raise ValueError("Either dataset_data or record_file is required.")
            dataset_record = DatasetRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                dataset_data=dataset_data,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                record_file=record_file,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([dataset_record])
                if not insert_success:
                    logger.info(f"Failed to insert DatasetRecord: {dataset_record}")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info(f"No new DatasetRecord was inserted.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                dataset_record = cls.get_by_id(inserted_record_id)
            return dataset_record
        except Exception as e:
            logger.error(f"Error creating DatasetRecord: {e}")
            return None
    

    @classmethod
    def insert(cls, records: List["DatasetRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of dataset records into the database.

        Args:
            records (List[DatasetRecord]): The list of dataset records to insert.
        Returns:
            tuple[bool, List[str]]: A tuple containing a boolean indicating success and a list of inserted record IDs.
        """
        try:
            if not records or len(records) == 0:
                logger.info(f"No records provided to insert.")
                return False, []
            records = cls.verify_records(records)
            records = [cls.process_record(record) for record in tqdm(records, desc="Processing Records for Dataset: " + records[0].dataset_name)]
            records_to_insert = []
            for record in records:
                record_dict = record.model_dump()
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                records_to_insert.append(record_dict)
            logger.info(f"Inserting {len(records_to_insert)} records.")
            inserted_record_ids = DatasetRecordModel.insert_bulk('dataset_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_record_ids)} records.")
            return True, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting records: {e}")
            return False, []

    @classmethod
    def get(
        cls,
        timestamp: datetime,
        dataset_name: str,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
    ) -> Optional["DatasetRecord"]:
        """
        Retrieve a dataset record by its parameters.

        Examples:
            >>> record = DatasetRecord.get(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site"
            ... )
            >>> record
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            timestamp (datetime): The timestamp of the record.
            dataset_name (str): The name of the dataset.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Optional["DatasetRecord"]: The retrieved dataset record, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning(f"Timestamp is required to get the DatasetRecord.")
                return None
            if not dataset_name:
                logger.warning(f"Dataset name is required to get the DatasetRecord.")
                return None
            if not experiment_name and not season_name and not site_name:
                logger.warning(f"At least one of experiment_name, season_name, or site_name is required to get the DatasetRecord.")
                return None
            dataset_record = DatasetRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not dataset_record:
                logger.debug(f"DatasetRecord not found.")
                return None
            dataset_record = cls.model_validate(dataset_record)
            return dataset_record
        except Exception as e:
            logger.error(f"Error getting DatasetRecord: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["DatasetRecord"]:
        """
        Retrieve a dataset record by its ID.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> record
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            id (UUID | int | str): The ID of the dataset record.
        Returns:
            Optional["DatasetRecord"]: The retrieved dataset record, or None if not found.
        """
        try:
            db_instance = DatasetRecordModel.get(id)
            if not db_instance:
                logger.debug(f"DatasetRecord with id {id} not found.")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting DatasetRecord by id: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["DatasetRecord"]]:
        """
        Retrieve all dataset records.

        Examples:
            >>> records = DatasetRecord.get_all(limit=10)
            >>> for record in records:
            ...     print(record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), dataset_name='another_dataset', dataset_data={...}, experiment_name='another_experiment', season_name='another_season', site_name='another_site')

        Args:
            limit (int, optional): The maximum number of records to retrieve. Defaults to 100.
        Returns:
            Optional[List["DatasetRecord"]]: A list of dataset records, or None if an error occurred.
        """
        try:
            records = DatasetRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info(f"No DatasetRecords found.")
                return None
            records = [cls.model_validate(record) for record in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all DatasetRecords: {e}")
            return None


    @classmethod
    def search(
        cls,
        dataset_name: str = None,
        dataset_data: dict = None,
        experiment_name: str = None,    
        season_name: str = None,
        site_name: str = None,
        collection_date: date = None,
        record_info: dict = None,
    ) -> Generator["DatasetRecord", None, None]:
        """
        Search for dataset records based on various criteria.

        Examples:
            >>> records = DatasetRecord.search(
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     collection_date=date(2023, 10, 1),
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), dataset_name='another_dataset', dataset_data={...}, experiment_name='another_experiment', season_name='another_season', site_name='another_site')
            
        Args:
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            dataset_data (dict, optional): The data content. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Yields:
            Generator["DatasetRecord", None, None]: A generator of matching dataset records.
        """
        try:
            if not any([dataset_name, dataset_data, experiment_name, season_name, site_name, collection_date, record_info]):
                raise ValueError("At least one parameter must be provided.")
            records = DatasetRecordsIMMVModel.stream(
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                collection_date=collection_date,
                dataset_data=dataset_data,
                record_info=record_info
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error searching DatasetRecords: {e}")
            yield None

    @classmethod
    def filter(
        cls,
        dataset_names: List[str] = None,
        start_timestamp: datetime = None,
        end_timestamp: datetime = None,
        experiment_names: List[str] = None,
        season_names: List[str] = None,
        site_names: List[str] = None
    ) -> Generator["DatasetRecord", None, None]:
        """
        Filter dataset records based on various criteria.

        Examples:
            >>> records = DatasetRecord.filter(
            ...     dataset_names=["example_dataset"],
            ...     start_timestamp=datetime(2023, 10, 1, 0, 0, 0),
            ...     end_timestamp=datetime(2023, 10, 31, 23, 59, 59),
            ...     experiment_names=["example_experiment"],
            ...     season_names=["example_season"],
            ...     site_names=["example_site"]
            ... )
            >>> for record in records:
            ...     print(record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), dataset_name='another_dataset', dataset_data={...}, experiment_name='another_experiment', season_name='another_season', site_name='another_site')

        Args:
            dataset_names (List[str], optional): The names of the datasets. Defaults to None.
            start_timestamp (datetime, optional): The start timestamp for filtering. Defaults to None.
            end_timestamp (datetime, optional): The end timestamp for filtering. Defaults to None.
            experiment_names (List[str], optional): The names of the experiments. Defaults to None.
            season_names (List[str], optional): The names of the seasons. Defaults to None.
            site_names (List[str], optional): The names of the sites. Defaults to None.
        Yields:
            Generator["DatasetRecord", None, None]: A generator of matching dataset records.
        """
        try:
            if not any([dataset_names, start_timestamp, end_timestamp, experiment_names, season_names, site_names]):
                raise ValueError("At least one parameter must be provided.")
            records = DatasetRecordModel.filter_records(
                dataset_names=dataset_names,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error filtering DatasetRecords: {e}")
            yield None

    
    def update(
        self,
        dataset_data: dict = None,
        record_info: dict = None
    ) -> Optional["DatasetRecord"]:
        """
        Update the details of a dataset record.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> updated_record = record.update(
            ...     dataset_data={"new_key": "new_value"},
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            dataset_data (dict, optional): The new data content. Defaults to None.
            record_info (dict, optional): The new additional info. Defaults to None.
        Returns:
            Optional["DatasetRecord"]: The updated dataset record, or None if an error occurred.
        """
        try:
            if not any([dataset_data, record_info]):
                logger.warning(f"At least one parameter must be provided to update the DatasetRecord.")
                return None
            current_id = self.id
            dataset_record = DatasetRecordModel.get(current_id)
            if not dataset_record:
                logger.debug(f"DatasetRecord with id {current_id} not found.")
                return None
            dataset_record = DatasetRecordModel.update(
                dataset_record,
                dataset_data=dataset_data,
                record_info=record_info
            )
            dataset_record = self.model_validate(dataset_record)
            self.refresh()
            return dataset_record
        except Exception as e:
            logger.error(f"Error updating DatasetRecord: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete a dataset record.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> result = record.delete()
            >>> print(result)
            True

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        try:
            current_id = self.id
            dataset_record = DatasetRecordModel.get(current_id)
            if not dataset_record:
                logger.debug(f"DatasetRecord with id {current_id} not found.")
                return False
            DatasetRecordModel.delete(dataset_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting DatasetRecord: {e}")
            return False
        
    def refresh(self) -> Optional["DatasetRecord"]:
        """
        Refresh the dataset record's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> refreshed_record = record.refresh()
            >>> print(refreshed_record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')
   

        Returns:
            Optional["DatasetRecord"]: The refreshed dataset record, or None if an error occurred.
        """
        try:
            db_instance = DatasetRecordModel.get(self.id)
            if not db_instance:
                logger.debug(f"DatasetRecord with id {self.id} not found.")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing DatasetRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the dataset record.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> record_info = record.get_info()
            >>> record_info
            { 'info_key': 'info_value' }


        Returns:
            Optional[dict]: The record info dictionary, or None if not found.
        """
        try:
            current_id = self.id
            dataset_record = DatasetRecordModel.get(current_id)
            if not dataset_record:
                logger.debug(f"DatasetRecord with id {current_id} not found.")
                return None
            record_info = dataset_record.record_info
            if not record_info:
                logger.info(f"No record info found for DatasetRecord with id {current_id}.")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting record info: {e}")
            return None

    def set_info(self, record_info: dict) -> Optional["DatasetRecord"]:
        """
        Set the additional information of the dataset record.

        Examples:
            >>> record = DatasetRecord.get_by_id(UUID('...'))
            >>> updated_record = record.set_info(
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> updated_record.get_info()
            { 'new_info_key': 'new_info_value' }


        Args:
            record_info (dict): The record info dictionary.
        Returns:
            Optional["DatasetRecord"]: The updated dataset record, or None if an error occurred.
        """
        try:
            current_id = self.id
            dataset_record = DatasetRecordModel.get(current_id)
            if not dataset_record:
                logger.debug(f"DatasetRecord with id {current_id} not found.")
                return None
            dataset_record = DatasetRecordModel.update(
                dataset_record,
                record_info=record_info
            )
            dataset_record = self.model_validate(dataset_record)
            self.refresh()
            return dataset_record
        except Exception as e:
            logger.error(f"Error setting record info: {e}")
            return None
    
    @classmethod
    def create_file_uri(cls, record: "DatasetRecord") -> Optional[str]:
        """
        Create a file URI for the dataset record.

        Examples:
            >>> record = DatasetRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_file="/path/to/record/file.txt"
            ... )
            >>> file_uri = DatasetRecord.create_file_uri(record)
            >>> print(file_uri)
            dataset_data/example_experiment/example_dataset/2023-10-01/example_site/example_season/1704163200000.txt

        Args:
            record (DatasetRecord): The dataset record.
        Returns:
            Optional[str]: The file URI, or None if an error occurred.
        """
        try:
            original_file_path = record.record_file
            if not original_file_path:
                logger.warning(f"record_file is required to create file URI.")
                return None
            if not os.path.exists(original_file_path):
                logger.warning(f"File {original_file_path} does not exist.")
                return None
            # Assuming the file is stored in a specific structure, we can create a file URI
            collection_date = record.collection_date.strftime("%Y-%m-%d")
            dataset_name = record.dataset_name
            experiment_name = record.experiment_name
            season_name = record.season_name
            site_name = record.site_name
            file_extension = os.path.splitext(original_file_path)[1]
            file_timestamp = str(int(record.timestamp.timestamp() * 1000))
            file_key = f"dataset_data/{experiment_name}/{dataset_name}/{collection_date}/{site_name}/{season_name}/{file_timestamp}{file_extension}"
            return file_key
        except Exception as e:
            logger.error(f"Error creating file URI: {e}")
            return None


    @classmethod
    def process_record(cls, record: "DatasetRecord") -> "DatasetRecord":
        """
        Process the dataset record for storage, including file upload and metadata generation.

        This method handles the file upload to the storage provider and updates the record's file URI.

        Examples:
            >>> record = DatasetRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site",
            ...     record_file="/path/to/record/file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> processed_record = DatasetRecord.process_record(record)
            >>> print(processed_record)
            DatasetRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), dataset_name='example_dataset', dataset_data={...}, experiment_name='example_experiment', season_name='example_season', site_name='example_site')

        Args:
            record (DatasetRecord): The dataset record to process.
        Returns:
            DatasetRecord: The processed dataset record.
        """
        try:
            file = record.record_file
            if not file:
                return record
            file_key = cls.create_file_uri(record)
            if not file_key:
                logger.info(f"Failed to create file URI for record: {record}")
                return record
            content_type, _ = mimetypes.guess_type(file)
            # Generate Metadata for upload
            file_metadata = {
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
            logger.error(f"Error processing record: {e}")
            return record


