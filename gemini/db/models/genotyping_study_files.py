"""
SQLAlchemy model for the per-study file-pointer table that backs the
PGEN-in-MinIO architecture.

For every genotyping study, the wizard's ingest endpoint writes a small
fixed set of artefacts to MinIO (PGEN + sidecars + per-variant stats
parquet) and records one row here per artefact. Read paths look up the
``s3_uri`` to stream the file out (export) or hand a presigned URL to a
worker (GWAS).
"""
from datetime import datetime
import uuid

from sqlalchemy import BigInteger, ForeignKey, PrimaryKeyConstraint, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gemini.db.core.base import BaseModel


# Allowed values for ``file_kind``. Validated by the application; not a
# DB CHECK so the set can grow without a migration.
ALLOWED_FILE_KINDS = (
    "pgen",       # PLINK2 packed genotype matrix (canonical)
    "pvar",       # PLINK2 variant metadata sidecar
    "psam",       # PLINK2 sample metadata sidecar
    "bcf",        # bcftools binary VCF (region queries)
    "bcf_index",  # .csi for the bcf above
    "parquet",    # per-variant stats in Apache Parquet
    "manifest",   # JSON manifest summarizing the artefacts
    "source",     # original uploaded archive (xlsx/HapMap/VCF) for audit
)


class GenotypingStudyFileModel(BaseModel):
    """File pointer for one MinIO artefact backing a genotyping study."""

    __tablename__ = "genotyping_study_files"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_kind: Mapped[str] = mapped_column(Text, nullable=False)
    s3_uri: Mapped[str] = mapped_column(Text, nullable=False)
    bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now,
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("study_id", "file_kind"),
    )
