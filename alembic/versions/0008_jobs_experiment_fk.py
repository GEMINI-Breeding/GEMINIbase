"""Add ``ON DELETE CASCADE`` FK on ``gemini.jobs.experiment_id``.

Revision ID: 0008_jobs_experiment_fk
Revises: 0007_experiment_files_dataset
Create Date: 2026-05-18

Before this revision ``jobs.experiment_id`` was a plain UUID column with
no FK constraint, so deleting an experiment left every job that
referenced it stranded. A pre-existing dev DB had 99 jobs with
``experiment_id`` pointing to rows that no longer existed — none reachable
from the cascade, none surfaced anywhere in the UI. Adding the FK with
``ON DELETE CASCADE`` matches the convention applied to every other
``experiment_id`` column (seasons, accession_aliases, all the
``experiment_*`` association tables, experiment_files): owned data is
swept when its experiment is dropped. Jobs are owned data — a completed
job whose experiment is gone is meaningless.

Pre-flight: drop any pre-existing dangling rows (experiment_id present
but pointing at a non-existent experiment) so the ALTER TABLE that adds
the FK doesn't immediately reject the constraint check. Rows with
``experiment_id IS NULL`` are preserved (legacy jobs that never had an
experiment assignment).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0008_jobs_experiment_fk"
down_revision: Union[str, Sequence[str], None] = "0007_experiment_files_dataset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM gemini.jobs
         WHERE experiment_id IS NOT NULL
           AND experiment_id NOT IN (SELECT id FROM gemini.experiments);
        """
    )
    op.create_foreign_key(
        "fk_jobs_experiment",
        "jobs",
        "experiments",
        ["experiment_id"],
        ["id"],
        source_schema="gemini",
        referent_schema="gemini",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_jobs_experiment",
        "jobs",
        type_="foreignkey",
        schema="gemini",
    )
