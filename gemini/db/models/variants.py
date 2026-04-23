"""
SQLAlchemy model for Variant (marker/SNP) entities in the GEMINIbase database.
"""

from sqlalchemy import String, Text, Integer, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class VariantModel(BaseModel):
    """
    Represents a genetic variant (marker/SNP) in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the variant.
        variant_name (str): The name/identifier for the variant (e.g. "2_24641").
        chromosome (int): Chromosome number.
        position (float): Genetic map position in centiMorgans (cM).
        alleles (str): SNP alleles in "ref/alt" format (e.g. "T/C").
        design_sequence (str): Flanking sequence with variant marked (e.g. "...GACT[T/C]GAC...").
        variant_info (dict): Additional JSONB data for the variant.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    variant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chromosome: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[float] = mapped_column(nullable=False)
    alleles: Mapped[str] = mapped_column(String(50), nullable=False)
    design_sequence: Mapped[str] = mapped_column(Text, default='')
    variant_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('variant_name'),
        Index('idx_variants_info', 'variant_info', postgresql_using='GIN'),
        Index('idx_variants_chromosome', 'chromosome'),
    )
