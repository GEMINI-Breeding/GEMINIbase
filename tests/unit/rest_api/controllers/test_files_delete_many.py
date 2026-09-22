"""POST /api/files/delete_many — delete selected images in one request."""
from unittest.mock import MagicMock, patch

MINIO = "gemini.rest_api.controllers.files.minio_storage_provider"
ENGINE = "gemini.db.core.base.db_engine"


def _session_ctx(executed):
    session = MagicMock()
    session.execute.side_effect = lambda stmt: executed.append(str(stmt))
    ctx = MagicMock()
    ctx.__enter__.return_value = session
    ctx.__exit__.return_value = False
    return ctx


@patch(ENGINE)
@patch(MINIO)
def test_deletes_objects_and_their_pointer_rows(mock_minio, mock_engine, test_client):
    executed: list = []
    mock_engine.get_session.return_value = _session_ctx(executed)
    mock_minio.file_exists.return_value = True
    mock_minio.delete_file.return_value = True
    objs = [
        "Raw/S/E/D/P/2024-06-01/DJI/RGB/ab12cd34/Images/a.jpg",
        "Raw/S/E/D/P/2024-06-01/DJI/RGB/ab12cd34/Images/b.jpg",
    ]
    res = test_client.post("/api/files/delete_many", json={"objects": objs})
    assert res.status_code == 201, res.text
    assert res.json() == {"deleted": objs, "failed": []}
    assert mock_minio.delete_file.call_count == 2
    # One experiment_files sweep per object.
    assert sum("DELETE FROM" in s and "experiment_files" in s for s in executed) == 2


@patch(ENGINE)
@patch(MINIO)
def test_reports_missing_and_refuses_prefixes(mock_minio, mock_engine, test_client):
    mock_engine.get_session.return_value = _session_ctx([])
    mock_minio.file_exists.side_effect = lambda object_name, bucket_name: (
        object_name.endswith("a.jpg")
    )
    mock_minio.delete_file.return_value = True
    res = test_client.post(
        "/api/files/delete_many",
        json={"objects": ["Raw/x/a.jpg", "Raw/x/gone.jpg", "Raw/x/"]},
    )
    body = res.json()
    assert body["deleted"] == ["Raw/x/a.jpg"]
    failed = {f["object"]: f["error"] for f in body["failed"]}
    assert "not found" in failed["Raw/x/gone.jpg"].lower()
    assert "folder" in failed["Raw/x/"].lower()
    # A prefix is never even looked up, let alone deleted.
    assert mock_minio.delete_file.call_count == 1


def test_empty_request_is_a_400(test_client):
    res = test_client.post("/api/files/delete_many", json={"objects": []})
    assert res.status_code == 400
