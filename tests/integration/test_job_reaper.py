"""
Integration tests for the orphaned-job reaper.

Hits a real PostgreSQL database — no mocks. The reaper sweeps stale
PENDING/RUNNING jobs whose `updated_at` is older than the threshold,
marking them FAILED with a clear error_message.
"""
import pytest
from sqlalchemy import text


pytestmark = pytest.mark.integration


def _insert_job(session, status: str, age_seconds: int, job_type: str = "RUN_ODM"):
    """Insert a job with updated_at backdated by age_seconds. Returns the id."""
    row = session.execute(
        text(
            """
            INSERT INTO gemini.jobs (job_type, status, progress, updated_at)
            VALUES (:job_type, :status, 0, NOW() - make_interval(secs => :age))
            RETURNING id
            """
        ),
        {"job_type": job_type, "status": status, "age": age_seconds},
    ).scalar()
    session.commit()
    return str(row)


def _get_job(session, job_id: str) -> dict:
    row = session.execute(
        text(
            "SELECT status, error_message, completed_at "
            "FROM gemini.jobs WHERE id = :id"
        ),
        {"id": job_id},
    ).mappings().first()
    return dict(row) if row else None


class TestJobReaper:
    def test_reaper_marks_only_stale_running_or_pending_as_failed(self, setup_real_db):
        """The reaper should:
        - Mark stale RUNNING and stale PENDING as FAILED.
        - Leave fresh RUNNING and fresh PENDING alone (worker is still alive).
        - Leave terminal-state jobs (COMPLETED/FAILED/CANCELLED) alone, even
          if they're old — those are correctly closed and shouldn't be touched.
        """
        from gemini.api.job_reaper import reap_orphaned_jobs

        engine = setup_real_db
        threshold = 60  # 1 minute

        with engine.get_session() as session:
            stale_running = _insert_job(session, "RUNNING", age_seconds=120)
            stale_pending = _insert_job(session, "PENDING", age_seconds=300)
            fresh_running = _insert_job(session, "RUNNING", age_seconds=10)
            fresh_pending = _insert_job(session, "PENDING", age_seconds=5)
            old_completed = _insert_job(session, "COMPLETED", age_seconds=600)
            old_failed = _insert_job(session, "FAILED", age_seconds=600)
            old_cancelled = _insert_job(session, "CANCELLED", age_seconds=600)

        reaped = reap_orphaned_jobs(stale_after_seconds=threshold)

        reaped_ids = {r[0] for r in reaped}
        assert reaped_ids == {stale_running, stale_pending}, (
            f"reaper should sweep exactly the two stale rows, got {reaped_ids}"
        )

        with engine.get_session() as session:
            assert _get_job(session, stale_running)["status"] == "FAILED"
            assert _get_job(session, stale_pending)["status"] == "FAILED"
            # Error message should be present and informative
            stale_msg = _get_job(session, stale_running)["error_message"]
            assert stale_msg is not None
            assert "Orphaned" in stale_msg
            assert str(threshold) in stale_msg
            # completed_at should be set on reaped rows
            assert _get_job(session, stale_running)["completed_at"] is not None

            # Untouched rows
            assert _get_job(session, fresh_running)["status"] == "RUNNING"
            assert _get_job(session, fresh_pending)["status"] == "PENDING"
            assert _get_job(session, old_completed)["status"] == "COMPLETED"
            assert _get_job(session, old_failed)["status"] == "FAILED"
            # The pre-existing FAILED row was inserted with no error_message,
            # the reaper must NOT have rewritten it.
            assert _get_job(session, old_failed)["error_message"] is None
            assert _get_job(session, old_cancelled)["status"] == "CANCELLED"

    def test_reaper_disabled_with_zero_threshold(self, setup_real_db):
        """stale_after_seconds=0 disables the reaper entirely (no rows touched)."""
        from gemini.api.job_reaper import reap_orphaned_jobs

        engine = setup_real_db
        with engine.get_session() as session:
            stale_running = _insert_job(session, "RUNNING", age_seconds=99999)

        reaped = reap_orphaned_jobs(stale_after_seconds=0)
        assert reaped == []

        with engine.get_session() as session:
            assert _get_job(session, stale_running)["status"] == "RUNNING"

    def test_reaper_returns_empty_when_no_orphans(self, setup_real_db):
        """Healthy DB → reaper returns []."""
        from gemini.api.job_reaper import reap_orphaned_jobs

        engine = setup_real_db
        with engine.get_session() as session:
            _insert_job(session, "RUNNING", age_seconds=5)
            _insert_job(session, "COMPLETED", age_seconds=99999)

        assert reap_orphaned_jobs(stale_after_seconds=60) == []
