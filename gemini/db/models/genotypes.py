"""
SQLAlchemy model for Genotype (genotyping study/protocol) entities in the GEMINI database.
"""

from sqlalchemy import String, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class GenotypeModel(BaseModel):
    """
    Represents a genotyping study or protocol in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the genotype study.
        genotype_name (str): The name of the genotyping study/protocol.
        genotype_info (dict): Additional JSONB data (reference genome, platform, methodology, etc.).
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "genotypes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    genotype_name: Mapped[str] = mapped_column(String(255), nullable=False)
    genotype_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('genotype_name'),
        Index('idx_genotypes_info', 'genotype_info', postgresql_using='GIN'),
    )
