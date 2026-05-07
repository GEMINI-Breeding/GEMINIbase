"""
SQLAlchemy model for the study-scoped sample catalog (Phase 9d').

One row per (study, accession) records which accessions appear in this
study's .psam and at what 0-based ordinal. Used by GWAS to align
phenotype rows to PGEN columns.
"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gemini.db.core.base import BaseModel


class GenotypingStudySampleModel(BaseModel):
    """Study↔accession ↔ PSAM ordinal mapping."""

    __tablename__ = "genotyping_study_samples"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
        nullable=False,
    )
    accession_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.accessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("study_id", "accession_id"),
        Index(
            "idx_genotyping_study_samples_ordinal",
            "study_id",
            "sample_index",
            unique=True,
        ),
    )
