"""Backfill `plots.plot_geometry_info` from active `plot_geometry_versions`.

PlotGeometryVersion.save() and .activate() now materialize a `plots` row
for every polygon in the active snapshot, populating
`plot_geometry_info` with the GeoJSON Feature. Existing snapshots saved
before that hook landed are missing this materialization — they
contain the boundaries inside their `state_snapshot` but no
corresponding `plots` rows have geometry.

Running this script (one-shot, idempotent) iterates every directory's
currently-active version and re-runs the materialization. Safe to
re-run — it uses `ON CONFLICT DO UPDATE` so re-imported geometry
overwrites stale rows.

Usage from the rest-api container:

    docker exec geminibase-rest-api \\
        poetry run python -m gemini.scripts.backfill_plot_geometry
"""
from __future__ import annotations

import logging
import sys

from sqlalchemy import select

from gemini.api.plot_geometry_version import _materialize_plots_from_snapshot
from gemini.db.core.base import db_engine
from gemini.db.models.plot_geometry_versions import PlotGeometryVersionModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Iterate every active plot-geometry version and re-materialize plots."""
    with db_engine.get_session() as session:
        rows = (
            session.execute(
                select(
                    PlotGeometryVersionModel.directory,
                    PlotGeometryVersionModel.version,
                    PlotGeometryVersionModel.state_snapshot,
                )
                .where(PlotGeometryVersionModel.is_active.is_(True))
                .order_by(PlotGeometryVersionModel.directory)
            )
            .all()
        )

    if not rows:
        logger.info("No active plot-geometry versions to backfill.")
        return 0

    logger.info(f"Backfilling {len(rows)} active versions.")
    success = 0
    for r in rows:
        try:
            _materialize_plots_from_snapshot(r.directory, r.state_snapshot or {})
            success += 1
        except Exception as e:
            logger.error(f"Backfill failed for {r.directory!r} v{r.version}: {e}")
    logger.info(
        f"Backfill complete: {success}/{len(rows)} directories processed."
    )
    return 0 if success == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
