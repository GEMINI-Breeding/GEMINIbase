"""Add ``metadata_json`` JSONB to ``gemini.experiment_files``.

Revision ID: 0005_experiment_files_metadata
Revises: 0004_experiment_files
Create Date: 2026-05-07

Caches per-image EXIF GPS (and any future per-object derived metadata)
on the same row that already points at the MinIO object. Lets the
Image Exclusion + GCP picker map views render in one DB query instead
of fanning out one HTTP Range request per image to read EXIF in the
browser.

The column is named ``metadata_json`` rather than ``metadata`` because
``metadata`` is a reserved attribute name on SQLAlchemy declarative
classes (it's the registry's MetaData object) and shadowing it is a
footgun.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_experiment_files_metadata"
down_revision: Union[str, Sequence[str], None] = "0004_experiment_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiment_files",
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="gemini",
    )


def downgrade() -> None:
    op.drop_column("experiment_files", "metadata_json", schema="gemini")
