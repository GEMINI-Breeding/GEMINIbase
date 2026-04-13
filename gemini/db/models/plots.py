"""
SQLAlchemy model for Plot entities in the GEMINI database.
"""

from sqlalchemy import (
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

import uuid
from datetime import datetime

class PlotModel(BaseModel):
  """
  Represents a plot in the GEMINI database.

  Attributes:
    id (uuid.UUID): Unique identifier for the plot.
    experiment_id (uuid.UUID): Foreign key referencing the experiment to which the plot belongs.
    season_id (uuid.UUID): Foreign key referencing the season during which the plot was used.
    site_id (uuid.UUID): Foreign key referencing the site where the plot is located.
    accession_id (uuid.UUID): Foreign key referencing the accession planted in this plot.
    population_id (uuid.UUID): Foreign key referencing the population this plot is enrolled in.
    plot_number (int): The number of the plot.
    plot_row_number (int): The row number of the plot in a grid layout.
    plot_column_number (int): The column number of the plot in a grid layout.
    plot_geometry_info (dict): Additional JSONB data describing the plot's geometry.
    plot_info (dict): Additional JSONB data for the plot.
    created_at (datetime): Timestamp when the record was created.
    updated_at (datetime): Timestamp when the record was last updated.
  """
  __tablename__ = 'plots'

  id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
  experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.experiments.id'))
  season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.seasons.id'))
  site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.sites.id'))
  accession_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.accessions.id'), nullable=True)
  population_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.populations.id'), nullable=True)
  plot_number: Mapped[int] = mapped_column(Integer)
  plot_row_number: Mapped[int] = mapped_column(Integer)
  plot_column_number: Mapped[int] = mapped_column(Integer)
  plot_geometry_info: Mapped[dict] = mapped_column(JSONB, default={})
  plot_info: Mapped[dict] = mapped_column(JSONB, default={})
  created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
  updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

  __table_args__ = (
    UniqueConstraint('experiment_id', 'season_id', 'site_id', 'plot_number', 'plot_row_number', 'plot_column_number'),
    Index('idx_plots_info', 'plot_info', postgresql_using='GIN'),
  )
