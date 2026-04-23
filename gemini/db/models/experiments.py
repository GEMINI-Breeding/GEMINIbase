"""
SQLAlchemy model for Experiment entities in the GEMINIbase database.
"""
from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    CheckConstraint,
    Index,
    DATE,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime, date
import uuid


class ExperimentModel(BaseModel):
    """
    Represents an experiment in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the experiment.
        experiment_name (str): The name of the experiment.
        experiment_info (dict): Additional JSONB data for the experiment.
        experiment_start_date (date): The start date of the experiment.
        experiment_end_date (date): The end date of the experiment.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    experiment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    experiment_info: Mapped[dict] = mapped_column(JSONB, nullable=True)
    experiment_start_date: Mapped[date] = mapped_column(DATE, nullable=False, default=date.today)
    experiment_end_date: Mapped[date] = mapped_column(DATE, nullable=False, default=date.today)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("experiment_name"),
        CheckConstraint("experiment_start_date <= experiment_end_date"),
        CheckConstraint("experiment_end_date >= experiment_start_date"),
        Index("idx_experiments_info", "experiment_info", postgresql_using="GIN"),
    )
