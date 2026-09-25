"""
Orphaned-job reaper.

A worker that's killed mid-`process()` (app quit, compose down, OOM,
container crash) leaves its job in RUNNING with no one to drive it; the
restarted worker only claims PENDING jobs, so without this the job — and
the UI spinner — stays RUNNING forever.

Liveness signal: `updated_at`. While a job runs, the worker's heartbeat
thread (`BaseWorker._heartbeat`) bumps it through `touch_job` every
`HEARTBEAT_INTERVAL_SECONDS`, on top of every progress PATCH. A RUNNING job
whose `updated_at` is older than the threshold has no live worker.

The REST API runs `reap_orphaned_jobs` periodically (see
`gemini.rest_api.app`), not only on startup: a worker can die while the API
stays up. PENDING jobs are never reaped. They are waiting in the queue,
and with one worker per job type a queue behind a multi-hour ODM run is
normal; failing them as "orphaned" was wrong.
"""
from typing import List, Tuple

import logging
from sqlalchemy import text

from gemini.db.core.base import db_engine

logger = logging.getLogger(__name__)

# How often a worker bumps its running job. The reaper threshold must be
# several multiples of this.
HEARTBEAT_INTERVAL_SECONDS = 30


def touch_job(job_id: str) -> bool:
    """Heartbeat: bump a RUNNING job's updated_at. False if it isn't RUNNING."""
    with db_engine.get_session() as session:
        result = session.execute(
            text(
                """
                UPDATE gemini.jobs SET updated_at = NOW()
                WHERE id = :job_id AND status = 'RUNNING'
                """
            ),
            {"job_id": job_id},
        )
        return result.rowcount > 0


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
