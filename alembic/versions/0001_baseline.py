"""baseline — matches init_sql/ DDL as of Phase 3.5

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-24

This is the Alembic baseline for GEMINIbase. Before this revision,
schema was created exclusively by the ``gemini/db/init_sql/scripts/*.sql``
files that the Postgres container runs on first-time volume init. That
works fine for fresh installs but silently breaks any developer who
already had a DB volume when a new table landed (Phase 2 added five
tables via init_sql — users, user_experiments, reference_datasets,
reference_plots, plot_geometry_versions — and existing volumes never
picked them up without a manual ``psql`` session).

Going forward:
- Day-0 schema stays in init_sql/ so first-boot Postgres behaviour is
  unchanged.
- Any schema change after this baseline is a new Alembic revision.
- The rest-api container runs ``alembic upgrade head`` on startup
  (opt-in via GEMINI_RUN_MIGRATIONS=1); existing DBs should be stamped
  to this baseline once with ``alembic stamp head``.

This migration is intentionally a no-op on upgrade and downgrade. It
exists purely to mark the "everything from init_sql is considered
already applied" point in history.
"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: tables exist via init_sql/ DDL on fresh Postgres init."""
    pass


def downgrade() -> None:
    """No-op: the baseline does not describe a reversible schema state."""
    pass
