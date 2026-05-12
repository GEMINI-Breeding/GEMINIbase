"""Add nullable ``dataset_id`` FK to ``gemini.experiment_files``.

Revision ID: 0007_experiment_files_dataset
Revises: 0006_trait_records_accession
Create Date: 2026-05-11

Pre-this-revision, every upload type other than trait CSV imports
produced ``experiment_files`` rows owned only by the experiment — there
was no per-batch deletable unit between "the experiment" and "the
individual MinIO object". The amiga worker's hundreds of extracted
RGB/Disparity outputs were even worse off: they wrote zero
``experiment_files`` rows at all, surviving only because the
experiment-delete cascade prefix-sweeps ``Processed/{year}/{exp_name}/``
as a backstop.

This revision adds a nullable foreign-key column so each chunk-upload
finalize and each worker-registered output can claim a dataset id. The
``Dataset.delete()`` cascade is extended in a follow-up code change to
read these rows and sweep the named MinIO objects + delete the rows
themselves. Existing rows stay valid with NULL — they're "experiment-
owned, dataset-orphaned" and remain deletable via the experiment
cascade only. No backfill — inferring the right dataset name from the
object path is exactly the brittleness this change is removing.

``ON DELETE SET NULL`` so a dataset row can disappear without
cascading the file rows out from under any concurrent listing; the
file rows then revert to legacy "experiment-only" status and are
swept by the experiment cascade as before.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_experiment_files_dataset"
down_revision: Union[str, Sequence[str], None] = "0006_trait_records_accession"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiment_files",
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="gemini",
    )
    op.create_foreign_key(
        "fk_experiment_files_dataset",
        "experiment_files",
        "datasets",
        ["dataset_id"],
        ["id"],
        source_schema="gemini",
        referent_schema="gemini",
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_experiment_files_dataset_id",
        "experiment_files",
        ["dataset_id"],
        schema="gemini",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_experiment_files_dataset_id",
        table_name="experiment_files",
        schema="gemini",
    )
    op.drop_constraint(
        "fk_experiment_files_dataset",
        "experiment_files",
        type_="foreignkey",
        schema="gemini",
    )
    op.drop_column("experiment_files", "dataset_id", schema="gemini")
