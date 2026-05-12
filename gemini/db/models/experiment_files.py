"""
SQLAlchemy model for the per-experiment MinIO file index.

Every chunked upload from the Files page lands at a deterministic
``Raw/{year}/{exp_name}/...`` path in MinIO, but until this table existed
the experiment row had no record of which objects were "its". The cascade
on experiment delete therefore had to guess the layout from the
experiment name alone, and got it wrong (it built ``Raw/{exp_name}/``
which never matches because the year sits between).

Each row here is the authoritative pointer from a Postgres-known
experiment to a MinIO object. Inserted at the moment the upload's
multipart-complete call succeeds. The FK with ``ON DELETE CASCADE``
makes the table itself self-cleaning when the experiment row goes; the
``Experiment.delete()`` cascade reads rows out *before* the delete and
removes the named MinIO objects.

Worker-written outputs (e.g. ``Processed/{year}/{exp_name}/``) and
record-level uploads (sensor/dataset/model/etc. record files,
genotyping_study_files) are NOT tracked here — they have their own
row-typed sources of truth, or they're sweepable by the year-prefix
backstop in the experiment cascade. This table is scoped to the
"chunked-upload from the user" path only.
"""
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, TIMESTAMP, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from gemini.db.core.base import BaseModel


class ExperimentFileModel(BaseModel):
    """One row per MinIO object uploaded under a given experiment."""

    __tablename__ = "experiment_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Sub-grouping inside an experiment: the "upload batch". Optional —
    # legacy rows pre-dating migration 0007 stay NULL and are only
    # cleanable via the experiment cascade. ON DELETE SET NULL so
    # Dataset.delete() can drop the dataset row without orphaning the
    # file rows mid-sweep (it reads them first, then nulls, then
    # deletes the rows by id after MinIO removal).
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    bucket: Mapped[str] = mapped_column(Text, nullable=False)
    object_name: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemini.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now,
        nullable=False,
    )
    # Per-object derived metadata (e.g., {"gps": {"lat", "lon", "alt"}}).
    # Populated at upload time for image extensions and lazily backfilled
    # by the image-gps endpoint for older rows. Named ``metadata_json``
    # because plain ``metadata`` is a reserved attribute on SQLAlchemy
    # declarative classes.
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        # An object key is globally unique per bucket; uniqueness here
        # also makes the upload-finalize INSERT idempotent against
        # accidental double-finalise (multipart retry on the very last
        # chunk).
        UniqueConstraint("bucket", "object_name", name="experiment_files_unique_object"),
        Index("idx_experiment_files_experiment_id", "experiment_id"),
        Index("idx_experiment_files_dataset_id", "dataset_id"),
    )
