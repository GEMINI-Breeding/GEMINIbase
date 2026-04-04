"""
SQLAlchemy model for Job entities in the GEMINI database.

Jobs represent long-running processing tasks (ML training, plant location,
trait extraction, stitching, ODM, drone processing, etc.) that are submitted
via the REST API and executed by worker services.
"""
from sqlalchemy import (
    String,
    TIMESTAMP,
    Float,
    Index,
)
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class JobModel(BaseModel):
    """
    Represents a processing job in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the job.
        job_type (str): Type of processing job (e.g. TRAIN_MODEL, LOCATE_PLANTS).
        status (str): Current status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED).
        progress (float): Progress percentage 0-100.
        progress_detail (dict): Detailed progress info (e.g. {epoch: 5, map: 0.82}).
        parameters (dict): Job input parameters.
        result (dict): Job output/result data.
        error_message (str): Error details if job failed.
        experiment_id (uuid.UUID): Associated experiment (optional).
        worker_id (str): ID of the worker processing this job.
        started_at (datetime): When the worker started processing.
        completed_at (datetime): When the job finished.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    progress_detail: Mapped[dict] = mapped_column(JSONB, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str] = mapped_column(String(2000), nullable=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), nullable=True)
    worker_id: Mapped[str] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_type", "job_type"),
        Index("idx_jobs_experiment", "experiment_id"),
        Index("idx_jobs_detail", "progress_detail", postgresql_using="GIN"),
    )
