"""
SQLAlchemy model for Population entities in the GEMINI database.

A Population is a named germplasm grouping within a breeding program
(e.g. a diversity panel, RIL population, NAM population). Populations
contain Accessions via the population_accessions join table.
"""

from sqlalchemy import String, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class PopulationModel(BaseModel):
    """
    Represents a population in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the population.
        population_name (str): The globally-unique name of the population.
        population_type (str): The type of population (e.g. diversity_panel, ril, nam, biparental, breeding_pop).
        species (str): The species of the population (e.g. "Zea mays").
        population_info (dict): Additional JSONB data for the population.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "populations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    population_name: Mapped[str] = mapped_column(String(255), nullable=False)
    population_type: Mapped[str] = mapped_column(String(64), default="")
    species: Mapped[str] = mapped_column(String(255), default="")
    population_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('population_name', name='population_unique'),
        Index('idx_populations_info', 'population_info', postgresql_using='GIN'),
    )
