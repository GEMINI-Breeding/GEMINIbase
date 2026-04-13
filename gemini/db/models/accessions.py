"""
SQLAlchemy model for Accession entities in the GEMINI database.

An Accession is a canonical germplasm unit (variety, clone, inbred line
entry) that gets planted in plots. Accession names are globally unique.
Accessions belong to one or more Populations via population_accessions,
and may optionally reference a Line via line_id.
"""

from sqlalchemy import String, TIMESTAMP, UniqueConstraint, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class AccessionModel(BaseModel):
    """
    Represents an accession (germplasm unit) in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the accession.
        accession_name (str): The globally-unique name of the accession (e.g. PI number, clone ID).
        line_id (uuid.UUID): Optional FK to the breeding line this accession derives from.
        species (str): The species of the accession (e.g. "Zea mays").
        accession_info (dict): Additional JSONB data (synonyms, passport data, release status).
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "accessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    accession_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gemini.lines.id"), nullable=True)
    species: Mapped[str] = mapped_column(String(255), default="")
    accession_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('accession_name', name='accession_unique'),
        Index('idx_accessions_info', 'accession_info', postgresql_using='GIN'),
    )
