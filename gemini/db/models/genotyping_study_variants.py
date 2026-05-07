"""
SQLAlchemy model for the study-scoped variant catalog (Phase 9d').

One row per (study, variant) records which variants live in this
study's PGEN file and at what 0-based ordinal. The ordinal index lets
detail endpoints slice the PGEN row directly without a sequential scan.
"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gemini.db.core.base import BaseModel


class GenotypingStudyVariantModel(BaseModel):
    """Study↔variant ↔ PGEN ordinal mapping."""

    __tablename__ = "genotyping_study_variants"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.variants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("study_id", "variant_id"),
        Index(
            "idx_genotyping_study_variants_ordinal",
            "study_id",
            "variant_index",
            unique=True,
        ),
    )
