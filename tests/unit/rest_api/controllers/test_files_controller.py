"""Tests for the File controller.

This controller is special: it uses minio_storage_provider (a module-level
variable) rather than an API class. We mock the minio_storage_provider
directly.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


MINIO_PATH = "gemini.rest_api.controllers.files.minio_storage_provider"
CHUNKS_PATH = "gemini.rest_api.controllers.files._chunk_uploads"


class TestGetFileMetadata:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = True
        mock_minio.get_file_metadata.return_value = {
            "bucket_name": "test-bucket",
            "object_name": "file.txt",
            "size": 1024,
            "last_modified": datetime(2024, 1, 1),
            "content_type": "text/plain",
            "etag": "abc123",
        }
        response = test_client.get("/api/files/metadata/test-bucket/file.txt")
        assert response.status_code == 200
        data = response.json()
        assert data["object_name"] == "file.txt"

    @patch(MINIO_PATH)
    def test_bucket_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = False
        response = test_client.get("/api/files/metadata/missing-bucket/file.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_file_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = False
        response = test_client.get("/api/files/metadata/test-bucket/missing.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_error(self, mock_minio, test_client):
        mock_minio.bucket_exists.side_effect = Exception("Connection error")
        response = test_client.get("/api/files/metadata/test-bucket/file.txt")
        assert response.status_code == 500


class TestListFiles:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.list_files.return_value = ["file1.txt", "file2.txt"]
        mock_minio.get_file_metadata.return_value = {
            "bucket_name": "test-bucket",
            "object_name": "file1.txt",
            "size": 1024,
            "last_modified": datetime(2024, 1, 1),
            "content_type": "text/plain",
            "etag": "abc123",
        }
        response = test_client.get("/api/files/list/test-bucket/path/to")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch(MINIO_PATH)
    def test_bucket_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = False
        response = test_client.get("/api/files/list/missing-bucket/path")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_empty_list(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.list_files.return_value = []
        response = test_client.get("/api/files/list/test-bucket/path")
        assert response.status_code == 200
        assert response.json() == []

    @patch(MINIO_PATH)
    def test_error(self, mock_minio, test_client):
        mock_minio.bucket_exists.side_effect = Exception("Connection error")
        response = test_client.get("/api/files/list/test-bucket/path")
        assert response.status_code == 500


class TestDeleteFile:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = True
        mock_minio.delete_file.return_value = True
        response = test_client.delete("/api/files/delete/test-bucket/file.txt")
        assert response.status_code in (200, 204)

    @patch(MINIO_PATH)
    def test_bucket_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = False
        response = test_client.delete("/api/files/delete/missing-bucket/file.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_file_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = False
        response = test_client.delete("/api/files/delete/test-bucket/missing.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_delete_fails(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = True
        mock_minio.delete_file.return_value = False
        response = test_client.delete("/api/files/delete/test-bucket/file.txt")
        assert response.status_code == 500

    @patch(MINIO_PATH)
    def test_error(self, mock_minio, test_client):
        mock_minio.bucket_exists.side_effect = Exception("Connection error")
        response = test_client.delete("/api/files/delete/test-bucket/file.txt")
        assert response.status_code == 500


class TestDownloadFile:

    @patch(MINIO_PATH)
    def test_bucket_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = False
        response = test_client.get("/api/files/download/missing-bucket/file.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_file_not_found(self, mock_minio, test_client):
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = False
        response = test_client.get("/api/files/download/test-bucket/missing.txt")
        assert response.status_code == 404

    @patch(MINIO_PATH)
    def test_error(self, mock_minio, test_client):
        mock_minio.bucket_exists.side_effect = Exception("Connection error")
        response = test_client.get("/api/files/download/test-bucket/file.txt")
        assert response.status_code == 500


class TestUploadChunk:

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_single_chunk_of_many(self, mock_minio, test_client):
        """Uploading chunk 0 of 3 should return complete=False."""
        response = test_client.post(
            "/api/files/upload_chunk",
            data={
                "chunk_index": "0",
                "total_chunks": "3",
                "file_identifier": "test-file-abc",
                "object_name": "path/to/file.bin",
                "bucket_name": "test-bucket",
            },
            files={"file_chunk": ("chunk0.bin", io.BytesIO(b"chunk-zero-data"), "application/octet-stream")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_identifier"] == "test-file-abc"
        assert data["uploaded_chunks"] == 1
        assert data["total_chunks"] == 3
        assert data["complete"] is False

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_final_chunk_assembles_and_uploads(self, mock_minio, test_client):
        """When all chunks arrive, the file should be assembled and uploaded to MinIO."""
        import tempfile, os
        # Pre-populate chunk 0
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".chunk0")
        tmp.write(b"part-one-")
        tmp.close()

        from gemini.rest_api.controllers.files import _chunk_uploads
        _chunk_uploads["assemble-test"] = {0: tmp.name}

        mock_minio.upload_file.return_value = "http://minio/test-bucket/file.bin"

        response = test_client.post(
            "/api/files/upload_chunk",
            data={
                "chunk_index": "1",
                "total_chunks": "2",
                "file_identifier": "assemble-test",
                "object_name": "path/to/file.bin",
                "bucket_name": "test-bucket",
            },
            files={"file_chunk": ("chunk1.bin", io.BytesIO(b"part-two"), "application/octet-stream")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["complete"] is True
        assert data["uploaded_chunks"] == 2
        mock_minio.upload_file.assert_called_once()
        # Verify temp chunk files were cleaned up
        assert not os.path.exists(tmp.name)
        assert "assemble-test" not in _chunk_uploads

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_upload_error_cleans_up_temps(self, mock_minio, test_client):
        """If MinIO upload fails, temp files should be cleaned up."""
        mock_minio.upload_file.side_effect = Exception("MinIO down")

        # Upload chunk 0 of 1 — will try to assemble and fail
        response = test_client.post(
            "/api/files/upload_chunk",
            data={
                "chunk_index": "0",
                "total_chunks": "1",
                "file_identifier": "fail-test",
                "object_name": "path/to/file.bin",
                "bucket_name": "test-bucket",
            },
            files={"file_chunk": ("chunk0.bin", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert response.status_code == 500
        from gemini.rest_api.controllers.files import _chunk_uploads
        assert "fail-test" not in _chunk_uploads


class TestCheckUploadedChunks:

    @patch(CHUNKS_PATH, {"existing-file": {0: "/tmp/a", 1: "/tmp/b"}})
    def test_returns_count_for_existing(self, test_client):
        response = test_client.post(
            "/api/files/check_uploaded_chunks",
            json={"file_identifier": "existing-file", "total_chunks": 5},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_identifier"] == "existing-file"
        assert data["uploaded_chunks"] == 2
        assert data["total_chunks"] == 5
        assert data["complete"] is False

    @patch(CHUNKS_PATH, {})
    def test_returns_zero_for_unknown(self, test_client):
        response = test_client.post(
            "/api/files/check_uploaded_chunks",
            json={"file_identifier": "unknown-file", "total_chunks": 3},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["uploaded_chunks"] == 0


class TestClearUploadCache:

    @patch(CHUNKS_PATH, {})
    def test_clear_nonexistent_is_ok(self, test_client):
        response = test_client.post(
            "/api/files/clear_upload_cache",
            json={"file_identifier": "no-such-file"},
        )
        assert response.status_code == 201
        assert response.json()["status"] == "ok"

    @patch(CHUNKS_PATH, {})
    def test_clear_existing_removes_entry(self, test_client):
        import tempfile
        from gemini.rest_api.controllers.files import _chunk_uploads
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".chunk0")
        tmp.write(b"data")
        tmp.close()
        _chunk_uploads["cleanup-test"] = {0: tmp.name}

        response = test_client.post(
            "/api/files/clear_upload_cache",
            json={"file_identifier": "cleanup-test"},
        )
        assert response.status_code == 201
        assert "cleanup-test" not in _chunk_uploads
        import os
        assert not os.path.exists(tmp.name)


class TestPresignUrl:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.get_download_url.return_value = "https://minio.local/test-bucket/file.txt?X-Amz-Signature=abc"
        response = test_client.get("/api/files/presign/test-bucket/file.txt")
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"].startswith("https://")
        assert data["expires_in_seconds"] == 3600

    @patch(MINIO_PATH)
    def test_custom_expiry(self, mock_minio, test_client):
        mock_minio.get_download_url.return_value = "https://minio.local/bucket/file.txt"
        response = test_client.get("/api/files/presign/test-bucket/file.txt?expires_seconds=7200")
        assert response.status_code == 200
        assert response.json()["expires_in_seconds"] == 7200

    @patch(MINIO_PATH)
    def test_error(self, mock_minio, test_client):
        mock_minio.get_download_url.side_effect = Exception("File not found")
        response = test_client.get("/api/files/presign/test-bucket/missing.txt")
        assert response.status_code == 500
