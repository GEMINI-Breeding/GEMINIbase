"""
SQLAlchemy model for Line entities in the GEMINIbase database.

A Line represents a breeding-line pedigree anchor (e.g. an inbred line,
a clonal parent). Accessions are derived from a Line via accessions.line_id.
"""

from sqlalchemy import String, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class LineModel(BaseModel):
    """
    Represents a breeding line in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the line.
        line_name (str): The globally-unique name of the line.
        species (str): The species of the line (e.g. "Zea mays").
        line_info (dict): Additional JSONB data for the line (synonyms, pedigree notes, release status).
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    line_name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str] = mapped_column(String(255), default="")
    line_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('line_name', name='line_unique'),
        Index('idx_lines_info', 'line_info', postgresql_using='GIN'),
    )
