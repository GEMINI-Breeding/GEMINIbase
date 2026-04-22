"""Tests for the Jobs controller."""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from gemini.rest_api.models import JobOutput


JOB_API_PATH = "gemini.rest_api.controllers.jobs.Job"
PUBLISH_PATH = "gemini.rest_api.controllers.jobs._publish_job_event"


def _job_output(job_id=None, job_type="TRAIN_MODEL", status="PENDING", progress=0.0):
    """Create a JobOutput model instance for test responses."""
    return JobOutput(
        id=job_id or str(uuid4()),
        job_type=job_type,
        status=status,
        progress=progress,
        parameters={"epochs": 100},
    )


class TestSubmitJob:

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_submit_valid_job(self, mock_job_cls, mock_publish, test_client):
        out = _job_output()
        mock_job_cls.create.return_value = out

        response = test_client.post("/api/jobs/submit", json={
            "job_type": "TRAIN_MODEL",
            "parameters": {"epochs": 100},
        })
        assert response.status_code == 201
        assert response.json()["job_type"] == "TRAIN_MODEL"
        mock_job_cls.create.assert_called_once()
        mock_publish.assert_called_once()

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_submit_invalid_job_type(self, mock_job_cls, mock_publish, test_client):
        response = test_client.post("/api/jobs/submit", json={
            "job_type": "INVALID_TYPE",
            "parameters": {},
        })
        assert response.status_code == 400

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_submit_creation_fails(self, mock_job_cls, mock_publish, test_client):
        mock_job_cls.create.return_value = None
        response = test_client.post("/api/jobs/submit", json={
            "job_type": "LOCATE_PLANTS",
            "parameters": {},
        })
        assert response.status_code == 500


class TestGetJob:

    @patch(JOB_API_PATH)
    def test_get_existing_job(self, mock_job_cls, test_client):
        job_id = str(uuid4())
        mock_job_cls.get_by_id.return_value = _job_output(job_id=job_id)

        response = test_client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["id"] == job_id

    @patch(JOB_API_PATH)
    def test_get_missing_job(self, mock_job_cls, test_client):
        mock_job_cls.get_by_id.return_value = None
        response = test_client.get(f"/api/jobs/{uuid4()}")
        assert response.status_code == 404


class TestGetAllJobs:

    @patch(JOB_API_PATH)
    def test_get_all_jobs(self, mock_job_cls, test_client):
        mock_job_cls.get_all.return_value = [_job_output(), _job_output(job_type="LOCATE_PLANTS")]
        response = test_client.get("/api/jobs/all")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @patch(JOB_API_PATH)
    def test_get_all_with_status_filter(self, mock_job_cls, test_client):
        mock_job_cls.search.return_value = [_job_output(status="RUNNING")]
        response = test_client.get("/api/jobs/all?status=RUNNING")
        assert response.status_code == 200
        mock_job_cls.search.assert_called_once_with(status="RUNNING")

    @patch(JOB_API_PATH)
    def test_get_all_empty(self, mock_job_cls, test_client):
        mock_job_cls.get_all.return_value = None
        response = test_client.get("/api/jobs/all")
        assert response.status_code == 200
        assert response.json() == []


class TestCancelJob:

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_cancel_pending_job(self, mock_job_cls, mock_publish, test_client):
        job_id = str(uuid4())
        job = MagicMock()
        job.status = "PENDING"
        job.cancel.return_value = _job_output(job_id=job_id, status="CANCELLED")
        mock_job_cls.get_by_id.return_value = job

        response = test_client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 201
        mock_publish.assert_called_once()

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_cancel_completed_job_fails(self, mock_job_cls, mock_publish, test_client):
        job = MagicMock()
        job.status = "COMPLETED"
        job.cancel.return_value = None
        mock_job_cls.get_by_id.return_value = job

        response = test_client.post(f"/api/jobs/{uuid4()}/cancel")
        assert response.status_code == 409

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_cancel_missing_job(self, mock_job_cls, mock_publish, test_client):
        mock_job_cls.get_by_id.return_value = None
        response = test_client.post(f"/api/jobs/{uuid4()}/cancel")
        assert response.status_code == 404


class TestUpdateJobStatus:

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_update_status(self, mock_job_cls, mock_publish, test_client):
        job_id = str(uuid4())
        job = MagicMock()
        job.update.return_value = _job_output(job_id=job_id, status="RUNNING", progress=10.0)
        mock_job_cls.get_by_id.return_value = job

        response = test_client.patch(f"/api/jobs/{job_id}/status", json={
            "status": "RUNNING",
            "worker_id": "worker-1",
            "progress": 10.0,
        })
        assert response.status_code == 200
        mock_publish.assert_called_once()

    @patch(PUBLISH_PATH)
    @patch(JOB_API_PATH)
    def test_update_missing_job(self, mock_job_cls, mock_publish, test_client):
        mock_job_cls.get_by_id.return_value = None
        response = test_client.patch(f"/api/jobs/{uuid4()}/status", json={
            "status": "RUNNING",
        })
        assert response.status_code == 404


class TestDeleteJob:

    @patch(JOB_API_PATH)
    def test_delete_existing(self, mock_job_cls, test_client):
        job_id = str(uuid4())
        job = MagicMock()
        job.delete.return_value = True
        mock_job_cls.get_by_id.return_value = job

        response = test_client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @patch(JOB_API_PATH)
    def test_delete_missing(self, mock_job_cls, test_client):
        mock_job_cls.get_by_id.return_value = None
        response = test_client.delete(f"/api/jobs/{uuid4()}")
        assert response.status_code == 404
