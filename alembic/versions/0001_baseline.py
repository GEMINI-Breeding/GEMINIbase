"""baseline — the pre-Alembic schema created by main's init_sql/

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-24

This is the Alembic baseline for GEMINIbase. Before this revision,
schema was created exclusively by the ``gemini/db/init_sql/scripts/*.sql``
files that the Postgres container runs on first-time volume init. That
works fine for fresh installs but silently breaks any developer who
already had a DB volume when a new table landed.

What "at baseline" means: the schema a DB has after being bootstrapped
from the pre-Alembic (main-branch) init_sql/. Note that this does NOT
include five tables that were added to init_sql/ on the Alembic branch
— users, user_experiments, reference_datasets, reference_plots and
plot_geometry_versions. Those are created idempotently
(``CREATE ... IF NOT EXISTS``) by a bridge at the top of
0002_genomic_pgen_metadata's upgrade(), so a main-built DB stamped here
picks them up on ``alembic upgrade head``.

Going forward:
- Day-0 schema stays in init_sql/ so first-boot Postgres behaviour is
  unchanged; a volume bootstrapped from the CURRENT init_sql/ is already
  at head and should be stamped with ``alembic stamp head``.
- Any schema change after this baseline is a new Alembic revision.
- The rest-api container runs ``alembic upgrade head`` on startup
  (opt-in via GEMINI_RUN_MIGRATIONS=1).
- An existing DB built from main's pre-Alembic init_sql/ should be
  stamped ONCE at this revision (``alembic stamp 0001_baseline``), not
  at head, and then upgraded.

This migration is intentionally a no-op on upgrade and downgrade. It
exists purely to mark the "pre-Alembic init_sql is considered already
applied" point in history.
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
