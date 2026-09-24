"""Image endpoints must not pull whole (possibly multi-GB) objects into the
API process.

- EXIF GPS lives in the first few KB, so the /image-gps backfill and the
  chunked-upload finalize read a bounded range, and remember images that
  have no GPS instead of downloading them again on every call.
- Thumbnails refuse sources over a size cap before downloading anything,
  and close the MinIO stream they do open.
"""
import io
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from gemini.rest_api.controllers import files

PROVIDER = "gemini.rest_api.controllers.files.minio_storage_provider"
MAX_EXIF_READ = 256 * 1024


def _jpeg(size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def _ranged_response(data: bytes):
    resp = MagicMock()
    resp.read.return_value = data
    return resp


@pytest.fixture
def minio():
    with patch(PROVIDER) as provider:
        provider.bucket_exists.return_value = True
        provider.client.get_object.side_effect = lambda *a, **kw: _ranged_response(_jpeg())
        yield provider


def _assert_bounded_reads(minio):
    minio.download_file_stream.assert_not_called()
    assert minio.client.get_object.call_count >= 1
    for call in minio.client.get_object.call_args_list:
        assert call.kwargs.get("offset") == 0
        assert 0 < call.kwargs.get("length", 0) <= MAX_EXIF_READ


@contextmanager
def _image_gps_env(cached_rows):
    session = MagicMock()
    session.execute.return_value.all.return_value = cached_rows
    engine = MagicMock()

    @contextmanager
    def get_session():
        yield session

    engine.get_session = get_session
    with patch("gemini.db.core.base.db_engine", engine), \
         patch.object(files, "_synced_positions", return_value={}), \
         patch.object(files, "_update_experiment_file_metadata") as update:
        yield update


class TestImageGpsBackfill:
    def test_reads_only_the_exif_head(self, minio, test_client):
        minio.list_files_with_metadata.return_value = [{"object_name": "Raw/ortho.tif"}]
        with _image_gps_env(cached_rows=[]):
            res = test_client.get("/api/files/image-gps/gemini/Raw/")
        assert res.status_code == 200, res.text
        _assert_bounded_reads(minio)

    def test_image_without_gps_is_remembered(self, minio, test_client):
        minio.list_files_with_metadata.return_value = [{"object_name": "Raw/thermal.jpg"}]
        with _image_gps_env(cached_rows=[]) as update:
            test_client.get("/api/files/image-gps/gemini/Raw/")
        update.assert_called_once_with(
            bucket="gemini", object_name="Raw/thermal.jpg", patch={"gps": {}}
        )

    def test_remembered_image_is_not_read_again(self, minio, test_client):
        minio.list_files_with_metadata.return_value = [{"object_name": "Raw/thermal.jpg"}]
        row = MagicMock(object_name="Raw/thermal.jpg", metadata_json={"gps": {}})
        with _image_gps_env(cached_rows=[row]):
            res = test_client.get("/api/files/image-gps/gemini/Raw/")
        assert res.json()["images"] == [{"name": "thermal.jpg", "lat": None, "lon": None, "alt": None}]
        minio.client.get_object.assert_not_called()
        minio.download_file_stream.assert_not_called()

    def test_read_failure_is_not_remembered(self, minio, test_client):
        minio.list_files_with_metadata.return_value = [{"object_name": "Raw/a.jpg"}]
        minio.client.get_object.side_effect = ConnectionError("minio down")
        with _image_gps_env(cached_rows=[]) as update:
            res = test_client.get("/api/files/image-gps/gemini/Raw/")
        assert res.status_code == 200
        update.assert_not_called()


@patch("gemini.rest_api.controllers.files._chunk_uploads", {})
def test_chunk_finalize_reads_only_the_exif_head(minio, test_client):
    files._chunk_uploads["gps-test"] = {
        "upload_id": "upload-xyz",
        "bucket_name": "gemini",
        "object_name": "Raw/ortho.tif",
        "parts": {1: "etag-1"},
        "total": 2,
    }
    minio.upload_part.return_value = "etag-2"
    with patch.object(files, "_record_experiment_file"), \
         patch.object(files, "_update_experiment_file_metadata"):
        res = test_client.post(
            "/api/files/upload_chunk",
            data={
                "chunk_index": "1",
                "total_chunks": "2",
                "file_identifier": "gps-test",
                "object_name": "Raw/ortho.tif",
                "bucket_name": "gemini",
                "experiment_id": "00000000-0000-0000-0000-000000000001",
            },
            files={"file_chunk": ("c1.bin", io.BytesIO(b"x"), "application/octet-stream")},
        )
    assert res.status_code == 201, res.text
    _assert_bounded_reads(minio)


class TestThumbnail:
    def _source(self, minio, size_bytes, data=None):
        minio.file_exists.side_effect = lambda object_name, bucket_name: not object_name.startswith(".thumbnails/")
        minio.get_file_metadata.return_value = {"size": size_bytes}
        stream = MagicMock()
        stream.read.side_effect = io.BytesIO(data or _jpeg()).read
        minio.download_file_stream.return_value = stream
        return stream

    def test_oversized_source_is_refused_without_downloading(self, minio, test_client):
        self._source(minio, size_bytes=5 * 1024 ** 3)
        res = test_client.get("/api/files/thumbnail/gemini/Raw/ortho.tif")
        assert res.status_code == 413
        minio.download_file_stream.assert_not_called()

    def test_source_stream_is_closed(self, minio, test_client):
        stream = self._source(minio, size_bytes=10_000)
        res = test_client.get("/api/files/thumbnail/gemini/Raw/a.jpg", params={"size": 32})
        assert res.status_code == 200, res.text
        assert Image.open(io.BytesIO(res.content)).size[0] <= 32
        stream.close.assert_called_once()
        stream.release_conn.assert_called_once()

    def test_decompression_bomb_is_refused(self, minio, test_client):
        self._source(minio, size_bytes=10_000, data=_jpeg((400, 400)))
        with patch.object(Image, "MAX_IMAGE_PIXELS", 100):
            res = test_client.get("/api/files/thumbnail/gemini/Raw/a.jpg")
        assert res.status_code == 413
