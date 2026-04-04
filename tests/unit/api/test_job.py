"""Tests for gemini.api.job module - Job class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime

from gemini.api.job import Job


JOB_MODULE = "gemini.api.job"


def _make_job_db_instance(**overrides):
    """Create a mock JobModel DB instance."""
    defaults = {
        "id": uuid4(),
        "job_type": "TRAIN_MODEL",
        "status": "PENDING",
        "progress": 0.0,
        "progress_detail": None,
        "parameters": {"epochs": 100},
        "result": None,
        "error_message": None,
        "experiment_id": None,
        "worker_id": None,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestJobExists:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_exists_returns_true(self, mock_model):
        mock_model.exists.return_value = True
        assert Job.exists(job_type="TRAIN_MODEL") is True

    @patch(f"{JOB_MODULE}.JobModel")
    def test_exists_returns_false(self, mock_model):
        mock_model.exists.return_value = False
        assert Job.exists(job_type="MISSING") is False

    @patch(f"{JOB_MODULE}.JobModel")
    def test_exists_returns_false_on_exception(self, mock_model):
        mock_model.exists.side_effect = Exception("DB error")
        assert Job.exists(job_type="TRAIN_MODEL") is False


class TestJobCreate:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_create_success(self, mock_model):
        db_inst = _make_job_db_instance()
        mock_model.create.return_value = db_inst
        job = Job.create(job_type="TRAIN_MODEL", parameters={"epochs": 50})
        assert job is not None
        assert job.job_type == "TRAIN_MODEL"
        assert job.status == "PENDING"

    @patch(f"{JOB_MODULE}.JobModel")
    def test_create_returns_none_on_exception(self, mock_model):
        mock_model.create.side_effect = Exception("DB error")
        assert Job.create(job_type="TRAIN_MODEL") is None


class TestJobGetById:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_get_by_id_found(self, mock_model):
        job_id = uuid4()
        db_inst = _make_job_db_instance(id=job_id)
        mock_model.get.return_value = db_inst
        job = Job.get_by_id(id=job_id)
        assert job is not None
        assert job.id == job_id

    @patch(f"{JOB_MODULE}.JobModel")
    def test_get_by_id_not_found(self, mock_model):
        mock_model.get.return_value = None
        assert Job.get_by_id(id=uuid4()) is None


class TestJobGetAll:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_get_all_returns_list(self, mock_model):
        mock_model.all.return_value = [_make_job_db_instance(), _make_job_db_instance()]
        jobs = Job.get_all()
        assert jobs is not None
        assert len(jobs) == 2

    @patch(f"{JOB_MODULE}.JobModel")
    def test_get_all_empty(self, mock_model):
        mock_model.all.return_value = []
        assert Job.get_all() is None


class TestJobSearch:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_search_returns_results(self, mock_model):
        mock_model.search.return_value = [_make_job_db_instance(status="RUNNING")]
        jobs = Job.search(status="RUNNING")
        assert jobs is not None
        assert len(jobs) == 1

    @patch(f"{JOB_MODULE}.JobModel")
    def test_search_empty(self, mock_model):
        mock_model.search.return_value = []
        assert Job.search(status="MISSING") is None


class TestJobUpdate:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_update_success(self, mock_model):
        job_id = uuid4()
        db_inst = _make_job_db_instance(id=job_id)
        updated_inst = _make_job_db_instance(id=job_id, status="RUNNING")
        mock_model.get.return_value = db_inst
        mock_model.update.return_value = updated_inst
        job = Job.model_validate(db_inst)
        result = job.update(status="RUNNING")
        assert result is not None

    @patch(f"{JOB_MODULE}.JobModel")
    def test_update_not_found(self, mock_model):
        mock_model.get.return_value = None
        job = Job(id=uuid4(), job_type="TRAIN_MODEL")
        assert job.update(status="RUNNING") is None


class TestJobCancel:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_cancel_pending(self, mock_model):
        job_id = uuid4()
        db_inst = _make_job_db_instance(id=job_id, status="PENDING")
        cancelled_inst = _make_job_db_instance(id=job_id, status="CANCELLED")
        mock_model.get.return_value = db_inst
        mock_model.update.return_value = cancelled_inst
        job = Job.model_validate(db_inst)
        result = job.cancel()
        assert result is not None

    def test_cancel_completed_returns_none(self):
        job = Job(id=uuid4(), job_type="TRAIN_MODEL", status="COMPLETED")
        assert job.cancel() is None

    def test_cancel_failed_returns_none(self):
        job = Job(id=uuid4(), job_type="TRAIN_MODEL", status="FAILED")
        assert job.cancel() is None


class TestJobDelete:

    @patch(f"{JOB_MODULE}.JobModel")
    def test_delete_success(self, mock_model):
        db_inst = _make_job_db_instance()
        mock_model.get.return_value = db_inst
        mock_model.delete.return_value = True
        job = Job.model_validate(db_inst)
        assert job.delete() is True

    @patch(f"{JOB_MODULE}.JobModel")
    def test_delete_not_found(self, mock_model):
        mock_model.get.return_value = None
        job = Job(id=uuid4(), job_type="TRAIN_MODEL")
        assert job.delete() is False
