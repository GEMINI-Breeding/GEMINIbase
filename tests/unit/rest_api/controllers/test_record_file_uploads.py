"""POST /api/<entity>/id/{id}/records with a record_file upload.

The five record-upload handlers must:
- run their blocking DB/MinIO work off the event loop,
- save each upload under its own name inside the uploads folder, whatever
  filename the client sent, and
- delete that local copy once the request is done.
"""
import asyncio
import io
import os
from unittest.mock import MagicMock, patch

import pytest

from gemini.rest_api.file_handler import api_file_handler

CASES = [
    ("datasets", "dataset", "Dataset", {"dataset_data": "{}"}),
    ("sensors", "sensor", "Sensor", {"sensor_data": "{}"}),
    ("procedures", "procedure", "Procedure", {"dataset_name": "d", "procedure_data": "{}"}),
    ("models", "model", "Model", {"dataset_name": "d", "model_data": "{}"}),
    ("scripts", "script", "Script", {"dataset_name": "d", "script_data": "{}"}),
]
IDS = [c[0] for c in CASES]


@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    folder = tmp_path / "uploads"
    folder.mkdir()
    monkeypatch.setattr(api_file_handler, "uploads_folder", str(folder))
    return folder


def _post(test_client, route, fields, filename, content):
    return test_client.post(
        f"/api/{route}/id/abc/records",
        data={"timestamp": "2024-06-15T10:00:00", **fields},
        files={"record_file": (filename, io.BytesIO(content), "text/plain")},
    )


class _Capture:
    """Stands in for <entity>.insert_record and snapshots the saved upload."""

    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        path = kwargs["record_file"]
        with open(path, "rb") as f:
            self.calls.append((path, f.read()))
        return False, []


@pytest.mark.parametrize("route,module,entity,fields", CASES, ids=IDS)
def test_blocking_work_runs_off_the_event_loop(route, module, entity, fields, test_client, uploads_dir):
    seen = {}

    def get_by_id(**_kwargs):
        try:
            asyncio.get_running_loop()
            seen["on_loop"] = True
        except RuntimeError:
            seen["on_loop"] = False
        return None

    with patch(f"gemini.rest_api.controllers.{module}.{entity}") as cls:
        cls.get_by_id.side_effect = get_by_id
        _post(test_client, route, fields, "a.txt", b"x")
    assert seen == {"on_loop": False}


@pytest.mark.parametrize("route,module,entity,fields", CASES, ids=IDS)
def test_same_filename_uploads_do_not_overwrite_each_other(route, module, entity, fields, test_client, uploads_dir):
    capture = _Capture()
    with patch(f"gemini.rest_api.controllers.{module}.{entity}") as cls:
        cls.get_by_id.return_value.insert_record.side_effect = capture
        _post(test_client, route, fields, "data.csv", b"first")
        _post(test_client, route, fields, "data.csv", b"second")

    (path_a, body_a), (path_b, body_b) = capture.calls
    assert path_a != path_b
    assert (body_a, body_b) == (b"first", b"second")
    # The MinIO object key is built from the extension, so keep it.
    assert path_a.endswith(".csv") and path_b.endswith(".csv")


@pytest.mark.parametrize("route,module,entity,fields", CASES, ids=IDS)
def test_client_filename_cannot_escape_uploads_folder(route, module, entity, fields, test_client, uploads_dir):
    capture = _Capture()
    with patch(f"gemini.rest_api.controllers.{module}.{entity}") as cls:
        cls.get_by_id.return_value.insert_record.side_effect = capture
        _post(test_client, route, fields, "../../escape.txt", b"x")

    (path, _), = capture.calls
    assert os.path.dirname(os.path.realpath(path)) == os.path.realpath(uploads_dir)
    assert not (uploads_dir.parent.parent / "escape.txt").exists()


@pytest.mark.parametrize("route,module,entity,fields", CASES, ids=IDS)
def test_local_upload_is_deleted_after_the_request(route, module, entity, fields, test_client, uploads_dir):
    capture = _Capture()
    with patch(f"gemini.rest_api.controllers.{module}.{entity}") as cls:
        cls.get_by_id.return_value.insert_record.side_effect = capture
        _post(test_client, route, fields, "a.txt", b"x")

    (path, _), = capture.calls
    assert not os.path.exists(path)
    assert list(uploads_dir.iterdir()) == []
