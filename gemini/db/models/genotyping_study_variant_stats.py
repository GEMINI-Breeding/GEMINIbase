"""
SQLAlchemy model for pre-computed per-variant analytics (Phase 9d').

Computed at ingest from the PGEN by a single bcftools / DuckDB pass so
the variant browser can show MAF / missing / HWE without cracking the
PGEN file at query time. Small (one row per variant per study), heap
storage, indexed by primary key.
"""
import uuid

from sqlalchemy import Float, ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gemini.db.core.base import BaseModel


class GenotypingStudyVariantStatsModel(BaseModel):
    """Per-variant precomputed statistics for a study."""

    __tablename__ = "genotyping_study_variant_stats"

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
    n_called: Mapped[int | None] = mapped_column(Integer)
    n_missing: Mapped[int | None] = mapped_column(Integer)
    maf: Mapped[float | None] = mapped_column(Float)
    hwe_p: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        PrimaryKeyConstraint("study_id", "variant_id"),
    )
