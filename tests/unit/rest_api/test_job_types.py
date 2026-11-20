"""The jobs API accepts every job type the workers define."""
from gemini.rest_api.controllers.jobs import VALID_JOB_TYPES
from gemini.workers.types import JobType


def test_every_worker_job_type_is_accepted():
    assert VALID_JOB_TYPES == {t.value for t in JobType}
    assert "GROUND_PLOT_FRAMES" in VALID_JOB_TYPES
