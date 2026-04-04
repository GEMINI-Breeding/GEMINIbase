"""
SQLAlchemy model for Plant entities in the GEMINI database.
"""

from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel
from datetime import datetime
import uuid


class PlantModel(BaseModel):
    """
    Represents a plant in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the plant.
        plot_id (uuid.UUID): Foreign key referencing the plot where the plant is located.
        plant_number (int): The number of the plant within the plot.
        plant_info (dict): Additional JSONB data for the plant.
        population_id (uuid.UUID): Foreign key referencing the population of the plant.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "plants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    plot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gemini.plots.id"))
    plant_number: Mapped[int] = mapped_column(Integer)
    plant_info: Mapped[dict] = mapped_column(JSONB, default={})
    population_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gemini.populations.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("plot_id", "plant_number"),
        Index("idx_plants_info", "plant_info", postgresql_using="GIN"),
    )
