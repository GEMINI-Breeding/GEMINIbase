"""
Integration tests for the job queue.

These tests hit a real PostgreSQL database — no mocks.
Requires:  docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest
from uuid import uuid4


pytestmark = pytest.mark.integration


class TestJobTableExists:
    """Verify the jobs table was created by the init script."""

    def test_jobs_table_in_schema(self, db_engine):
        from sqlalchemy import text
        with db_engine.get_session() as session:
            result = session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'gemini' AND table_name = 'jobs'"
            ))
            assert result.scalar() == "jobs"

    def test_jobs_table_has_expected_columns(self, db_engine):
        from sqlalchemy import text
        with db_engine.get_session() as session:
            result = session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'gemini' AND table_name = 'jobs' "
                "ORDER BY ordinal_position"
            ))
            columns = [row[0] for row in result]
        expected = [
            "id", "job_type", "status", "progress", "progress_detail",
            "parameters", "result", "error_message", "experiment_id",
            "worker_id", "started_at", "completed_at", "created_at", "updated_at",
        ]
        assert columns == expected

    def test_jobs_indexes_exist(self, db_engine):
        from sqlalchemy import text
        with db_engine.get_session() as session:
            result = session.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'gemini' AND tablename = 'jobs'"
            ))
            index_names = {row[0] for row in result}
        assert "idx_jobs_status" in index_names
        assert "idx_jobs_type" in index_names
        assert "idx_jobs_experiment" in index_names
        assert "idx_jobs_detail" in index_names


class TestJobCRUD:
    """Test job creation, retrieval, update, and deletion against real DB."""

    def test_create_job(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="TRAIN_MODEL", parameters={"epochs": 50})
        assert job is not None
        assert job.id is not None
        assert job.job_type == "TRAIN_MODEL"
        assert job.status == "PENDING"
        assert job.progress == 0.0
        assert job.parameters == {"epochs": 50}

    def test_get_job_by_id(self, setup_real_db):
        from gemini.api.job import Job
        created = Job.create(job_type="LOCATE_PLANTS", parameters={"batch": 32})
        fetched = Job.get_by_id(id=created.id)
        assert fetched is not None
        assert str(fetched.id) == str(created.id)
        assert fetched.job_type == "LOCATE_PLANTS"

    def test_get_all_jobs(self, setup_real_db):
        from gemini.api.job import Job
        Job.create(job_type="TRAIN_MODEL", parameters={})
        Job.create(job_type="EXTRACT_TRAITS", parameters={})
        jobs = Job.get_all()
        assert jobs is not None
        assert len(jobs) == 2

    def test_search_by_status(self, setup_real_db):
        from gemini.api.job import Job
        Job.create(job_type="TRAIN_MODEL", parameters={})
        Job.create(job_type="EXTRACT_TRAITS", parameters={})
        pending = Job.search(status="PENDING")
        assert pending is not None
        assert len(pending) == 2
        running = Job.search(status="RUNNING")
        assert running is None

    def test_update_job_status(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="RUN_ODM", parameters={})
        updated = job.update(status="RUNNING", worker_id="test-worker")
        assert updated is not None
        assert updated.status == "RUNNING"
        assert updated.worker_id == "test-worker"

    def test_update_progress(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="RUN_STITCH", parameters={})
        updated = job.update_progress(progress=42.5, detail={"step": "alignment"})
        assert updated is not None
        assert updated.progress == 42.5
        assert updated.progress_detail == {"step": "alignment"}

    def test_claim_job(self, setup_real_db):
        from gemini.api.job import Job
        Job.create(job_type="RUN_ODM", parameters={"test": True})
        claimed = Job.claim(job_type="RUN_ODM", worker_id="worker-1")
        assert claimed is not None
        assert claimed.status == "RUNNING"
        assert claimed.worker_id == "worker-1"
        assert claimed.started_at is not None
        assert claimed.parameters == {"test": True}

    def test_claim_no_pending_returns_none(self, setup_real_db):
        from gemini.api.job import Job
        result = Job.claim(job_type="RUN_ODM", worker_id="worker-1")
        assert result is None

    def test_claim_is_atomic(self, setup_real_db):
        """Two workers claiming the same job type should each get a different job."""
        from gemini.api.job import Job
        Job.create(job_type="RUN_ODM", parameters={"idx": 1})
        Job.create(job_type="RUN_ODM", parameters={"idx": 2})

        claimed_1 = Job.claim(job_type="RUN_ODM", worker_id="worker-A")
        claimed_2 = Job.claim(job_type="RUN_ODM", worker_id="worker-B")

        assert claimed_1 is not None
        assert claimed_2 is not None
        assert str(claimed_1.id) != str(claimed_2.id)

        # Third claim should return None — no more pending
        claimed_3 = Job.claim(job_type="RUN_ODM", worker_id="worker-C")
        assert claimed_3 is None

    def test_claim_only_matches_type(self, setup_real_db):
        from gemini.api.job import Job
        Job.create(job_type="TRAIN_MODEL", parameters={})
        result = Job.claim(job_type="RUN_ODM", worker_id="worker-1")
        assert result is None

    def test_cancel_pending_job(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="TRAIN_MODEL", parameters={})
        cancelled = job.cancel()
        assert cancelled is not None
        assert cancelled.status == "CANCELLED"

    def test_cancel_completed_job_returns_none(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="TRAIN_MODEL", parameters={})
        job.update(status="COMPLETED")
        refreshed = job.refresh()
        result = refreshed.cancel()
        assert result is None

    def test_complete_job(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="EXTRACT_TRAITS", parameters={})
        completed = job.complete(result={"extracted": 150})
        assert completed is not None
        assert completed.status == "COMPLETED"
        assert completed.progress == 100.0
        assert completed.result == {"extracted": 150}

    def test_fail_job(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="PROCESS_DRONE_TIFF", parameters={})
        failed = job.fail(error_message="Out of memory")
        assert failed is not None
        assert failed.status == "FAILED"
        assert failed.error_message == "Out of memory"

    def test_delete_job(self, setup_real_db):
        from gemini.api.job import Job
        job = Job.create(job_type="TRAIN_MODEL", parameters={})
        job_id = job.id
        assert job.delete() is True
        assert Job.get_by_id(id=job_id) is None

    def test_job_lifecycle(self, setup_real_db):
        """Full lifecycle: create -> start -> progress -> complete."""
        from gemini.api.job import Job
        job = Job.create(job_type="TRAIN_MODEL", parameters={"epochs": 10})
        assert job.status == "PENDING"

        job = job.start(worker_id="worker-1")
        assert job.status == "RUNNING"
        assert job.worker_id == "worker-1"
        assert job.started_at is not None

        job = job.update_progress(50.0, {"epoch": 5, "map": 0.75})
        assert job.progress == 50.0

        job = job.complete(result={"final_map": 0.89})
        assert job.status == "COMPLETED"
        assert job.progress == 100.0
        assert job.completed_at is not None


class TestJobRESTEndpoints:
    """Test job REST API endpoints against real DB."""

    @pytest.fixture
    def client(self, setup_real_db):
        from litestar.testing import TestClient
        from gemini.rest_api.app import app
        with TestClient(app=app) as c:
            yield c

    def test_submit_job(self, client):
        resp = client.post("/api/jobs/submit", json={
            "job_type": "TRAIN_MODEL",
            "parameters": {"epochs": 100},
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["id"] is not None
        assert data["job_type"] == "TRAIN_MODEL"
        assert data["status"] == "PENDING"

    def test_submit_invalid_type(self, client):
        resp = client.post("/api/jobs/submit", json={
            "job_type": "BOGUS",
            "parameters": {},
        })
        assert resp.status_code == 400

    def test_get_job(self, client):
        create_resp = client.post("/api/jobs/submit", json={
            "job_type": "LOCATE_PLANTS",
            "parameters": {},
        })
        job_id = create_resp.json()["id"]

        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id

    def test_get_missing_job(self, client):
        resp = client.get(f"/api/jobs/{uuid4()}")
        assert resp.status_code == 404

    def test_list_jobs(self, client):
        client.post("/api/jobs/submit", json={"job_type": "TRAIN_MODEL", "parameters": {}})
        client.post("/api/jobs/submit", json={"job_type": "RUN_ODM", "parameters": {}})

        resp = client.get("/api/jobs/all")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_list_jobs_filter_by_type(self, client):
        client.post("/api/jobs/submit", json={"job_type": "TRAIN_MODEL", "parameters": {}})
        client.post("/api/jobs/submit", json={"job_type": "RUN_ODM", "parameters": {}})

        resp = client.get("/api/jobs/all?job_type=RUN_ODM")
        assert resp.status_code == 200
        jobs = resp.json()
        assert all(j["job_type"] == "RUN_ODM" for j in jobs)

    def test_cancel_job(self, client):
        create_resp = client.post("/api/jobs/submit", json={
            "job_type": "EXTRACT_TRAITS",
            "parameters": {},
        })
        job_id = create_resp.json()["id"]

        resp = client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 201
        assert resp.json()["status"] == "CANCELLED"

    def test_cancel_already_completed(self, client):
        create_resp = client.post("/api/jobs/submit", json={
            "job_type": "TRAIN_MODEL",
            "parameters": {},
        })
        job_id = create_resp.json()["id"]

        # Complete it first
        client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "COMPLETED",
            "progress": 100.0,
        })

        resp = client.post(f"/api/jobs/{job_id}/cancel")
        assert resp.status_code == 409

    def test_update_status(self, client):
        create_resp = client.post("/api/jobs/submit", json={
            "job_type": "RUN_STITCH",
            "parameters": {},
        })
        job_id = create_resp.json()["id"]

        resp = client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "RUNNING",
            "worker_id": "test-worker",
            "progress": 25.0,
            "progress_detail": {"step": "feature_matching"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert data["progress"] == 25.0

    def test_delete_job(self, client):
        create_resp = client.post("/api/jobs/submit", json={
            "job_type": "TRAIN_MODEL",
            "parameters": {},
        })
        job_id = create_resp.json()["id"]

        resp = client.delete(f"/api/jobs/{job_id}")
        assert resp.status_code == 200

        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 404

    def test_claim_job_via_rest(self, client):
        client.post("/api/jobs/submit", json={
            "job_type": "RUN_ODM", "parameters": {"images": 5},
        })
        resp = client.post("/api/jobs/claim", json={
            "job_type": "RUN_ODM", "worker_id": "rest-worker-1",
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert data["worker_id"] == "rest-worker-1"
        assert data["parameters"] == {"images": 5}

    def test_claim_returns_404_when_empty(self, client):
        resp = client.post("/api/jobs/claim", json={
            "job_type": "RUN_ODM", "worker_id": "worker-1",
        })
        assert resp.status_code == 404

    def test_claim_invalid_type(self, client):
        resp = client.post("/api/jobs/claim", json={
            "job_type": "BOGUS", "worker_id": "worker-1",
        })
        assert resp.status_code == 400

    def test_claim_prevents_double_claim(self, client):
        """Two claim requests for the same single pending job — only one succeeds."""
        client.post("/api/jobs/submit", json={
            "job_type": "RUN_ODM", "parameters": {},
        })
        resp1 = client.post("/api/jobs/claim", json={
            "job_type": "RUN_ODM", "worker_id": "worker-A",
        })
        resp2 = client.post("/api/jobs/claim", json={
            "job_type": "RUN_ODM", "worker_id": "worker-B",
        })
        assert resp1.status_code == 201
        # Second claim gets 404 — no more pending
        assert resp2.status_code == 404

    def test_full_lifecycle_via_rest(self, client):
        """Submit -> start -> progress updates -> complete, all via REST."""
        # Submit
        resp = client.post("/api/jobs/submit", json={
            "job_type": "TRAIN_MODEL",
            "parameters": {"epochs": 10},
        })
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        # Start
        resp = client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "RUNNING",
            "worker_id": "worker-1",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "RUNNING"

        # Progress
        resp = client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "RUNNING",
            "progress": 50.0,
            "progress_detail": {"epoch": 5},
        })
        assert resp.status_code == 200
        assert resp.json()["progress"] == 50.0

        # Complete
        resp = client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "COMPLETED",
            "progress": 100.0,
            "result": {"final_map": 0.92},
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

        # Verify final state
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        final = resp.json()
        assert final["status"] == "COMPLETED"
        assert final["progress"] == 100.0
        assert final["result"] == {"final_map": 0.92}
