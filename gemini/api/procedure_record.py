"""
This module defines the ProcedureRecord class, which represents a record of a procedure, including metadata, associations to datasets, experiments, sites, and seasons, and file handling capabilities.

It includes methods for creating, retrieving, updating, and deleting procedure records, as well as methods for checking existence, searching, filtering, and managing file handling for records.

This module includes the following methods:

- `exists`: Check if a procedure record with the given parameters exists.
- `create`: Create a new procedure record.
- `get`: Retrieve a procedure record by its parameters.
- `get_by_id`: Retrieve a procedure record by its ID.
- `get_all`: Retrieve all procedure records.
- `search`: Search for procedure records based on various criteria.
- `filter`: Filter procedure records based on custom logic.
- `update`: Update the details of a procedure record.
- `delete`: Delete a procedure record.
- `refresh`: Refresh the procedure record's data from the database.
- `get_info`: Get the additional information of the procedure record.
- `set_info`: Set the additional information of the procedure record.
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
from gemini.db.models.columnar.procedure_records import ProcedureRecordModel
from gemini.db.models.views.procedure_records_immv import ProcedureRecordsIMMVModel


from datetime import date, datetime

logger = logging.getLogger(__name__)

class ProcedureRecord(APIBase, FileHandlerMixin):
    """
    Represents a record of a procedure, including metadata, associations to datasets, experiments, sites, and seasons, and file handling capabilities.

    Attributes:
        id (Optional[ID]): The unique identifier of the procedure record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        procedure_id (Optional[ID]): The ID of the associated procedure.
        procedure_name (Optional[str]): The name of the associated procedure.
        procedure_data (Optional[dict]): The data content of the procedure record.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        experiment_name (Optional[str]): The name of the associated experiment.
        season_id (Optional[ID]): The ID of the associated season.
        season_name (Optional[str]): The name of the associated season.
        site_id (Optional[ID]): The ID of the associated site.
        site_name (Optional[str]): The name of the associated site.
        record_file (Optional[str]): The file path or URI of the record file.
        record_info (Optional[dict]): Additional information about the record.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "procedure_record_id"))
    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    procedure_id: Optional[ID] = None
    procedure_name: Optional[str] = None
    procedure_data: Optional[dict] = None
    experiment_id: Optional[ID] = None
    experiment_name : Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the ProcedureRecord object."""
        return f"ProcedureRecord(id={self.id}, timestamp={self.timestamp}, procedure_name={self.procedure_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    def __repr__(self):
        """Return a detailed string representation of the ProcedureRecord object."""
        return f"ProcedureRecord(id={self.id}, timestamp={self.timestamp}, procedure_name={self.procedure_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        procedure_name: str,
        dataset_name: str,
        experiment_name: str,
        season_name: str,
        site_name: str
    ) -> bool:
        """
        Check if a procedure record with the given parameters exists.

        Examples:
            >>> ProcedureRecord.exists(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     procedure_name="SampleProcedure",
            ...     dataset_name="SampleDataset",
            ...     experiment_name="SampleExperiment",
            ...     season_name="SampleSeason",
            ...     site_name="SampleSite"
            ... )
            True

        Args:
            timestamp (datetime): The timestamp of the record.
            procedure_name (str): The name of the procedure.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.
        Returns:
            bool: True if the procedure record exists, False otherwise.
        """
        try:
            exists = ProcedureRecordModel.exists(
                timestamp=timestamp,
                procedure_name=procedure_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of ProcedureRecord: {e}")
            raise e
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        procedure_name: str = None,
        procedure_data: dict = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        record_file: str = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["ProcedureRecord"]:
        """
        Create a new procedure record.

        Examples:
            >>> record = ProcedureRecord.create(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="SampleDataset",
            ...     procedure_name="SampleProcedure",
            ...     procedure_data={"key": "value"},
            ...     experiment_name="SampleExperiment",
            ...     site_name="SampleSite",
            ...     season_name="SampleSeason",
            ...     record_file="/path/to/file.txt",
            ...     record_info={"info_key": "info_value"},
            ...     insert_on_create=True
            ... )
            >>> print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to now.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            procedure_name (str, optional): The name of the procedure. Defaults to None.
            procedure_data (dict, optional): The data content. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            record_file (str, optional): The file path or URI. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
            insert_on_create (bool, optional): Whether to insert on create. Defaults to True.
        Returns:
            Optional[ProcedureRecord]: The created procedure record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, site_name, season_name]):
                raise ValueError("At least one of experiment_name, site_name, or season_name must be provided.")
            if not procedure_name:
                raise ValueError("Procedure name is required.")
            if not dataset_name:
                raise ValueError("Dataset name is required.")
            if not timestamp:
                raise ValueError("Timestamp is required.")
            if not collection_date:
                collection_date = timestamp.date()
            if not procedure_data and not record_file:
                raise ValueError("At least one of procedure_data or record_file must be provided.")
            procedure_record = ProcedureRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                procedure_name=procedure_name,
                procedure_data=procedure_data,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                record_file=record_file,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([procedure_record])
                if not insert_success:
                    logger.info(f"Failed to insert ProcedureRecord: {procedure_record}")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info(f"No new ProcedureRecord was inserted.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                procedure_record = cls.get_by_id(inserted_record_id)
            return procedure_record
        except Exception as e:
            logger.error(f"Error creating ProcedureRecord: {e}")
            raise None
        
    @classmethod
    def insert(cls, records: List["ProcedureRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of procedure records into the database.

        Args:
            records (List[ProcedureRecord]): The records to insert.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not records or len(records) == 0:
                logger.info(f"No records provided for insertion.")
                return False, []
            records = [cls.process_record(record) for record in tqdm(records, desc="Processing ProcedureRecords")]
            records_to_insert = []
            for record in records:
                record_dict = record.model_dump()
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                records_to_insert.append(record_dict)
            logger.info(f"Inserting {len(records_to_insert)} records.")
            inserted_record_ids = ProcedureRecordModel.insert_bulk('procedure_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_record_ids)} records.")
            return True, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting ProcedureRecords: {e}")
            return False, []
        
    @classmethod
    def get(
        cls,
        timestamp: datetime,
        procedure_name: str,
        dataset_name: str,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> Optional["ProcedureRecord"]:
        """
        Retrieve a procedure record by its parameters.

        Examples:
            >>> record = ProcedureRecord.get(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     procedure_name="SampleProcedure",
            ...     dataset_name="SampleDataset",
            ...     experiment_name="SampleExperiment",
            ...     season_name="SampleSeason",
            ...     site_name="SampleSite"
            ... )
            >>> print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            timestamp (datetime): The timestamp of the record.
            procedure_name (str): The name of the procedure.
            dataset_name (str): The name of the dataset.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Optional[ProcedureRecord]: The procedure record, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning(f"Timestamp is required to get ProcedureRecord.")
                return None
            if not dataset_name:
                logger.warning(f"Dataset name is required to get ProcedureRecord.")
                return None
            if not procedure_name:
                logger.warning(f"Procedure name is required to get ProcedureRecord.")
                return None
            if not experiment_name and not season_name and not site_name:
                logger.warning(f"At least one of experiment_name, season_name, or site_name is required to get ProcedureRecord.")
                return None
            procedure_record = ProcedureRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                procedure_name=procedure_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not procedure_record:
                logger.info(f"No ProcedureRecord found for the given parameters.")
                return None
            procedure_record = cls.model_validate(procedure_record)
            return procedure_record
        except Exception as e:
            logger.error(f"Error getting ProcedureRecord: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ProcedureRecord"]:
        """
        Retrieve a procedure record by its ID.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            id (UUID | int | str): The ID of the procedure record.
        Returns:
            Optional[ProcedureRecord]: The procedure record, or None if not found.
        """
        try:
            db_instance = ProcedureRecordModel.get(id)
            if not db_instance:
                logger.info(f"No ProcedureRecord found with ID: {id}")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting ProcedureRecord by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["ProcedureRecord"]]:
        """
        Retrieve all procedure records, up to a specified limit.

        Examples:
            >>> records = ProcedureRecord.get_all(limit=10)
            >>> for record in records:
            ...     print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), procedure_name='AnotherProcedure', dataset_name='AnotherDataset', experiment_name='AnotherExperiment', site_name='AnotherSite', season_name='AnotherSeason')

        Args:
            limit (int, optional): The maximum number of records to retrieve. Defaults to 100.
        Returns:
            Optional[List[ProcedureRecord]]: List of procedure records, or None if not found.
        """
        try:
            records = ProcedureRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info(f"No ProcedureRecords found.")
                return None
            records = [cls.model_validate(record) for record in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all ProcedureRecords: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        procedure_name: str = None,
        procedure_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        collection_date: date = None,
        record_info: dict = None
    ) -> Generator["ProcedureRecord", None, None]:
        """
        Search for procedure records based on various criteria.

        Examples:
            >>> records = ProcedureRecord.search(
            ...     procedure_name="SampleProcedure",
            ...     dataset_name="SampleDataset",
            ...     experiment_name="SampleExperiment",
            ...     site_name="SampleSite",
            ...     season_name="SampleSeason",
            ...     collection_date=date(2023, 10, 1),
            ...     record_info={"info_key": "info_value"}
            ... )
            >>> for record in records:
            ...     print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), procedure_name='AnotherProcedure', dataset_name='AnotherDataset', experiment_name='AnotherExperiment', site_name='AnotherSite', season_name='AnotherSeason')

        Args:
            procedure_name (str, optional): The name of the procedure. Defaults to None.
            procedure_data (dict, optional): The data content. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Yields:
            ProcedureRecord: Matching procedure records.
        """
        try:
            if not any([procedure_name, dataset_name, experiment_name, site_name, season_name, collection_date, record_info]):
                logger.warning(f"At least one parameter must be provided for search.")
                return
            records = ProcedureRecordsIMMVModel.stream(
                procedure_name=procedure_name,
                procedure_data=procedure_data,
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
            logger.error(f"Error searching ProcedureRecords: {e}")
            yield None


    @classmethod
    def filter(
        cls,
        procedure_names: List[str] = None,
        dataset_names: List[str] = None,
        start_timestamp: datetime = None,
        end_timestamp: datetime = None,
        experiment_names: List[str] = None,
        site_names: List[str] = None,
        season_names: List[str] = None
    ) -> Generator["ProcedureRecord", None, None]:
        """
        Filter procedure records based on custom logic.

        Examples:
            >>> records = ProcedureRecord.filter(
            ...     procedure_names=["SampleProcedure", "AnotherProcedure"],
            ...     dataset_names=["SampleDataset", "AnotherDataset"],
            ...     start_timestamp=datetime(2023, 10, 1, 0, 0, 0),
            ...     end_timestamp=datetime(2023, 10, 31, 23, 59, 59),
            ...     experiment_names=["SampleExperiment", "AnotherExperiment"],
            ...     site_names=["SampleSite", "AnotherSite"],
            ...     season_names=["SampleSeason", "AnotherSeason"]
            ... )
            >>> for record in records:
            ...     print(record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), procedure_name='AnotherProcedure', dataset_name='AnotherDataset', experiment_name='AnotherExperiment', site_name='AnotherSite', season_name='AnotherSeason')

        Args:
            procedure_names (List[str], optional): List of procedure names. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
        Yields:
            ProcedureRecord: Filtered procedure records.
        """
        try:
            if not any([procedure_names, dataset_names, start_timestamp, end_timestamp, experiment_names, site_names, season_names]):
                logger.warning(f"At least one parameter must be provided for filtering.")
                return
            records = ProcedureRecordModel.filter_records(
                procedure_names=procedure_names,
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
            logger.error(f"Error filtering ProcedureRecords: {e}")
            yield None

    def update(
        self,
        procedure_data: dict = None,
        record_info: dict = None
    ) -> Optional["ProcedureRecord"]:
        """
        Update the details of the procedure record.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> updated_record = record.update(
            ...     procedure_data={"new_key": "new_value"},
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            procedure_data (dict, optional): The new procedure data. Defaults to None.
            record_info (dict, optional): The new record information. Defaults to None.
        Returns:
            Optional[ProcedureRecord]: The updated procedure record, or None if an error occurred.
        """
        try:
            if not any([procedure_data, record_info]):
                logger.warning(f"At least one parameter must be provided for update.")
                return None
            current_id = self.id
            procedure_record = ProcedureRecordModel.get(current_id)
            if not procedure_record:
                logger.info(f"No ProcedureRecord found with ID: {current_id}")
                return None
            procedure_record = ProcedureRecordModel.update(
                procedure_record,
                procedure_data=procedure_data,
                record_info=record_info
            )
            procedure_record = self.model_validate(procedure_record)
            self.refresh()
            return procedure_record
        except Exception as e:
            logger.error(f"Error updating ProcedureRecord: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the procedure record.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> success = record.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the procedure record was deleted, False otherwise.
        """
        try:
            current_id = self.id
            procedure_record = ProcedureRecordModel.get(current_id)
            if not procedure_record:
                logger.info(f"No ProcedureRecord found with ID: {current_id}")
                return False
            ProcedureRecordModel.delete(procedure_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting ProcedureRecord: {e}")
            return False
        
    def refresh(self) -> Optional["ProcedureRecord"]:
        """
        Refresh the procedure record's data from the database.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> refreshed_record = record.refresh()
            >>> print(refreshed_record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Returns:
            Optional[ProcedureRecord]: The refreshed procedure record, or None if an error occurred.
        """
        try:
            db_instance = ProcedureRecordModel.get(self.id)
            if not db_instance:
                logger.info(f"No ProcedureRecord found with ID: {self.id}")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing ProcedureRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the procedure record.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> info = record.get_info()
            >>> print(info)
            {'info_key': 'info_value'}

        Returns:
            Optional[dict]: The record's info, or None if not found.
        """
        try:
            current_id = self.id
            procedure_record = ProcedureRecordModel.get(current_id)
            if not procedure_record:
                logger.info(f"No ProcedureRecord found with ID: {current_id}")
                return None
            record_info = procedure_record.record_info
            if not record_info:
                logger.info(f"No record info found for ProcedureRecord with ID: {current_id}")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting record info: {e}")
            return None
        
    def set_info(self, record_info: dict) -> Optional["ProcedureRecord"]:
        """
        Set the additional information of the procedure record.

        Examples:
            >>> record = ProcedureRecord.get_by_id(UUID('...'))
            >>> updated_record = record.set_info(
            ...     record_info={"new_info_key": "new_info_value"}
            ... )
            >>> print(updated_record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            record_info (dict): The new information to set.
        Returns:
            Optional[ProcedureRecord]: The updated procedure record, or None if an error occurred.
        """
        try:
            current_id = self.id
            procedure_record = ProcedureRecordModel.get(current_id)
            if not procedure_record:
                logger.info(f"No ProcedureRecord found with ID: {current_id}")
                return None
            ProcedureRecordModel.update(
                procedure_record,
                record_info=record_info
            )
            procedure_record = self.model_validate(procedure_record)
            self.refresh()
            return procedure_record
        except Exception as e:
            logger.error(f"Error setting record info: {e}")
            return None
        
    @classmethod
    def create_file_uri(cls, record: "ProcedureRecord") -> Optional[str]:
        """
        Create a file URI for the given procedure record.

        Examples:
            >>> record = ProcedureRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="SampleDataset",
            ...     procedure_name="SampleProcedure",
            ...     experiment_name="SampleExperiment",
            ...     site_name="SampleSite",
            ...     season_name="SampleSeason",
            ...     record_file="/path/to/file.txt"
            ... )
            >>> file_uri = ProcedureRecord.create_file_uri(record)
            >>> print(file_uri)
            procedure_data/SampleExperiment/SampleProcedure/SampleDataset/2023-10-01/SampleSite/SampleSeason/1706467200000.txt

        Args:
            record (ProcedureRecord): The procedure record for which to create the file URI.
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
            procedure_name = record.procedure_name
            dataset_name = record.dataset_name
            experiment_name = record.experiment_name
            season_name = record.season_name
            site_name = record.site_name
            file_extension = os.path.splitext(original_file_path)[1]
            file_timestamp = str(int(record.timestamp.timestamp() * 1000))
            file_key = f"procedure_data/{experiment_name}/{procedure_name}/{dataset_name}/{collection_date}/{site_name}/{season_name}/{file_timestamp}{file_extension}"
            return file_key
        except Exception as e:
            logger.error(f"Error creating file URI: {e}")
            return None


    @classmethod
    def process_record(cls, record: "ProcedureRecord") -> "ProcedureRecord":
        """
        Process a procedure record (custom logic, e.g., file upload).

        Examples:
            >>> record = ProcedureRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="SampleDataset",
            ...     procedure_name="SampleProcedure",
            ...     experiment_name="SampleExperiment",
            ...     site_name="SampleSite",
            ...     season_name="SampleSeason",
            ...     record_file="/path/to/file.txt"
            ... )
            >>> processed_record = ProcedureRecord.process_record(record)
            >>> print(processed_record)
            ProcedureRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), procedure_name='SampleProcedure', dataset_name='SampleDataset', experiment_name='SampleExperiment', site_name='SampleSite', season_name='SampleSeason')

        Args:
            record (ProcedureRecord): The procedure record to process.
        Returns:
            ProcedureRecord: The processed procedure record.
        """
        try:
            file = record.record_file
            if not file:
                logger.warning(f"record_file is required to process ProcedureRecord.")
                return record
            file_key = cls.create_file_uri(record)
            if not file_key:
                logger.info(f"Failed to create file URI for ProcedureRecord: {record}")
                return record
            content_type, _ = mimetypes.guess_type(file)
            # Generate Metadata for upload
            file_metadata = {
                "Procedure-Name": record.procedure_name,
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
            logger.error(f"Error processing ProcedureRecord: {e}")
            return record

