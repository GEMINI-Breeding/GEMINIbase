"""
This module defines the TraitRecord class, which represents a record of a trait, including metadata, associations to datasets, experiments, sites, seasons, and plots, and related operations.

It includes methods for creating, retrieving, updating, and deleting trait records, as well as methods for checking existence, searching, filtering, and managing additional information.

This module includes the following methods:

- `exists`: Check if a trait record with the given parameters exists.
- `create`: Create a new trait record.
- `insert`: Insert a list of trait records into the database.
- `get`: Retrieve a trait record by its parameters.
- `get_by_id`: Retrieve a trait record by its ID.
- `get_all`: Retrieve all trait records.
- `search`: Search for trait records based on various criteria.
- `filter`: Filter trait records based on custom logic.
- `update`: Update the details of a trait record.
- `delete`: Delete a trait record.
- `refresh`: Refresh the trait record's data from the database.
- `get_info`: Get the additional information of the trait record.
- `set_info`: Set the additional information of the trait record.

"""

from typing import Optional, List, Generator
from uuid import UUID
from tqdm import tqdm

import logging
from gemini.api.types import ID
from pydantic import Field, AliasChoices
from gemini.api.base import APIBase
from gemini.db.models.columnar.trait_records import TraitRecordModel
from gemini.db.models.views.trait_records_immv import TraitRecordsIMMVModel

from datetime import date, datetime

logger = logging.getLogger(__name__)

