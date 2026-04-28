"""
Orphaned-job reaper.

A worker that's killed mid-`process()` (compose down, OOM, container crash,
network partition during the final PATCH) leaves its job sitting in
PENDING/RUNNING with no one to drive it. The frontend's ProcessContext
rehydration query then picks it up on every mount, opens a WebSocket to
`/api/jobs/{id}/progress` for the ghost, and the row never disappears.

The reaper sweeps these on REST-API startup. The signal is `updated_at`:
workers' `report_progress` PATCH bumps it on every progress event, and a
worker that's actually running will always have a fresh value. Anything
older than the threshold cannot have a live worker behind it.

This is a single-shot pass on startup, not a periodic background sweeper —
the compose stack restarts together, so by the time the REST-API is up,
any "live" worker would have heartbeat-PATCHed within seconds.
"""
from typing import List, Tuple

import logging
from sqlalchemy import text

from gemini.db.core.base import db_engine

logger = logging.getLogger(__name__)


def reap_orphaned_jobs(stale_after_seconds: int) -> List[Tuple[str, str]]:
    """Mark stale PENDING/RUNNING jobs as FAILED.

    Args:
        stale_after_seconds: A job is reaped if its updated_at is older than
            this many seconds. Pass 0 to disable (no rows touched, returns []).

    Returns:
        List of (id, job_type) tuples for the rows that were reaped.
    """
    if stale_after_seconds <= 0:
        return []

    error_message = (
        f"Orphaned: no worker activity for {stale_after_seconds}s; "
        "reaped on REST-API startup"
    )

    with db_engine.get_session() as session:
        result = session.execute(
            text(
                """
                UPDATE gemini.jobs
                SET status = 'FAILED',
                    error_message = :error_message,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE status IN ('PENDING', 'RUNNING')
                  AND updated_at < NOW() - make_interval(secs => :stale_after_seconds)
                RETURNING id, job_type
                """
            ),
            {
                "error_message": error_message,
                "stale_after_seconds": stale_after_seconds,
            },
        )
        reaped = [(str(row[0]), row[1]) for row in result.fetchall()]

    if reaped:
        logger.info(
            "Reaped %d orphaned job(s) older than %ds: %s",
            len(reaped),
            stale_after_seconds,
            reaped,
        )
    else:
        logger.info("Reaper found no orphaned jobs (threshold %ds)", stale_after_seconds)
    return reaped
