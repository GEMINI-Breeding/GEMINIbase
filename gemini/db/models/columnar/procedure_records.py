"""
SQLAlchemy model for columnar ProcedureRecord entities in the GEMINIbase database.
"""

from sqlalchemy.orm import relationship, mapped_column, Mapped, Relationship
from sqlalchemy import (
    UUID,
    JSON,
    String,
    Integer,
    UniqueConstraint,
    Index,
    ForeignKey,
    TIMESTAMP,
    DATE,
    delete as sa_delete,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text, bindparam
from gemini.db.core.base import ColumnarBaseModel, db_engine
import uuid
from datetime import datetime, date
from typing import Optional, List


class ProcedureRecordModel(ColumnarBaseModel):
    """
    Represents a procedure record in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the procedure record.
        timestamp (datetime): Timestamp of the record.
        collection_date (date): The date when the data was collected.
        dataset_id (UUID): Foreign key referencing the dataset.
        dataset_name (str): The name of the dataset.
        procedure_id (UUID): Foreign key referencing the procedure.
        procedure_name (str): The name of the procedure.
        procedure_data (dict): Additional JSONB data for the procedure.
        experiment_id (UUID): Foreign key referencing the experiment.
        experiment_name (str): The name of the experiment.
        season_id (UUID): Foreign key referencing the season.
        season_name (str): The name of the season.
        site_id (UUID): Foreign key referencing the site.
        site_name (str): The name of the site.
        record_file (str): The file where the record is stored.
        record_info (dict): Additional JSONB data for the record.
    """

    __tablename__ = "procedure_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    collection_date: Mapped[date] = mapped_column(DATE, nullable=False)
    dataset_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    dataset_name: Mapped[str] = mapped_column(String(255))
    procedure_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    procedure_name: Mapped[str] = mapped_column(String(255))
    procedure_data : Mapped[dict] = mapped_column(JSONB)
    experiment_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    experiment_name: Mapped[str] = mapped_column(String(255))
    season_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    season_name: Mapped[str] = mapped_column(String(255))
    site_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    site_name: Mapped[str] = mapped_column(String(255))
    record_file : Mapped[str] = mapped_column(String(255))
    record_info: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            'timestamp',
            'collection_date', 
            'procedure_id', 
            'procedure_name', 
            'dataset_id',
            'dataset_name', 
            'experiment_id',
            'experiment_name', 
            'season_id', 
            'season_name',
            'site_id',
            'site_name',
            name='procedure_records_unique'
        ),
        Index('idx_procedure_records_record_info', 'record_info', postgresql_using='GIN'),
    )

    @classmethod
    def filter_records(
        cls,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        procedure_names: Optional[List[str]] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ):
        stmt = text(
            """
            SELECT * FROM gemini.filter_procedure_records(
                p_start_timestamp => :start_timestamp,
                p_end_timestamp => :end_timestamp,
                p_procedure_names => :procedure_names,
                p_dataset_names => :dataset_names,
                p_experiment_names => :experiment_names,
                p_season_names => :season_names,
                p_site_names => :site_names
            )
            """
        ).bindparams(
            bindparam('start_timestamp', value=start_timestamp),
            bindparam('end_timestamp', value=end_timestamp),
            bindparam('procedure_names', value=procedure_names),
            bindparam('dataset_names', value=dataset_names),
            bindparam('experiment_names', value=experiment_names),
            bindparam('season_names', value=season_names),
            bindparam('site_names', value=site_names)
        )
        with db_engine.get_session() as session:
            result = session.execute(stmt, execution_options={"yield_per": 1000})
            for record in result:
                yield record

    # See `trait_records._bulk_delete_in_session` for the rationale —
    # this mirrors the pg_ivm-aware bulk-delete pattern, with the
    # procedure_records table + its IMMV.
    @classmethod
    def _bulk_delete_in_session(cls, session, column_name: str, value: str) -> int:
        session.execute(text("SET LOCAL session_replication_role = 'replica'"))
        try:
            base_col = cls.__table__.c[column_name]
            result = session.execute(
                sa_delete(cls.__table__).where(base_col == value)
            )
            session.execute(
                text(
                    f"DELETE FROM gemini.procedure_records_immv "
                    f"WHERE {column_name} = :value"
                ),
                {"value": value},
            )
            return result.rowcount
        finally:
            session.execute(text("SET LOCAL session_replication_role = 'origin'"))

    @classmethod
    def _bulk_delete(cls, column_name: str, value: str, session=None) -> int:
        if session is not None:
            return cls._bulk_delete_in_session(session, column_name, value)
        with db_engine.get_session() as s:
            return cls._bulk_delete_in_session(s, column_name, value)

    @classmethod
    def delete_by_procedure(cls, procedure_name: str, session=None) -> int:
        return cls._bulk_delete("procedure_name", procedure_name, session=session)

    @classmethod
    def delete_by_experiment(cls, experiment_name: str, session=None) -> int:
        return cls._bulk_delete("experiment_name", experiment_name, session=session)

    @classmethod
    def delete_by_dataset(cls, dataset_name: str, session=None) -> int:
        return cls._bulk_delete("dataset_name", dataset_name, session=session)
