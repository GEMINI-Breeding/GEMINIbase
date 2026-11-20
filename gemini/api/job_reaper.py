"""
Orphaned-job reaper.

A worker that's killed mid-`process()` (app quit, compose down, OOM,
container crash) leaves its job in RUNNING with no one to drive it; the
restarted worker only claims PENDING jobs, so without this the job — and
the UI spinner — stays RUNNING forever.

The REST API runs the reaper on startup and then every
GEMINI_JOB_REAPER_INTERVAL_SECONDS, since a worker can die at any time,
not only when the whole stack restarts. The signal is `updated_at`:
workers bump it on every progress event and, while process() runs, with a
heartbeat (`touch_running_job`), so a job whose worker is alive always has
a fresh value even during a long step that reports no progress. Anything
older than the threshold cannot have a live worker behind it.
PENDING jobs are never reaped: they are waiting in the queue, and with one
worker per job type a queue behind a multi-hour ODM run is normal.
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
    """Mark RUNNING jobs with no worker activity for the threshold as FAILED.

    Args:
        stale_after_seconds: A job is reaped if its updated_at is older than
            this many seconds. Pass 0 to disable (no rows touched, returns []).

    Returns:
        List of (id, job_type) tuples for the rows that were reaped.
    """
    if stale_after_seconds <= 0:
        return []

    error_message = (
        f"Interrupted: the worker stopped responding (no heartbeat for "
        f"{stale_after_seconds}s), e.g. because the app or its container was "
        "stopped. Run the step again."
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
                WHERE status = 'RUNNING'
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
    return reaped