class TraitRecord(APIBase):
    """
    Represents a record of a trait, including metadata, associations to datasets, experiments, sites, seasons, and plots, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the trait record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        trait_id (Optional[ID]): The ID of the associated trait.
        trait_name (Optional[str]): The name of the associated trait.
        trait_value (Optional[float]): The value of the trait.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        experiment_name (Optional[str]): The name of the associated experiment.
        season_id (Optional[ID]): The ID of the associated season.
        season_name (Optional[str]): The name of the associated season.
        site_id (Optional[ID]): The ID of the associated site.
        site_name (Optional[str]): The name of the associated site.
        plot_id (Optional[ID]): The ID of the associated plot.
        plot_number (Optional[int]): The number of the associated plot.
        plot_row_number (Optional[int]): The row number of the associated plot.
        plot_column_number (Optional[int]): The column number of the associated plot.
        record_info (Optional[dict]): Additional information about the record.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "trait_record_id"))

    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    trait_id: Optional[ID] = None
    trait_name: Optional[str] = None
    trait_value: Optional[float] = None
    experiment_id: Optional[ID] = None
    experiment_name : Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    plot_id: Optional[ID] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the TraitRecord object."""
        return f"TraitRecord(id={self.id}, timestamp={self.timestamp}, trait_name={self.trait_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name}, plot_number={self.plot_number}, plot_row_number={self.plot_row_number}, plot_column_number={self.plot_column_number})"

    def __repr__(self):
        """Return a detailed string representation of the TraitRecord object."""
        return f"TraitRecord(id={self.id}, timestamp={self.timestamp}, trait_name={self.trait_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name}, plot_number={self.plot_number}, plot_row_number={self.plot_row_number}, plot_column_number={self.plot_column_number})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        trait_name: str,
        dataset_name: str,
        experiment_name: str,
        site_name: str,
        season_name: str,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> bool:
        """
        Check if a trait record with the given parameters exists.

        Examples:
            >>> TraitRecord.exists(
            ...     timestamp=datetime(2023, 10, 1, 12, 0),
            ...     trait_name="Height",
            ...     dataset_name="Plant Growth Study",
            ...     experiment_name="Growth Experiment 1",
            ...     site_name="Research Farm A",
            ...     season_name="Spring 2023",
            ...     plot_number=1,
            ...     plot_row_number=2,
            ...     plot_column_number=3
            ... )
            True


        Args:
            timestamp (datetime): The timestamp of the record.
            trait_name (str): The name of the trait.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            bool: True if the trait record exists, False otherwise.
        """
        try:
            exists = TraitRecordModel.exists(
                timestamp=timestamp,
                trait_name=trait_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of TraitRecord: {e}")
            raise e
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        trait_name: str = None,
        trait_value: float = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["TraitRecord"]:
        """
        Create a new trait record.

        Examples:
            >>> TraitRecord.create(
            ...     timestamp=datetime(2023, 10, 1, 12, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="Plant Growth Study",
            ...     trait_name="Height",
            ...     trait_value=150.0,
            ...     experiment_name="Growth Experiment 1",
            ...     site_name="Research Farm A",
            ...     season_name="Spring 2023",
            ...     plot_number=1,
            ...     plot_row_number=2,
            ...     plot_column_number=3,
            ...     record_info={"notes": "Initial measurement"},
            ...     insert_on_create=True
            ... )
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to now.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            trait_name (str, optional): The name of the trait. Defaults to None.
            trait_value (float, optional): The value of the trait. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
            insert_on_create (bool, optional): Whether to insert on create. Defaults to True.
        Returns:
            Optional[TraitRecord]: The created trait record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, site_name, season_name]):
                raise ValueError("At least one of experiment_name, site_name, or season_name must be provided.")
            if not trait_name:
                raise ValueError("Trait name is required.")
            if not dataset_name:
                raise ValueError("Dataset name is required.")
            # Plot row/column may only be provided together with a plot_number.
            # plot_number by itself is valid (row/column are optional).
            if (plot_row_number is not None or plot_column_number is not None) and plot_number is None:
                raise ValueError("plot_number is required when plot_row_number or plot_column_number is provided.")
            if not timestamp:
                timestamp = datetime.now()
            if not collection_date:
                collection_date = timestamp.date()
            # Allow 0.0 and negative values — only reject None/missing.
            if trait_value is None:
                raise ValueError("Trait value is required.")
            trait_record = TraitRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                trait_name=trait_name,
                trait_value=trait_value,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([trait_record])
                if not insert_success:
                    logger.info(f"Failed to insert TraitRecord: {trait_record}")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info(f"No TraitRecord IDs returned after insertion.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                trait_record = cls.get_by_id(inserted_record_id)
            return trait_record
        except Exception as e:
            logger.error(f"Error creating TraitRecord: {e}")
            return None
        
    @classmethod
    def insert(cls, records: List["TraitRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of trait records into the database.

        Args:
            records (List[TraitRecord]): The records to insert.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        if not records or len(records) == 0:
            logger.info(f"No records provided to insert.")
            return False, []
        records_to_insert = []
        for record in records:
            record_dict = record.model_dump()
            record_dict = {k: v for k, v in record_dict.items() if v is not None}
            records_to_insert.append(record_dict)
        logger.info(f"Inserting {len(records_to_insert)} TraitRecords.")
        # Deliberately does NOT swallow DB errors: Postgres trigger RAISEs
        # (e.g. "No matching plot found for the given parameters") carry the
        # actual cause the caller needs to surface to the user.
        inserted_record_ids = TraitRecordModel.insert_bulk('trait_records_unique', records_to_insert)
        logger.info(f"Inserted {len(inserted_record_ids)} TraitRecords.")
        return True, inserted_record_ids
        
    @classmethod
    def get(
        cls,
        timestamp: datetime,
        trait_name: str,
        dataset_name: str,
        experiment_name: str,
        site_name: str,
        season_name: str,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> Optional["TraitRecord"]:
        """
        Retrieve a trait record by its parameters.

        Examples:
            >>> TraitRecord.get(
            ...     timestamp=datetime(2023, 10, 1, 12, 0),
            ...     trait_name="Height",
            ...     dataset_name="Plant Growth Study",
            ...     experiment_name="Growth Experiment 1",
            ...     site_name="Research Farm A",
            ...     season_name="Spring 2023",
            ...     plot_number=1,
            ...     plot_row_number=2,
            ...     plot_column_number=3
            ... )
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            timestamp (datetime): The timestamp of the record.
            trait_name (str): The name of the trait.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            site_name (str): The name of the site.
            season_name (str): The name of the season.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            Optional[TraitRecord]: The trait record, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning("Timestamp is required to get TraitRecord.")
                return None
            if not trait_name:
                logger.warning("Trait name is required to get TraitRecord.")
                return None
            if not dataset_name:
                logger.warning("Dataset name is required to get TraitRecord.")
                return None
            if not experiment_name and not site_name and not season_name:
                logger.warning("At least one of experiment_name, site_name, or season_name is required to get TraitRecord.")
                return None
            if not all([plot_number, plot_row_number, plot_column_number]):
                logger.warning("Plot information (number, row, column) is required if any is provided.")
                return None
            trait_record = TraitRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                trait_name=trait_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            if not trait_record:
                logger.debug("TraitRecord not found with the provided parameters.")
                return None
            trait_record = cls.model_validate(trait_record)
            return trait_record
        except Exception as e:
            logger.error(f"Error getting TraitRecord: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["TraitRecord"]:
        """
        Retrieve a trait record by its ID.

        Examples:
            >>> TraitRecord.get_by_id(UUID('...'))
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            id (UUID | int | str): The ID of the trait record.
        Returns:
            Optional[TraitRecord]: The trait record, or None if not found.
        """
        try:
            db_instance = TraitRecordModel.get(id)
            if not db_instance:
                logger.debug(f"TraitRecord with ID {id} not found.")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting TraitRecord by ID {id}: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["TraitRecord"]]:
        """
        Retrieve all trait records, up to a specified limit.

        Examples:
            >>> TraitRecord.get_all(limit=10)
            >>> for record in TraitRecord.get_all(limit=10):
            ...     print(record)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), trait_name='Width', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            limit (int, optional): The maximum number of records to retrieve. Defaults to 100.
        Returns:
            Optional[List[TraitRecord]]: List of trait records, or None if not found.
        """
        try:
            records = TraitRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info(f"No TraitRecords found")
                return None
            records = [cls.model_validate(instance) for instance in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all TraitRecords: {e}")
            return None

    @classmethod
    def search(
        cls,
        dataset_name: str = None,
        trait_name: str = None,
        trait_value: float = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        collection_date: date = None,
        record_info: dict = None
    ) -> Generator["TraitRecord", None, None]:
        """
        Search for trait records based on various criteria.

        Examples:
            >>> for record in TraitRecord.search(dataset_name="Plant Growth Study", trait_name="Height"):
            ...     print(record)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            trait_name (str, optional): The name of the trait. Defaults to None.
            trait_value (float, optional): The value of the trait. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Yields:
            TraitRecord: Matching trait records.
        """
        try:
            if not any([dataset_name, trait_name, trait_value, experiment_name, site_name, season_name, plot_number, plot_row_number, plot_column_number, collection_date, record_info]):
                logger.warning("At least one search parameter must be provided.")
                return
            records = TraitRecordsIMMVModel.stream(
                dataset_name=dataset_name,
                trait_name=trait_name,
                trait_value=trait_value,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                collection_date=collection_date,
                record_info=record_info
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error searching TraitRecords: {e}")
            yield from []


    @classmethod
    def filter(
        cls,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        trait_names: Optional[List[str]] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> Generator["TraitRecord", None, None]:
        """
        Filter trait records based on custom logic.

        Examples:
            >>> records = TraitRecord.filter(
            ...     start_timestamp=datetime(2023, 10, 1, 0, 0),
            ...     end_timestamp=datetime(2023, 10, 31, 23, 59),
            ...     trait_names=["Height", "Width"],
            ...     dataset_names=["Plant Growth Study"],
            ...     experiment_names=["Growth Experiment 1"],
            ...     season_names=["Spring 2023"],
            ...     site_names=["Research Farm A"]
            ... )
            >>> for record in records:
            ...     print(record)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            trait_names (List[str], optional): List of trait names. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
        Yields:
            TraitRecord: Filtered trait records.
        """
        try:
            if not any([start_timestamp, end_timestamp, trait_names, dataset_names, experiment_names, season_names, site_names]):
                logger.warning("At least one filter parameter must be provided.")
                return
            records = TraitRecordModel.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                trait_names=trait_names,
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error filtering TraitRecords: {e}")
            yield from []

    def update(
        self,
        trait_value: float = None,
        record_info: dict = None
    ) -> Optional["TraitRecord"]:
        """
        Update the details of the trait record.

        Examples:
            >>> trait_record = TraitRecord.get_by_id(UUID('...'))
            >>> updated_record = trait_record.update(
            ...     trait_value=160.0,
            ...     record_info={"notes": "Updated measurement"}
            ... )
            >>> print(updated_record)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            trait_value (float, optional): The new trait value. Defaults to None.
            record_info (dict, optional): The new record information. Defaults to None.
        Returns:
            Optional[TraitRecord]: The updated trait record, or None if an error occurred.
        """
        try:
            if not any([trait_value, record_info]):
                logger.warning("At least one parameter must be provided to update TraitRecord.")
                return None
            current_id = self.id
            trait_record = TraitRecordModel.get(current_id)
            if not trait_record:
                logger.debug(f"TraitRecord with ID {current_id} not found.")
                return None
            trait_record = TraitRecordModel.update(
                trait_record,
                trait_value=trait_value,
                record_info=record_info
            )
            trait_record = self.model_validate(trait_record)
            self.refresh()
            return trait_record
        except Exception as e:
            logger.error(f"Error updating TraitRecord: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the trait record.

        Examples:
            >>> trait_record = TraitRecord.get_by_id(UUID('...'))
            >>> success = trait_record.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the trait record was deleted, False otherwise.
        """
        try:
            current_id = self.id
            trait_record = TraitRecordModel.get(current_id)
            if not trait_record:
                logger.debug(f"TraitRecord with ID {current_id} not found.")
                return False
            TraitRecordModel.delete(trait_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting TraitRecord: {e}")
            return False
        
    def refresh(self) -> Optional["TraitRecord"]:
        """
        Refresh the trait record's data from the database.

        Examples:
            >>> trait_record = TraitRecord.get_by_id(UUID('...'))
            >>> refreshed_record = trait_record.refresh()
            >>> print(refreshed_record)
            TraitRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), trait_name='Height', dataset_name='Plant Growth Study', experiment_name='Growth Experiment 1', site_name='Research Farm A', season_name='Spring 2023', plot_number=1, plot_row_number=2, plot_column_number=3)

        Returns:
            Optional[TraitRecord]: The refreshed trait record, or None if an error occurred.
        """
        try:
            db_instance = TraitRecordModel.get(self.id)
            if not db_instance:
                logger.debug(f"TraitRecord with ID {self.id} not found.")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != 'id':
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing TraitRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the trait record.

        Examples:
            >>> trait_record = TraitRecord.get_by_id(UUID('...'))
            >>> record_info = trait_record.get_info()
            >>> print(record_info)
            {'notes': 'Initial measurement', 'source': 'Field observation'}

        Returns:
            Optional[dict]: The record's info, or None if not found.
        """
        try:
            current_id = self.id
            trait_record = TraitRecordModel.get(current_id)
            if not trait_record:
                logger.debug(f"TraitRecord with ID {current_id} not found.")
                return None
            record_info = trait_record.record_info
            if not record_info:
                logger.info(f"No record info found for TraitRecord with ID {current_id}.")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting record info for TraitRecord: {e}")
            return None
        
    def set_info(self, record_info: dict) -> Optional["TraitRecord"]:
        """
        Set the additional information of the trait record.

        Examples:
            >>> trait_record = TraitRecord.get_by_id(UUID('...'))
            >>> updated_record = trait_record.set_info(
            ...     record_info={"notes": "Updated measurement", "source": "Field observation"}
            ... )
            >>> print(updated_record.record_info)
            {'notes': 'Updated measurement', 'source': 'Field observation'}

        Args:
            record_info (dict): The new information to set.
        Returns:
            Optional[TraitRecord]: The updated trait record, or None if an error occurred.
        """
        try:
            current_id = self.id
            trait_record = TraitRecordModel.get(current_id)
            if not trait_record:
                logger.debug(f"TraitRecord with ID {current_id} not found.")
                return None
            TraitRecordModel.update(
                trait_record,
                record_info=record_info
            )
            trait_record = self.model_validate(trait_record)
            self.refresh()
            return trait_record
        except Exception as e:
            logger.error(f"Error setting record info for TraitRecord: {e}")
            return None
