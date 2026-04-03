"""
This module defines the ScriptRecord class, which represents a record of a script, including metadata, associations to datasets, experiments, sites, and seasons, and file handling capabilities.

It includes methods for creating, retrieving, updating, and deleting script records, as well as methods for checking existence, searching, filtering, and managing file handling for records.

This module includes the following methods:

- `exists`: Check if a script record with the given parameters exists.
- `create`: Create a new script record.
- `get`: Retrieve a script record by its parameters.
- `get_by_id`: Retrieve a script record by its ID.
- `get_all`: Retrieve all script records.
- `search`: Search for script records based on various criteria.
- `filter`: Filter script records based on custom logic.
- `update`: Update the details of a script record.
- `delete`: Delete a script record.
- `refresh`: Refresh the script record's data from the database.
- `get_info`: Get the additional information of the script record.
- `set_info`: Set the additional information of the script record.
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
from gemini.db.models.columnar.script_records import ScriptRecordModel
from gemini.db.models.views.script_records_immv import ScriptRecordsIMMVModel
from datetime import date, datetime

logger = logging.getLogger(__name__)

class ScriptRecord(APIBase, FileHandlerMixin):
    """
    Represents a record of a script, including metadata, associations to datasets, experiments, sites, and seasons, and file handling capabilities.

    Attributes:
        id (Optional[ID]): The unique identifier of the script record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        script_id (Optional[ID]): The ID of the associated script.
        script_name (Optional[str]): The name of the associated script.
        script_data (Optional[dict]): The data content of the script record.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        experiment_name (Optional[str]): The name of the associated experiment.
        season_id (Optional[ID]): The ID of the associated season.
        season_name (Optional[str]): The name of the associated season.
        site_id (Optional[ID]): The ID of the associated site.
        site_name (Optional[str]): The name of the associated site.
        record_file (Optional[str]): The file path or URI of the record file.
        record_info (Optional[dict]): Additional information about the record.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "script_record_id"))

    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    script_id: Optional[ID] = None
    script_name: Optional[str] = None
    script_data: Optional[dict] = None
    experiment_id: Optional[ID] = None
    experiment_name : Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the ScriptRecord object."""
        return f"ScriptRecord(id={self.id}, timestamp={self.timestamp}, script_name={self.script_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    def __repr__(self):
        """Return a detailed string representation of the ScriptRecord object."""
        return f"ScriptRecord(id={self.id}, timestamp={self.timestamp}, script_name={self.script_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        script_name: str,
        dataset_name: str,
        experiment_name: str,
        season_name: str,
        site_name: str
    ) -> bool:
        """
        Check if a script record with the given parameters exists.

        Examples:
            >>> ScriptRecord.exists(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     script_name="example_script",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site"
            ... )
            True

        Args:
            timestamp (datetime): The timestamp of the record.
            script_name (str): The name of the script.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.
        Returns:
            bool: True if the script record exists, False otherwise.
        """
        try:
            exists = ScriptRecordModel.exists(
                timestamp=timestamp,
                script_name=script_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of ScriptRecord: {e}")
            raise e
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        script_name: str = None,
        script_data: dict = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        record_file: str = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["ScriptRecord"]:
        """
        Create a new script record.

        Examples:
            >>> script_record = ScriptRecord.create(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     script_name="example_script",
            ...     script_data={"key": "value"},
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="/path/to/file.txt",
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> print(script_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to now.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            script_name (str, optional): The name of the script. Defaults to None.
            script_data (dict, optional): The data content. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            record_file (str, optional): The file path or URI. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
            insert_on_create (bool, optional): Whether to insert on create. Defaults to True.
        Returns:
            Optional[ScriptRecord]: The created script record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, site_name, season_name]):
                raise ValueError("At least one of experiment_name, site_name, or season_name must be provided.")
            if not script_name:
                raise ValueError("Script name is required.")
            if not dataset_name:
                raise ValueError("Dataset name is required.")
            if not timestamp:
                raise ValueError("Timestamp is required.")
            if not collection_date:
                collection_date = timestamp.date()
            if not script_data and not record_file:
                raise ValueError("At least one of script_data or record_file must be provided.")
            script_record = ScriptRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                script_name=script_name,
                script_data=script_data,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                record_file=record_file,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([script_record])
                if not insert_success:
                    logger.info(f"Failed to insert ScriptRecord: {script_record}")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info(f"No new ScriptRecord was inserted.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                script_record = cls.get_by_id(inserted_record_id)
            return script_record
        except Exception as e:
            logger.error(f"Error creating ScriptRecord: {e}")
            raise None
        
    @classmethod
    def insert(cls, records: List["ScriptRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of script records into the database.

        Args:
            records (List[ScriptRecord]): The records to insert.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not records or len(records) == 0:
                logger.info(f"No records provided for insertion.")
                return False, []
            records = [cls.process_record(record) for record in tqdm(records, desc="Processing ScriptRecords")]
            records_to_insert = []
            for record in records:
                record_dict = record.model_dump()
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                records_to_insert.append(record_dict)
            logger.info(f"Inserting {len(records_to_insert)} records.")
            inserted_record_ids = ScriptRecordModel.insert_bulk('script_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_record_ids)} records.")
            return True, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting ScriptRecords: {e}")
            return False, []
        
    @classmethod
    def get(
        cls,
        timestamp: datetime,
        script_name: str,
        dataset_name: str,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> Optional["ScriptRecord"]:
        """
        Retrieve a script record by its parameters.

        Examples:
            >>> script_record = ScriptRecord.get(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     script_name="example_script",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     season_name="example_season",
            ...     site_name="example_site"
            ... )
            >>> print(script_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            timestamp (datetime): The timestamp of the record.
            script_name (str): The name of the script.
            dataset_name (str): The name of the dataset.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Optional[ScriptRecord]: The script record, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning(f"Timestamp is required to get ScriptRecord.")
                return None
            if not dataset_name:
                logger.warning(f"Dataset name is required to get ScriptRecord.")
                return None
            if not script_name:
                logger.warning(f"Script name is required to get ScriptRecord.")
                return None
            if not experiment_name and not season_name and not site_name:
                logger.warning(f"At least one of experiment_name, season_name, or site_name is required to get ScriptRecord.")
                return None
            script_record = ScriptRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                script_name=script_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not script_record:
                logger.info(f"No ScriptRecord found for the given parameters.")
                return None
            script_record = cls.model_validate(script_record)
            return script_record
        except Exception as e:
            logger.error(f"Error getting ScriptRecord: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ScriptRecord"]:
        """
        Retrieve a script record by its ID.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> print(script_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            id (UUID | int | str): The ID of the script record.
        Returns:
            Optional[ScriptRecord]: The script record, or None if not found.
        """
        try:
            db_instance = ScriptRecordModel.get(id)
            if not db_instance:
                logger.info(f"No ScriptRecord found with ID: {id}")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting ScriptRecord by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["ScriptRecord"]]:
        """
        Retrieve all script records, up to a specified limit.

        Examples:
            >>> script_records = ScriptRecord.get_all(limit=10)
            >>> for record in script_records:
            ...     print(record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), script_name='another_script', dataset_name='another_dataset', experiment_name='another_experiment', site_name='another_site', season_name='another_season)

        Args:
            limit (int, optional): The maximum number of records to retrieve. Defaults to 100.
        Returns:
            Optional[List[ScriptRecord]]: List of script records, or None if not found.
        """
        try:
            records = ScriptRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info(f"No ScriptRecords found.")
                return None
            records = [cls.model_validate(record) for record in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all ScriptRecords: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        script_name: str = None,
        script_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        collection_date: date = None,
        record_info: dict = None
    ) -> Generator["ScriptRecord", None, None]:
        """
        Search for script records based on various criteria.

        Examples:
            >>> script_records = ScriptRecord.search(
            ...     script_name="example_script",
            ...     dataset_name="example_dataset",
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     collection_date=date(2023, 10, 1),
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in script_records:
            ...     print(record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            script_name (str, optional): The name of the script. Defaults to None.
            script_data (dict, optional): The data content. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Yields:
            ScriptRecord: Matching script records.
        """
        try:
            if not any([script_name, dataset_name, experiment_name, site_name, season_name, collection_date, record_info]):
                logger.warning(f"At least one parameter must be provided for search.")
                return
            records = ScriptRecordsIMMVModel.stream(
                script_name=script_name,
                script_data=script_data,
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
            logger.error(f"Error searching ScriptRecords: {e}")
            yield None

    @classmethod
    def filter(
        cls,
        start_timestamp: datetime = None,
        end_timestamp: datetime = None,
        script_names: List[str] = None,
        dataset_names: List[str] = None,
        experiment_names: List[str] = None,
        season_names: List[str] = None,
        site_names: List[str] = None
    ) -> Generator["ScriptRecord", None, None]:
        """
        Filter script records based on custom logic.

        Examples:
            >>> script_records = ScriptRecord.filter(
            ...     start_timestamp=datetime(2023, 10, 1, 0, 0, 0),
            ...     end_timestamp=datetime(2023, 10, 31, 23, 59, 59),
            ...     script_names=["example_script"],
            ...     dataset_names=["example_dataset"],
            ...     experiment_names=["example_experiment"],
            ...     season_names=["example_season"],
            ...     site_names=["example_site"]
            ... )
            >>> for record in script_records:
            ...     print(record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), script_name='another_script', dataset_name='another_dataset', experiment_name='another_experiment', site_name='another_site', season_name='another_season)

        Args:
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            script_names (List[str], optional): List of script names. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
        Yields:
            ScriptRecord: Filtered script records.
        """
        try:
            if not any([start_timestamp, end_timestamp, script_names, dataset_names, experiment_names, season_names, site_names]):
                logger.warning(f"At least one parameter must be provided for filter.")
                return
            records = ScriptRecordModel.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                script_names=script_names,
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error filtering ScriptRecords: {e}")
            yield None
    

    def update(
        self,
        script_data: dict = None,
        record_info: dict = None
    ) -> Optional["ScriptRecord"]:
        """
        Update the details of the script record.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> updated_record = script_record.update(
            ...     script_data={"new_key": "new_value"},
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            script_data (dict, optional): The new script data. Defaults to None.
            record_info (dict, optional): The new record information. Defaults to None.
        Returns:
            Optional[ScriptRecord]: The updated script record, or None if an error occurred.
        """
        try:
            if not any([script_data, record_info]):
                logger.warning(f"At least one parameter must be provided for update.")
                return None
            current_id = self.id
            script_record = ScriptRecordModel.get(current_id)
            if not script_record:
                logger.info(f"No ScriptRecord found with ID: {current_id}")
                return None
            script_record = ScriptRecordModel.update(
                script_record,
                script_data=script_data,
                record_info=record_info
            )
            script_record = self.model_validate(script_record)
            self.refresh()
            return script_record
        except Exception as e:
            logger.error(f"Error updating ScriptRecord: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the script record.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> success = script_record.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the script record was deleted, False otherwise.
        """
        try:
            current_id = self.id
            script_record = ScriptRecordModel.get(current_id)
            if not script_record:
                logger.info(f"No ScriptRecord found with ID: {current_id}")
                return False
            ScriptRecordModel.delete(script_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting ScriptRecord: {e}")
            return False
        
    def refresh(self) -> Optional["ScriptRecord"]:
        """
        Refresh the script record's data from the database.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> refreshed_record = script_record.refresh()
            >>> print(refreshed_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Returns:
            Optional[ScriptRecord]: The refreshed script record, or None if an error occurred.
        """
        try:
            db_instance = ScriptRecordModel.get(self.id)
            if not db_instance:
                logger.info(f"No ScriptRecord found with ID: {self.id}")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing ScriptRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the script record.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> record_info = script_record.get_info()
            >>> print(record_info)
            {'info_key': 'info_value'}

        Returns:
            Optional[dict]: The record's info, or None if not found.
        """
        try:
            current_id = self.id
            script_record = ScriptRecordModel.get(current_id)
            if not script_record:
                logger.info(f"No ScriptRecord found with ID: {current_id}")
                return None
            record_info = script_record.record_info
            if not record_info:
                logger.info(f"No record info found for ScriptRecord with ID: {current_id}")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting record info: {e}")
            return None
        
    def set_info(self, record_info: dict) -> Optional["ScriptRecord"]:
        """
        Set the additional information of the script record.

        Examples:
            >>> script_record = ScriptRecord.get_by_id(UUID('...'))
            >>> updated_record = script_record.set_info(
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            record_info (dict): The new information to set.
        Returns:
            Optional[ScriptRecord]: The updated script record, or None if an error occurred.
        """
        try:
            current_id = self.id
            script_record = ScriptRecordModel.get(current_id)
            if not script_record:
                logger.info(f"No ScriptRecord found with ID: {current_id}")
                return None
            ScriptRecordModel.update(
                script_record,
                record_info=record_info
            )
            script_record = self.model_validate(script_record)
            self.refresh()
            return script_record
        except Exception as e:
            logger.error(f"Error setting record info: {e}")
            return None
        
    @classmethod
    def create_file_uri(cls, record: "ScriptRecord") -> Optional[str]:
        """
        Create a file URI for the given script record.

        Examples:
            >>> record = ScriptRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     script_name="example_script",
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="/path/to/file.txt"
            ... )
            >>> file_uri = ScriptRecord.create_file_uri(record)
            >>> print(file_uri)
            script_data/example_experiment/example_script/example_dataset/2023-10-01/example_site/example_season/1706467200000.txt

        Args:
            record (ScriptRecord): The script record for which to create the file URI.
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
            script_name = record.script_name
            dataset_name = record.dataset_name
            experiment_name = record.experiment_name
            season_name = record.season_name
            site_name = record.site_name
            file_extension = os.path.splitext(original_file_path)[1]
            file_timestamp = str(int(record.timestamp.timestamp() * 1000))
            file_key = f"script_data/{experiment_name}/{script_name}/{dataset_name}/{collection_date}/{site_name}/{season_name}/{file_timestamp}{file_extension}"
            return file_key
        except Exception as e:
            logger.error(f"Error creating file URI: {e}")
            return None


    @classmethod
    def process_record(cls, record: "ScriptRecord") -> "ScriptRecord":
        """
        Process a script record (custom logic, e.g., file upload).

        Examples:
            >>> record = ScriptRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="example_dataset",
            ...     script_name="example_script",
            ...     experiment_name="example_experiment",
            ...     site_name="example_site",
            ...     season_name="example_season",
            ...     record_file="/path/to/file.txt"
            ... )
            >>> processed_record = ScriptRecord.process_record(record)
            >>> print(processed_record)
            ScriptRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), script_name='example_script', dataset_name='example_dataset', experiment_name='example_experiment', site_name='example_site', season_name='example_season)

        Args:
            record (ScriptRecord): The script record to process.
        Returns:
            ScriptRecord: The processed script record.
        """
        try:
            file = record.record_file
            if not file:
                logger.warning(f"record_file is required to process ScriptRecord.")
                return record
            file_key = cls.create_file_uri(record)
            if not file_key:
                logger.info(f"Failed to create file URI for ScriptRecord: {record}")
                return record
            content_type, _ = mimetypes.guess_type(file)
            # Generate Metadata for upload
            file_metadata = {
                "Script-Name": record.script_name,
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
            logger.error(f"Error processing ScriptRecord: {e}")
            return record

