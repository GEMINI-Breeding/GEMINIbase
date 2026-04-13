"""
SQLAlchemy model for GenotypingStudy entities in the GEMINI database.

A GenotypingStudy represents a genotyping protocol or run (e.g. a SNP array
run, RNA-seq, whole genome sequencing). Individual allele calls are stored
in GenotypeRecordModel, which references this table via study_id.
"""

from sqlalchemy import String, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class GenotypingStudyModel(BaseModel):
    """
    Represents a genotyping study or protocol in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the genotyping study.
        study_name (str): The name of the genotyping study/protocol.
        study_info (dict): Additional JSONB data (reference genome, platform, methodology, etc.).
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "genotyping_studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    study_name: Mapped[str] = mapped_column(String(255), nullable=False)
    study_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('study_name', name='genotyping_study_unique'),
        Index('idx_genotyping_studies_info', 'study_info', postgresql_using='GIN'),
    )
