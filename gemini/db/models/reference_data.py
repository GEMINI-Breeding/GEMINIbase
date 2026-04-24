"""
SQLAlchemy models for reference-data uploads.

Reference data is breeder-supplied "ground truth" about plots: a CSV/Excel
file where each row is a plot and each column is either an identity field
(plot_id, col, row, accession) or a trait measurement. The dataset-level
metadata (experiment/location/population/date) comes from the upload form.

These tables are deliberately denormalized: `experiment`, `location`, and
`population` are free-text on the dataset rather than FKs, matching the
pre-migration FastAPI backend's semantics. Traits live in a JSONB column
on the plot row so different datasets can declare different trait columns
without a schema migration each time.
"""
from sqlalchemy import (
    String,
    TIMESTAMP,
    DATE,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from gemini.db.core.base import BaseModel

from datetime import datetime, date
import uuid


class ReferenceDatasetModel(BaseModel):
    """Dataset-level metadata for a reference-data upload."""

    __tablename__ = "reference_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    experiment: Mapped[str] = mapped_column(String(255), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    population: Mapped[str] = mapped_column(String(255), nullable=True)
    dataset_date: Mapped[date] = mapped_column(DATE, nullable=True)
    trait_columns: Mapped[list] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    dataset_info: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_reference_datasets_name", "name"),
        Index("idx_reference_datasets_experiment", "experiment"),
        Index("idx_reference_datasets_population", "population"),
    )


class ReferencePlotModel(BaseModel):
    """One plot (row) inside a reference dataset."""

    __tablename__ = "reference_plots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("gemini.reference_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    plot_id: Mapped[str] = mapped_column(String(255), nullable=True)
    plot_column: Mapped[str] = mapped_column(String(64), nullable=True)
    plot_row: Mapped[str] = mapped_column(String(64), nullable=True)
    accession: Mapped[str] = mapped_column(String(255), nullable=True)
    traits: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)

    __table_args__ = (
        Index("idx_reference_plots_dataset", "dataset_id"),
        Index("idx_reference_plots_plot_id", "plot_id"),
        Index("idx_reference_plots_accession", "accession"),
        Index("idx_reference_plots_traits", "traits", postgresql_using="GIN"),
    )
