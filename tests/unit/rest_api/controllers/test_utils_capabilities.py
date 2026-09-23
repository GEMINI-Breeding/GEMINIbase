"""/api/utils/capabilities: which job types have a live worker."""
import time
from unittest.mock import patch

from gemini.rest_api.controllers import jobs, utils


def test_a_polled_job_type_is_live_and_a_stale_one_is_not():
    with patch.dict(jobs._worker_seen, clear=True):
        jobs._worker_seen["RUN_STITCH"] = time.time() - 5
        jobs._worker_seen["RUN_ODM"] = time.time() - utils.WORKER_LIVE_SECONDS - 30
        assert utils._agrowstitch_status()["available"] is True
        with patch("urllib.request.urlopen", side_effect=OSError("down")):
            odm = utils._nodeodm_status()
        assert odm == {"worker": False, "nodeodm": False}


def test_nothing_polled_means_no_stitch_worker():
    with patch.dict(jobs._worker_seen, clear=True):
        assert utils._agrowstitch_status() == {"available": False, "path": None}
        assert jobs.workers_seen() == {}
