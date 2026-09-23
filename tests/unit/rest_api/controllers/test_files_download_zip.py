"""POST /api/files/download_zip — many files, one archive."""
import io
import zipfile
from unittest.mock import MagicMock, patch

MINIO = "gemini.rest_api.controllers.files.minio_storage_provider"

BODIES = {
    "Processed/S/E/D/P/2024-06-01/DJI/RGB/PlotImages/plot_1.png": b"png-a",
    "Processed/S/E/D/P/2024-07-01/DJI/RGB/PlotImages/plot_1.png": b"png-b",
    "Processed/S/E/D/P/2024-06-01/DJI/RGB/traits/v1.geojson": b'{"a":1}',
}


def _stream(object_name, bucket_name=None):
    name = object_name
    if name not in BODIES:
        raise FileNotFoundError(name)
    body = BODIES[name]
    s = MagicMock()
    s.stream.side_effect = lambda amt=None: iter([body])
    return s


@patch(MINIO)
def test_keeps_relative_paths_so_names_dont_collide(mock_minio, test_client):
    mock_minio.download_file_stream.side_effect = _stream
    res = test_client.post(
        "/api/files/download_zip",
        json={"files": list(BODIES), "filename": "plots"},
    )
    assert res.status_code == 201, res.text
    assert 'filename="plots.zip"' in res.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = sorted(zf.namelist())
    assert names == [
        "2024-06-01/DJI/RGB/PlotImages/plot_1.png",
        "2024-06-01/DJI/RGB/traits/v1.geojson",
        "2024-07-01/DJI/RGB/PlotImages/plot_1.png",
    ]
    assert zf.read("2024-07-01/DJI/RGB/PlotImages/plot_1.png") == b"png-b"
    # Images are stored, text is deflated.
    assert zf.getinfo("2024-06-01/DJI/RGB/PlotImages/plot_1.png").compress_type == zipfile.ZIP_STORED
    assert zf.getinfo("2024-06-01/DJI/RGB/traits/v1.geojson").compress_type == zipfile.ZIP_DEFLATED


@patch(MINIO)
def test_prefix_mode_is_relative_to_the_prefix(mock_minio, test_client):
    # The real provider returns plain object-name strings.
    mock_minio.list_files.return_value = list(BODIES)
    mock_minio.download_file_stream.side_effect = _stream
    res = test_client.post(
        "/api/files/download_zip",
        json={"prefix": "Processed/S/E/D/P/"},
    )
    assert res.status_code == 201, res.text
    names = zipfile.ZipFile(io.BytesIO(res.content)).namelist()
    assert "2024-06-01/DJI/RGB/PlotImages/plot_1.png" in names


@patch(MINIO)
def test_unreadable_files_are_listed_not_dropped(mock_minio, test_client):
    mock_minio.download_file_stream.side_effect = _stream
    res = test_client.post(
        "/api/files/download_zip",
        json={"files": [*BODIES, "Processed/S/E/D/P/gone.png"]},
    )
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    assert "gone.png" in zf.read("MISSING.txt").decode()


@patch(MINIO)
def test_nothing_to_zip_is_a_400(mock_minio, test_client):
    mock_minio.list_files.return_value = []
    res = test_client.post("/api/files/download_zip", json={"prefix": "nope/"})
    assert res.status_code == 400


@patch(MINIO)
def test_list_nested_processed_builds_tree_from_names(mock_minio, test_client):
    mock_minio.list_files.return_value = list(BODIES)
    res = test_client.get("/api/files/list_nested_processed")
    assert res.status_code == 200, res.text
    assert res.json() == {"S": {"E": {"D": {"P": ["2024-06-01", "2024-07-01"]}}}}
