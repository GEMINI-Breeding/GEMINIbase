"""
This module defines the SensorRecord class, which represents a record of sensor data, including metadata, associations to datasets, experiments, sites, seasons, and plots, and file handling capabilities.

It includes methods for creating, retrieving, updating, and deleting sensor records, as well as methods for checking existence, searching, filtering, and managing file handling for records.

This module includes the following methods:

- `exists`: Check if a sensor record with the given parameters exists.
- `create`: Create a new sensor record.
- `insert`: Insert a list of sensor records into the database.
- `get`: Retrieve a sensor record by its parameters.
- `get_by_id`: Retrieve a sensor record by its ID.
- `get_all`: Retrieve all sensor records.
- `search`: Search for sensor records based on various criteria.
- `filter`: Filter sensor records based on custom logic.
- `update`: Update the details of a sensor record.
- `delete`: Delete a sensor record.
- `refresh`: Refresh the sensor record's data from the database.
- `get_info`: Get the additional information of the sensor record.
- `set_info`: Set the additional information of the sensor record.
- File handling methods from FileHandlerMixin for managing record files.

"""

from typing import Optional, List, Generator
import os, mimetypes
from tqdm import tqdm   
from uuid import UUID

import logging
from gemini.api.types import ID
from pydantic import Field, AliasChoices
from gemini.api.base import APIBase, FileHandlerMixin
from gemini.db.models.columnar.sensor_records import SensorRecordModel
from gemini.db.models.views.sensor_records_immv import SensorRecordsIMMVModel

from datetime import date, datetime

logger = logging.getLogger(__name__)

