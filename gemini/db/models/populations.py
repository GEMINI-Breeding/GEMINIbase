"""
SQLAlchemy model for Population entities in the GEMINI database.
"""

from sqlalchemy import JSON, String, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class PopulationModel(BaseModel):
    """
    Represents a population in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the population.
        population_accession (str): The accession identifier for the population.
        population_name (str): The population name of the population.
        population_info (dict): Additional JSONB data for the population.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "populations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    population_accession: Mapped[str] = mapped_column(String(255), nullable=False)
    population_name: Mapped[str] = mapped_column(String(255), nullable=False)
    population_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('population_accession', 'population_name'),
        Index('idx_populations_info', 'population_info', postgresql_using='GIN')
    )
