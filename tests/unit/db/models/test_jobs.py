"""
Tests for gemini.db.models.jobs.JobModel schema definition.
"""
import pytest
from gemini.db.models.jobs import JobModel


class TestJobModelSchema:
    """Verify JobModel table metadata and column definitions."""

    def test_tablename(self):
        assert JobModel.__tablename__ == "jobs"

    def test_has_id_column(self):
        assert "id" in JobModel.__table__.columns

    def test_has_job_type_column(self):
        assert "job_type" in JobModel.__table__.columns

    def test_has_status_column(self):
        assert "status" in JobModel.__table__.columns

    def test_has_progress_column(self):
        assert "progress" in JobModel.__table__.columns

    def test_has_progress_detail_column(self):
        assert "progress_detail" in JobModel.__table__.columns

    def test_has_parameters_column(self):
        assert "parameters" in JobModel.__table__.columns

    def test_has_result_column(self):
        assert "result" in JobModel.__table__.columns

    def test_has_error_message_column(self):
        assert "error_message" in JobModel.__table__.columns

    def test_has_experiment_id_column(self):
        assert "experiment_id" in JobModel.__table__.columns

    def test_has_worker_id_column(self):
        assert "worker_id" in JobModel.__table__.columns

    def test_has_started_at_column(self):
        assert "started_at" in JobModel.__table__.columns

    def test_has_completed_at_column(self):
        assert "completed_at" in JobModel.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in JobModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in JobModel.__table__.columns

    def test_id_is_primary_key(self):
        assert JobModel.__table__.columns["id"].primary_key

    def test_job_type_not_nullable(self):
        assert JobModel.__table__.columns["job_type"].nullable is False

    def test_status_not_nullable(self):
        assert JobModel.__table__.columns["status"].nullable is False

    def test_progress_not_nullable(self):
        assert JobModel.__table__.columns["progress"].nullable is False

    def test_experiment_id_nullable(self):
        assert JobModel.__table__.columns["experiment_id"].nullable is True

    def test_indexes_exist(self):
        index_names = {idx.name for idx in JobModel.__table__.indexes}
        assert "idx_jobs_status" in index_names
        assert "idx_jobs_type" in index_names
        assert "idx_jobs_experiment" in index_names
        assert "idx_jobs_detail" in index_names