class SensorRecord(APIBase, FileHandlerMixin):
    """
    Represents a record of sensor data, including metadata, associations to datasets, experiments, sites, seasons, and plots, and file handling capabilities.

    Attributes:
        id (Optional[ID]): The unique identifier of the sensor record.
        timestamp (Optional[datetime]): The timestamp of the record.
        collection_date (Optional[date]): The collection date of the record.
        dataset_id (Optional[ID]): The ID of the associated dataset.
        dataset_name (Optional[str]): The name of the associated dataset.
        sensor_id (Optional[ID]): The ID of the associated sensor.
        sensor_name (Optional[str]): The name of the associated sensor.
        sensor_data (Optional[dict]): The data content of the sensor record.
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
        record_file (Optional[str]): The file path or URI of the record file.
        record_info (Optional[dict]): Additional information about the record.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "sensor_record_id"))

    timestamp: Optional[datetime] = None
    collection_date: Optional[date] = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    sensor_id: Optional[ID] = None
    sensor_name: Optional[str] = None
    sensor_data: Optional[dict] = None
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
    record_file: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the SensorRecord object."""
        return f"SensorRecord(id={self.id}, timestamp={self.timestamp}, sensor_name={self.sensor_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name}, plot_number={self.plot_number})"
    
    def __repr__(self):
        """Return a detailed string representation of the SensorRecord object."""
        return f"SensorRecord(id={self.id}, timestamp={self.timestamp}, sensor_name={self.sensor_name}, dataset_name={self.dataset_name}, experiment_name={self.experiment_name}, site_name={self.site_name}, season_name={self.season_name}, plot_number={self.plot_number})"
    
    @classmethod
    def exists(
        cls,
        timestamp: datetime,
        sensor_name: str,
        dataset_name: str,
        experiment_name: str,
        season_name: str,
        site_name: str,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> bool:
        """
        Check if a sensor record with the given parameters exists.

        Examples:
            >>> SensorRecord.exists(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     sensor_name="TemperatureSensor",
            ...     dataset_name="WeatherData",
            ...     experiment_name="ClimateExperiment",
            ...     season_name="Autumn",
            ...     site_name="SiteA",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1
            ... )
            True


        Args:
            timestamp (datetime): The timestamp of the record.
            sensor_name (str): The name of the sensor.
            dataset_name (str): The name of the dataset.
            experiment_name (str): The name of the experiment.
            season_name (str): The name of the season.
            site_name (str): The name of the site.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            bool: True if the sensor record exists, False otherwise.
        """
        try:
            exists = SensorRecordModel.exists(
                timestamp=timestamp,
                sensor_name=sensor_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of sensor record: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        timestamp: datetime = datetime.now(),
        collection_date: date = None,
        dataset_name: str = None,
        sensor_name: str = None,
        sensor_data: dict = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        record_file: str = None,
        record_info: dict = None,
        insert_on_create: bool = True
    ) -> Optional["SensorRecord"]:
        """
        Create a new sensor record.

        Examples:
            >>> sensor_record = SensorRecord.create(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="WeatherData",
            ...     sensor_name="TemperatureSensor",
            ...     sensor_data={"temperature": 22.5},
            ...     experiment_name="ClimateExperiment",
            ...     site_name="SiteA",
            ...     season_name="Autumn",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_file="/path/to/record/file.txt",
            ...     record_info={"notes": "Initial record"},
            ...     insert_on_create=True
            ... )
            >>> print(sensor_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            timestamp (datetime, optional): The timestamp of the record. Defaults to now.
            collection_date (date, optional): The collection date. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            sensor_name (str, optional): The name of the sensor. Defaults to None.
            sensor_data (dict, optional): The data content. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            record_file (str, optional): The file path or URI. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to {{}}.
            insert_on_create (bool, optional): Whether to insert on create. Defaults to True.
        Returns:
            Optional[SensorRecord]: The created sensor record, or None if an error occurred.
        """
        try:
            if not any([experiment_name, season_name, site_name]):
                raise ValueError("At least one of experiment_name, season_name, or site_name must be provided.")
            if not sensor_name:
                raise ValueError("Sensor name is required.")
            if not dataset_name:
                raise ValueError("Dataset name is required.")
            if not all([plot_number, plot_row_number, plot_column_number]):
                raise ValueError("Plot number, plot row number, and plot column number are required if a plot is specified.")
            if not timestamp:
                timestamp = datetime.now()
            if not collection_date:
                collection_date = timestamp.date()
            if not sensor_data and not record_file:
                raise ValueError("Either sensor_data or record_file must be provided.")
            sensor_record = SensorRecord(
                timestamp=timestamp,
                collection_date=collection_date,
                dataset_name=dataset_name,
                sensor_name=sensor_name,
                sensor_data=sensor_data,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                record_file=record_file,
                record_info=record_info
            )
            if insert_on_create:
                insert_success, inserted_record_ids = cls.insert([sensor_record])
                if not insert_success:
                    logger.info("Failed to insert SensorRecord.")
                    return None
                if not inserted_record_ids or len(inserted_record_ids) == 0:
                    logger.info("No new SensorRecord was inserted.")
                    return None
                inserted_record_id = inserted_record_ids[0]
                sensor_record = cls.get_by_id(inserted_record_id)
            return sensor_record    
        except Exception as e:
            logger.error(f"Error creating sensor record: {e}")
            return None
    
    @classmethod
    def insert(cls, records: List["SensorRecord"]) -> tuple[bool, List[str]]:
        """
        Insert a list of sensor records into the database.

        Args:
            records (List[SensorRecord]): The records to insert.
        Returns:
            tuple[bool, List[str]]: Success status and list of inserted record IDs.
        """
        try:
            if not records or len(records) == 0:
                raise ValueError("No records provided for insertion.")
                return False, []
            records = [cls.process_record(record) for record in tqdm(records, desc="Processing Records for Sensor: " + records[0].sensor_name)]
            records_to_insert = []
            for record in records:
                record_to_insert = record.model_dump()
                record_to_insert = {k: v for k, v in record_to_insert.items() if v is not None}
                records_to_insert.append(record_to_insert)
            logger.info(f"Inserting {len(records_to_insert)} records.")
            inserted_record_ids = SensorRecordModel.insert_bulk('sensor_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_record_ids)} records.")
            return True, inserted_record_ids
        except Exception as e:
            logger.error(f"Error inserting records: {e}")
            return False, []
        
    @classmethod
    def get(
        cls,
        timestamp: datetime,
        sensor_name: str,
        dataset_name: str,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> Optional["SensorRecord"]:
        """
        Retrieve a sensor record by its parameters.

        Examples:
            >>> sensor_record = SensorRecord.get(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     sensor_name="TemperatureSensor",
            ...     dataset_name="WeatherData",
            ...     experiment_name="ClimateExperiment",
            ...     site_name="SiteA",
            ...     season_name="Autumn",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1
            ... )
            >>> print(sensor_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            timestamp (datetime): The timestamp of the record.
            sensor_name (str): The name of the sensor.
            dataset_name (str): The name of the dataset.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            Optional[SensorRecord]: The sensor record, or None if not found.
        """
        try:
            if not timestamp:
                logger.warning("Timestamp is required to get a sensor record.")
                return None
            if not dataset_name:
                logger.warning("Dataset name is required to get a sensor record.")
                return None
            if not sensor_name:
                logger.warning("Sensor name is required to get a sensor record.")
                return None
            if not experiment_name and not site_name and not season_name:
                logger.warning("At least one of experiment_name, site_name, or season_name is required to get a sensor record.")
                return None
            if not all([plot_number, plot_row_number, plot_column_number]):
                logger.info("Plot number, plot row number, and plot column number are required if a plot is specified.")
                return None
            sensor_record = SensorRecordsIMMVModel.get_by_parameters(
                timestamp=timestamp,
                sensor_name=sensor_name,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                site_name=site_name,
                season_name=season_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            if not sensor_record:
                logger.info("No sensor record found with the provided parameters.")
                return None
            sensor_record = cls.model_validate(sensor_record)
            return sensor_record
        except Exception as e:
            logger.error(f"Error getting sensor record: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["SensorRecord"]:
        """
        Retrieve a sensor record by its ID.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> print(sensor_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            id (UUID | int | str): The ID of the sensor record.
        Returns:
            Optional[SensorRecord]: The sensor record, or None if not found.
        """
        try:
            db_instance = SensorRecordModel.get(id)
            if not db_instance:
                logger.info(f"No sensor record found with ID: {id}")
                return None
            record = cls.model_validate(db_instance)
            return record
        except Exception as e:
            logger.error(f"Error getting sensor record by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["SensorRecord"]]:
        """
        Retrieve all sensor records, up to a specified limit.

        Examples:
            >>> sensor_records = SensorRecord.get_all(limit=10)
            >>> for record in sensor_records:
            ...     print(record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='HumiditySensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteB', season_name='Winter', plot_number=2)

        Args:
            limit (int, optional): The maximum number of records to retrieve. Defaults to 100.
        Returns:
            Optional[List[SensorRecord]]: List of sensor records, or None if not found.
        """
        try:
            records = SensorRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                logger.info("No sensor records found.")
                return None
            records = [cls.model_validate(record) for record in records]
            return records
        except Exception as e:
            logger.error(f"Error getting all sensor records: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        sensor_name: str = None,
        sensor_data: dict = None,
        dataset_name: str = None,
        experiment_name: str = None,
        site_name: str = None,
        season_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        collection_date: date = None,
        record_info: dict = None
    ) -> Generator["SensorRecord", None, None]:
        """
        Search for sensor records based on various criteria.

        Examples:
            >>> sensor_records = SensorRecord.search(
            ...     sensor_name="TemperatureSensor",
            ...     dataset_name="WeatherData",
            ...     experiment_name="ClimateExperiment",
            ...     site_name="SiteA",
            ...     season_name="Autumn",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     collection_date=date(2023, 10, 1),
            ...     record_info={"notes": "Initial record"}
            ... )
            >>> for record in sensor_records:
            ...     print(record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            sensor_name (str, optional): The name of the sensor. Defaults to None.
            sensor_data (dict, optional): The data content. Defaults to None.
            dataset_name (str, optional): The name of the dataset. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            collection_date (date, optional): The collection date. Defaults to None.
            record_info (dict, optional): Additional info. Defaults to None.
        Yields:
            SensorRecord: Matching sensor records.
        """
        try:
            if not any([sensor_name, dataset_name, experiment_name, site_name, season_name, plot_number, plot_row_number, plot_column_number]):
                logger.warning("At least one search parameter must be provided.")
                return
            records = SensorRecordsIMMVModel.stream(
                sensor_name=sensor_name,
                sensor_data=sensor_data,
                dataset_name=dataset_name,
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
            logger.error(f"Error searching sensor records: {e}")
            yield from []

    @classmethod
    def filter(
        cls,
        start_timestamp: datetime = None,
        end_timestamp: datetime = None,
        sensor_names: List[str] = None,
        dataset_names: List[str] = None,
        experiment_names: List[str] = None,
        season_names: List[str] = None,
        site_names: List[str] = None
    ) -> Generator["SensorRecord", None, None]:
        """
        Filter sensor records based on custom logic.

        Examples:
            >>> sensor_records = SensorRecord.filter(
            ...     start_timestamp=datetime(2023, 10, 1, 0, 0, 0),
            ...     end_timestamp=datetime(2023, 10, 31, 23, 59, 59),
            ...     sensor_names=["TemperatureSensor", "HumiditySensor"],
            ...     dataset_names=["WeatherData"],
            ...     experiment_names=["ClimateExperiment"],
            ...     site_names=["SiteA", "SiteB"],
            ...     season_names=["Autumn"]
            ... )
            >>> for record in sensor_records:
            ...     print(record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 2, 12, 0), sensor_name='HumiditySensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteB', season_name='Autumn', plot_number=2)

        Args:
            start_timestamp (datetime, optional): Start of timestamp range. Defaults to None.
            end_timestamp (datetime, optional): End of timestamp range. Defaults to None.
            sensor_names (List[str], optional): List of sensor names. Defaults to None.
            dataset_names (List[str], optional): List of dataset names. Defaults to None.
            experiment_names (List[str], optional): List of experiment names. Defaults to None.
            season_names (List[str], optional): List of season names. Defaults to None.
            site_names (List[str], optional): List of site names. Defaults to None.
        Yields:
            SensorRecord: Filtered sensor records.
        """
        try:
            records = SensorRecordModel.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                sensor_names=sensor_names,
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                site_names=site_names,
                season_names=season_names
            )
            for record in records:
                record = cls.model_validate(record)
                yield record
        except Exception as e:
            logger.error(f"Error filtering sensor records: {e}")
            yield from []
    

    def update(
        self,
        sensor_data: dict = None,
        record_info: dict = None
    ) -> Optional["SensorRecord"]:
        """
        Update the details of the sensor record.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> updated_record = sensor_record.update(
            ...     sensor_data={"temperature": 23.0},
            ...     record_info={"notes": "Updated record"}
            ... )
            >>> print(updated_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            sensor_data (dict, optional): The new sensor data. Defaults to None.
            record_info (dict, optional): The new record information. Defaults to None.
        Returns:
            Optional[SensorRecord]: The updated sensor record, or None if an error occurred.
        """
        try:
            if not any([sensor_data, record_info]):
                logger.warning("At least one update parameter must be provided.")
                return None
            current_id = self.id
            sensor_record = SensorRecordModel.get(current_id)
            if not sensor_record:
                logger.info(f"No sensor record found with ID: {current_id}")
                return None
            sensor_record = SensorRecordModel.update(
                sensor_record,
                sensor_data=sensor_data,
                record_info=record_info
            )
            sensor_record = self.model_validate(sensor_record)
            self.refresh()
            return sensor_record
        except Exception as e:
            logger.error(f"Error updating sensor record: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the sensor record.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> success = sensor_record.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the sensor record was deleted, False otherwise.
        """
        try:
            current_id = self.id
            sensor_record = SensorRecordModel.get(current_id)
            if not sensor_record:
                logger.info(f"No sensor record found with ID: {current_id}")
                return False
            SensorRecordModel.delete(sensor_record)
            return True
        except Exception as e:
            logger.error(f"Error deleting sensor record: {e}")
            return False
        
    def refresh(self) -> Optional["SensorRecord"]:
        """
        Refresh the sensor record's data from the database.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> refreshed_record = sensor_record.refresh()
            >>> print(refreshed_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Returns:
            Optional[SensorRecord]: The refreshed sensor record, or None if an error occurred.
        """
        try:
            db_instance = SensorRecordModel.get(self.id)
            if not db_instance:
                logger.debug(f"SensorRecord with id {self.id} not found.")
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing SensorRecord: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the sensor record.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> record_info = sensor_record.get_info()
            >>> print(record_info)
            {'notes': 'Initial record', 'created_by': 'user123'}

        Returns:
            Optional[dict]: The record's info, or None if not found.
        """
        try:
            current_id = self.id
            sensor_record = SensorRecordModel.get(current_id)
            if not sensor_record:
                logger.info(f"No sensor record found with ID: {current_id}")
                return None
            record_info = sensor_record.record_info
            if not record_info:
                logger.info("No record info available for this sensor record.")
                return None
            return record_info
        except Exception as e:
            logger.error(f"Error getting sensor record info: {e}")
            return None
            

    def set_info(self, record_info: dict) -> Optional["SensorRecord"]:
        """
        Set the additional information of the sensor record.

        Examples:
            >>> sensor_record = SensorRecord.get_by_id(UUID('...'))
            >>> updated_record = sensor_record.set_info(
            ...     record_info={"notes": "Updated record", "created_by": "user123"}
            ... )
            >>> print(updated_record.get_info())
            {'notes': 'Updated record', 'created_by': 'user123'}

        Args:
            record_info (dict): The new information to set.
        Returns:
            Optional[SensorRecord]: The updated sensor record, or None if an error occurred.
        """
        try:
            current_id = self.id
            sensor_record = SensorRecordModel.get(current_id)
            if not sensor_record:
                logger.info(f"No sensor record found with ID: {current_id}")
                return None
            SensorRecordModel.update(
                sensor_record,
                record_info=record_info
            )
            sensor_record = self.model_validate(sensor_record)
            self.refresh()
            return sensor_record
        except Exception as e:
            logger.error(f"Error setting sensor record info: {e}")
            return None
    
    @classmethod
    def create_file_uri(cls, record: "SensorRecord") -> Optional[str]:
        """
        Create a file URI for the given sensor record.

        Examples:
            >>> record = SensorRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="WeatherData",
            ...     sensor_name="TemperatureSensor",
            ...     experiment_name="ClimateExperiment",
            ...     site_name="SiteA",
            ...     season_name="Autumn",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_file="/path/to/record/file.txt"
            ... )
            >>> file_uri = SensorRecord.create_file_uri(record)
            >>> print(file_uri)
            sensor_data/ClimateExperiment/TemperatureSensor/WeatherData/2023-10-01/SiteA/Autumn/1706467200000.txt

        Args:
            record (SensorRecord): The sensor record for which to create the file URI.
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
            sensor_name = record.sensor_name
            dataset_name = record.dataset_name
            experiment_name = record.experiment_name
            season_name = record.season_name
            site_name = record.site_name
            file_extension = os.path.splitext(original_file_path)[1]
            file_timestamp = str(int(record.timestamp.timestamp() * 1000))
            file_key = f"sensor_data/{experiment_name}/{sensor_name}/{dataset_name}/{collection_date}/{site_name}/{season_name}/{file_timestamp}{file_extension}"
            return file_key
        except Exception as e:
            logger.error(f"Error creating file URI: {e}")
            return None


    @classmethod
    def process_record(cls, record: "SensorRecord") -> "SensorRecord":
        """
        Process a sensor record (custom logic, e.g., file upload).

        Examples:
            >>> record = SensorRecord(
            ...     timestamp=datetime(2023, 10, 1, 12, 0, 0),
            ...     collection_date=date(2023, 10, 1),
            ...     dataset_name="WeatherData",
            ...     sensor_name="TemperatureSensor",
            ...     experiment_name="ClimateExperiment",
            ...     site_name="SiteA",
            ...     season_name="Autumn",
            ...     plot_number=1,
            ...     plot_row_number=1,
            ...     plot_column_number=1,
            ...     record_file="/path/to/record/file.txt"
            ... )
            >>> processed_record = SensorRecord.process_record(record)
            >>> print(processed_record)
            SensorRecord(id=UUID('...'), timestamp=datetime(2023, 10, 1, 12, 0), sensor_name='TemperatureSensor', dataset_name='WeatherData', experiment_name='ClimateExperiment', site_name='SiteA', season_name='Autumn', plot_number=1)

        Args:
            record (SensorRecord): The sensor record to process.
        Returns:
            SensorRecord: The processed sensor record.
        """
        try:
            file = record.record_file
            if not file:
                logger.warning(f"record_file is required to process SensorRecord.")
                return record
            file_key = cls.create_file_uri(record)
            if not file_key:
                logger.info(f"Failed to create file URI for SensorRecord: {record}")
                return record
            content_type, _ = mimetypes.guess_type(file)
            # Generate Metadata for upload
            file_metadata = {
                "Sensor-Name": record.sensor_name,
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
            logger.error(f"Error processing SensorRecord: {e}")
            return record