"""
SQLAlchemy model for columnar DatasetRecord entities in the GEMINIbase database.
"""

from sqlalchemy.orm import relationship, mapped_column, Mapped, Relationship
from sqlalchemy import UUID, JSON, String, Integer, UniqueConstraint, Index, ForeignKey, TIMESTAMP, DATE
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text, bindparam
from gemini.db.core.base import ColumnarBaseModel, db_engine
import uuid
from datetime import datetime, date
from typing import Optional, List


class DatasetRecordModel(ColumnarBaseModel):
    """
    Represents a dataset record in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the dataset record.
        timestamp (datetime): Timestamp of the record.
        collection_date (date): The date when the data was collected.
        dataset_id (UUID): Foreign key referencing the dataset.
        dataset_name (str): The name of the dataset.
        dataset_data (dict): Additional JSONB data for the dataset.
        experiment_id (UUID): Foreign key referencing the experiment.
        experiment_name (str): The name of the experiment.
        season_id (UUID): Foreign key referencing the season.
        season_name (str): The name of the season.
        site_id (UUID): Foreign key referencing the site.
        site_name (str): The name of the site.
        record_file (str): The file where the record is stored.
        record_info (dict): Additional JSONB data for the record.
    """
    __tablename__ = "dataset_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    collection_date: Mapped[date] = mapped_column(DATE, nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    dataset_name: Mapped[str] = mapped_column(String(255))
    dataset_data : Mapped[dict] = mapped_column(JSONB)
    experiment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    experiment_name: Mapped[str] = mapped_column(String(255))
    season_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    season_name: Mapped[str] = mapped_column(String(255))
    site_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    site_name: Mapped[str] = mapped_column(String(255))
    record_file: Mapped[str] = mapped_column(String(255))
    record_info: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            'timestamp',
            'collection_date',
            'dataset_id',
            'dataset_name',
            'experiment_id',
            'experiment_name',
            'season_id',
            'season_name',
            'site_id',
            'site_name',
            name='dataset_records_unique'
        ),
        Index('idx_dataset_records_record_info', 'record_info', postgresql_using='GIN'),
    )

    @classmethod
    def filter_records(
        cls,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ):
        """
        Filters dataset records based on the provided parameters.

        Args:
            start_timestamp (Optional[datetime]): The starting timestamp for the filter.
            end_timestamp (Optional[datetime]): The ending timestamp for the filter.
            dataset_names (Optional[List[str]]): A list of dataset names to filter by.
            experiment_names (Optional[List[str]]): A list of experiment names to filter by.
            season_names (Optional[List[str]]): A list of season names to filter by.
            site_names (Optional[List[str]]): A list of site names to filter by.

        Yields:
            record: Matching dataset records.
        """
        stmt = text(
            """
            SELECT * FROM gemini.filter_dataset_records(
                p_start_timestamp => :start_timestamp,
                p_end_timestamp => :end_timestamp,
                p_dataset_names => :dataset_names,
                p_experiment_names => :experiment_names,
                p_season_names => :season_names,
                p_site_names => :site_names
            )
            """
        ).bindparams(
            bindparam('start_timestamp', value=start_timestamp),
            bindparam('end_timestamp', value=end_timestamp),
            bindparam('dataset_names', value=dataset_names),
            bindparam('experiment_names', value=experiment_names),
            bindparam('season_names', value=season_names),
            bindparam('site_names', value=site_names)
        )
        with db_engine.get_session() as session:
            result = session.execute(stmt, execution_options={"yield_per": 1000})
            for record in result:
                yield record
