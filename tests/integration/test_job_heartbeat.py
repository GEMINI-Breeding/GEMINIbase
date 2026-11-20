"""POST /api/jobs/{id}/heartbeat keeps a RUNNING job out of the reaper's reach,
and never changes a job's status (so it can't undo a cancel).

Hits a real PostgreSQL database.
"""
import pytest
from tests.integration.test_job_reaper import _get_job, _insert_job

pytestmark = pytest.mark.integration


@pytest.fixture
def test_client_real_db(setup_real_db):
    from litestar.testing import TestClient
    from gemini.rest_api.app import app
    with TestClient(app=app) as client:
        yield client


def test_heartbeat_keeps_running_job_alive(setup_real_db, test_client_real_db):
    from gemini.api.job_reaper import reap_orphaned_jobs

    with setup_real_db.get_session() as session:
        job_id = _insert_job(session, "RUNNING", age_seconds=7200)
    res = test_client_real_db.post(f"/api/jobs/{job_id}/heartbeat")
    assert res.status_code == 200, res.text
    assert res.json() == {"alive": True}

    assert reap_orphaned_jobs(3600) == []
    with setup_real_db.get_session() as session:
        assert _get_job(session, job_id)["status"] == "RUNNING"


def test_heartbeat_does_not_revive_a_cancelled_job(setup_real_db, test_client_real_db):
    with setup_real_db.get_session() as session:
        job_id = _insert_job(session, "CANCELLED", age_seconds=10)
    res = test_client_real_db.post(f"/api/jobs/{job_id}/heartbeat")
    assert res.status_code == 200, res.text
    assert res.json() == {"alive": False}
    with setup_real_db.get_session() as session:
        assert _get_job(session, job_id)["status"] == "CANCELLED"
