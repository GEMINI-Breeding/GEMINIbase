"""
API entity for Job — represents a long-running processing task.

Provides CRUD operations and status management for jobs submitted
to the processing worker queue.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import Field, AliasChoices
import logging

from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.jobs import JobModel

logger = logging.getLogger(__name__)


class Job(APIBase):
    """
    Represents a processing job entity.

    Attributes:
        id: Unique identifier.
        job_type: Type of job (TRAIN_MODEL, LOCATE_PLANTS, etc.).
        status: Current status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED).
        progress: Progress percentage 0-100.
        progress_detail: Detailed progress (e.g. {epoch: 5, map: 0.82}).
        parameters: Input parameters for the job.
        result: Output result data.
        error_message: Error details if failed.
        experiment_id: Associated experiment UUID.
        worker_id: Worker processing this job.
        started_at: When processing started.
        completed_at: When processing finished.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "job_id"))
    job_type: str
    status: str = "PENDING"
    progress: float = 0.0
    progress_detail: Optional[dict] = None
    parameters: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    experiment_id: Optional[UUID] = None
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def exists(cls, **kwargs) -> bool:
        try:
            return JobModel.exists(**kwargs)
        except Exception as e:
            logger.error(f"Error checking job existence: {e}")
            return False

    @classmethod
    def create(cls, job_type: str, parameters: dict = None,
               experiment_id: UUID = None) -> Optional["Job"]:
        try:
            db_instance = JobModel.create(
                job_type=job_type,
                status="PENDING",
                progress=0.0,
                parameters=parameters,
                experiment_id=experiment_id,
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: ID) -> Optional["Job"]:
        try:
            db_instance = JobModel.get(id=id)
            if db_instance is None:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting job by id: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = 100, offset: int = 0) -> Optional[List["Job"]]:
        try:
            db_instances = JobModel.all(limit=limit, offset=offset)
            if not db_instances:
                return None
            return [cls.model_validate(inst) for inst in db_instances]
        except Exception as e:
            logger.error(f"Error getting all jobs: {e}")
            return None

    @classmethod
    def get(cls, **kwargs) -> Optional["Job"]:
        try:
            db_instance = JobModel.get_by_parameters(**kwargs)
            if db_instance is None:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return None

    @classmethod
    def search(cls, **kwargs) -> Optional[List["Job"]]:
        try:
            db_instances = JobModel.search(**kwargs)
            if not db_instances:
                return None
            return [cls.model_validate(inst) for inst in db_instances]
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return None

    def update(self, **kwargs) -> Optional["Job"]:
        try:
            db_instance = JobModel.get(id=self.id)
            if db_instance is None:
                return None
            db_instance = JobModel.update(db_instance, **kwargs)
            return Job.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error updating job: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = JobModel.get(id=self.id)
            if db_instance is None:
                return False
            return JobModel.delete(db_instance)
        except Exception as e:
            logger.error(f"Error deleting job: {e}")
            return False

    def refresh(self) -> Optional["Job"]:
        try:
            db_instance = JobModel.get(id=self.id)
            if db_instance is None:
                return None
            return Job.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error refreshing job: {e}")
            return None

    def cancel(self) -> Optional["Job"]:
        """Cancel a PENDING or RUNNING job."""
        if self.status not in ("PENDING", "RUNNING"):
            return None
        return self.update(status="CANCELLED", completed_at=datetime.now())

    def start(self, worker_id: str) -> Optional["Job"]:
        """Mark job as started by a worker."""
        return self.update(
            status="RUNNING",
            worker_id=worker_id,
            started_at=datetime.now(),
        )

    def complete(self, result: dict = None) -> Optional["Job"]:
        """Mark job as successfully completed."""
        return self.update(
            status="COMPLETED",
            progress=100.0,
            result=result,
            completed_at=datetime.now(),
        )

    def fail(self, error_message: str) -> Optional["Job"]:
        """Mark job as failed."""
        return self.update(
            status="FAILED",
            error_message=error_message,
            completed_at=datetime.now(),
        )

    def update_progress(self, progress: float, detail: dict = None) -> Optional["Job"]:
        """Update job progress."""
        kwargs = {"progress": progress}
        if detail is not None:
            kwargs["progress_detail"] = detail
        return self.update(**kwargs)
