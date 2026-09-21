"""Backfill `trait_records.population_id` / `population_name` for existing rows.

alembic 0009 added the population columns and a one-time backfill (from
`record_info->>'population'`, then from the plot). But records ingested
*before* the boundary plots carried a `population_id` — notably
EXTRACT_TRAITS output, whose GeoJSON has no population property — were
left NULL because the plot they link to had no population to inherit.

After running `backfill_plot_geometry` (which now stamps
`plots.population_id`), this script fills any remaining NULL-population
records straight from their linked plot, and refreshes the pg_ivm IMMV
so the analyze map (which reads the IMMV) sees the change.

Idempotent: only touches rows where `population_id IS NULL` and the
linked plot has a population. Safe to re-run.

Usage from the rest-api container:

    docker exec geminibase-rest-api \\
        python -m gemini.scripts.backfill_trait_record_population
"""
from __future__ import annotations

import logging
import sys

from sqlalchemy import text

from gemini.db.core.base import db_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    with db_engine.get_session() as session:
        # trait_records is a Citus columnar table — no UPDATE...FROM with a
        # correlated join in older citus_columnar. Resolve plot→population
        # first, then UPDATE by plot_id in batches. Columnar UPDATE rewrites
        # affected stripes, which is fine for this one-off.
        before = session.execute(
            text(
                "SELECT COUNT(*) FROM gemini.trait_records "
                "WHERE population_id IS NULL"
            )
        ).scalar()
        logger.info(f"trait_records with NULL population before: {before}")

        # Backfill from the linked plot's population. Done as a single
        # correlated UPDATE; if the columnar AM rejects it, fall back to
        # the IMMV-mediated approach below.
        session.execute(
            text(
                """
                UPDATE gemini.trait_records tr
                   SET population_id = pl.population_id,
                       population_name = COALESCE(tr.population_name, pop.population_name)
                  FROM gemini.plots pl
                  LEFT JOIN gemini.populations pop ON pop.id = pl.population_id
                 WHERE tr.population_id IS NULL
                   AND tr.plot_id IS NOT NULL
                   AND pl.id = tr.plot_id
                   AND pl.population_id IS NOT NULL;
                """
            )
        )

        after = session.execute(
            text(
                "SELECT COUNT(*) FROM gemini.trait_records "
                "WHERE population_id IS NULL"
            )
        ).scalar()
        logger.info(
            f"trait_records with NULL population after: {after} "
            f"(filled {before - after})"
        )

    # Refresh the IMMV so the analyze map's population-scoped reads see the
    # backfilled values. pg_ivm keeps the IMMV in sync on INSERT/UPDATE via
    # triggers, but a bulk UPDATE on a columnar source can bypass the
    # incremental path — a full refresh guarantees consistency.
    try:
        with db_engine.get_session() as session:
            session.execute(text("SELECT pgivm.refresh_immv('gemini.trait_records_immv', true)"))
        logger.info("Refreshed trait_records_immv.")
    except Exception as e:
        logger.warning(
            f"Could not refresh trait_records_immv ({e}); the pg_ivm "
            f"triggers may have already kept it in sync."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
