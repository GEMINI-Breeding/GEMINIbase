"""
Orphaned-job reaper.

A worker that's killed mid-`process()` (compose down, OOM, container crash,
network partition during the final PATCH) leaves its job sitting in
PENDING/RUNNING with no one to drive it. The frontend's ProcessContext
rehydration query then picks it up on every mount, opens a WebSocket to
`/api/jobs/{id}/progress` for the ghost, and the row never disappears.

The REST API runs the reaper on startup and then every
GEMINI_JOB_REAPER_INTERVAL_SECONDS, since a worker can die at any time,
not only when the whole stack restarts. The signal is `updated_at`:
workers bump it on every progress event and, while process() runs, with a
heartbeat (`touch_running_job`), so a job whose worker is alive always has
a fresh value even during a long step that reports no progress. Anything
older than the threshold cannot have a live worker behind it.
"""
from typing import List, Tuple

import logging
from sqlalchemy import text

from gemini.db.core.base import db_engine

logger = logging.getLogger(__name__)


def touch_running_job(job_id: str) -> bool:
    """Record that a RUNNING job's worker is still alive.

    Only bumps updated_at; the status is never changed, so a heartbeat that
    arrives after a cancel (or after the reaper gave up on the job) can't
    bring the job back.

    Returns:
        True if the job is RUNNING and was touched, False otherwise.
    """
    with db_engine.get_session() as session:
        touched = session.execute(
            text(
                """
                UPDATE gemini.jobs
                SET updated_at = NOW()
                WHERE id = :job_id AND status = 'RUNNING'
                RETURNING id
                """
            ),
            {"job_id": job_id},
        ).first()
    return touched is not None


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
        "reaped by the REST API"
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
