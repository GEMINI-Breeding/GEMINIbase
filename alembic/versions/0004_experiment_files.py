"""Phase 9j: add ``gemini.experiment_files`` so chunked uploads have a
DB-side index of the MinIO objects they wrote.

Revision ID: 0004_experiment_files
Revises: 0003_drop_genotype_records
Create Date: 2026-05-04

Until now, every ``POST /api/files/upload_chunk`` finalize landed at a
deterministic ``Raw/{year}/{exp_name}/...`` path in MinIO but wrote no
row to Postgres. The Experiment delete cascade then had to *guess* the
path layout from the experiment name alone, and got it wrong (it built
``Raw/{exp_name}/`` which never matches because the year sits between
``Raw/`` and the experiment). Result: every E2E test run leaked four-
plus drone images per spec, and a manual hard-delete of an experiment
left its raw uploads orphaned in MinIO.

This migration adds an authoritative pointer table so the cascade can
sweep by row instead of by guess. A follow-up code change has the
upload-finalize handler INSERT a row, and the cascade reads from it
plus a year-prefix backstop for legacy / worker-written objects.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_experiment_files"
down_revision: Union[str, Sequence[str], None] = "0003_drop_genotype_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiment_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_name", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "bucket", "object_name", name="experiment_files_unique_object"
        ),
        schema="gemini",
    )
    op.create_index(
        "idx_experiment_files_experiment_id",
        "experiment_files",
        ["experiment_id"],
        schema="gemini",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_experiment_files_experiment_id",
        table_name="experiment_files",
        schema="gemini",
    )
    op.drop_table("experiment_files", schema="gemini")
