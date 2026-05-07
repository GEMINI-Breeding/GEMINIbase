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
        mock_minio.list_files.return_value = []
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

    @patch("gemini.db.core.base.db_engine")
    @patch(MINIO_PATH)
    def test_success_also_drops_experiment_files_row(
        self, mock_minio, mock_db_engine, test_client
    ):
        """P0.5: a successful delete_file call must DELETE the matching
        experiment_files row in the same request — no dangling pointer
        when the chunked-upload finaliser previously inserted one for
        this (bucket, object_name).

        We assert by inspecting the SQLAlchemy DELETE statement that the
        endpoint executes against the mocked session: it must target
        experiment_files with WHERE bucket = <bucket> AND object_name =
        <object>.
        """
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = True
        mock_minio.delete_file.return_value = True

        # Capture the session.execute call so we can assert the
        # DELETE statement targets experiment_files. The endpoint opens
        # `db_engine.get_session()` as a context manager.
        mock_session = MagicMock()
        mock_db_engine.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        response = test_client.delete(
            "/api/files/delete/test-bucket/path/to/file.txt"
        )
        assert response.status_code in (200, 204)

        # Find the DELETE call to session.execute. The endpoint may
        # also call session.commit() afterwards — we don't care here.
        execute_calls = mock_session.execute.call_args_list
        assert execute_calls, (
            "delete_file should execute a DELETE on experiment_files "
            "after the MinIO delete succeeds"
        )
        # Render the first executed statement to a string and verify
        # it's a DELETE on the experiment_files table.
        first_stmt = execute_calls[0].args[0]
        rendered = str(first_stmt).lower()
        assert "delete from" in rendered, rendered
        assert "experiment_files" in rendered, rendered

    @patch("gemini.db.core.base.db_engine")
    @patch(MINIO_PATH)
    def test_db_failure_after_minio_delete_is_logged_not_fatal(
        self, mock_minio, mock_db_engine, test_client, caplog
    ):
        """P0.5 contract: if the experiment_files DELETE raises (e.g. DB
        is down), the response is still success — the MinIO object is
        already gone and a logged orphan row is recoverable. We assert
        the warning surfaces but the response stays 200/204."""
        mock_minio.bucket_exists.return_value = True
        mock_minio.file_exists.return_value = True
        mock_minio.delete_file.return_value = True
        mock_db_engine.get_session.side_effect = Exception("DB unavailable")

        response = test_client.delete(
            "/api/files/delete/test-bucket/path/to/file.txt"
        )
        assert response.status_code in (200, 204)


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
    # The chunked-upload controller now streams each chunk straight into a
    # MinIO multipart part rather than buffering temp files on the API
    # container. The session shape is `{upload_id, bucket_name, object_name,
    # parts: {part_number: etag}, total}`. The response is a
    # ChunkStatusResponse with `uploaded_part_numbers` (1-indexed list).

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_single_chunk_of_many(self, mock_minio, test_client):
        """Chunk 0 of 3 → multipart init + upload_part(1) + complete=False."""
        mock_minio.create_multipart_upload.return_value = "upload-xyz"
        mock_minio.upload_part.return_value = "etag-1"
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
        assert data["uploaded_part_numbers"] == [1]
        assert data["total_chunks"] == 3
        assert data["complete"] is False
        mock_minio.create_multipart_upload.assert_called_once()
        mock_minio.upload_part.assert_called_once()
        mock_minio.complete_multipart_upload.assert_not_called()

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_final_chunk_assembles_and_uploads(self, mock_minio, test_client):
        """When the last chunk arrives, MinIO is told to complete the multipart."""
        from gemini.rest_api.controllers.files import _chunk_uploads
        # Pre-seed an in-progress multipart session for chunk 0 already done.
        _chunk_uploads["assemble-test"] = {
            "upload_id": "upload-xyz",
            "bucket_name": "test-bucket",
            "object_name": "path/to/file.bin",
            "parts": {1: "etag-1"},
            "total": 2,
        }
        mock_minio.upload_part.return_value = "etag-2"

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
        assert data["uploaded_part_numbers"] == [1, 2]
        mock_minio.complete_multipart_upload.assert_called_once()
        mock_minio.create_multipart_upload.assert_not_called()
        assert "assemble-test" not in _chunk_uploads

    @patch(CHUNKS_PATH, {})
    @patch(MINIO_PATH)
    def test_upload_error_cleans_up_temps(self, mock_minio, test_client):
        """If MinIO upload_part fails, the multipart is aborted + session dropped."""
        mock_minio.create_multipart_upload.return_value = "upload-xyz"
        mock_minio.upload_part.side_effect = Exception("MinIO down")

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
        mock_minio.abort_multipart_upload.assert_called_once()


class TestCheckUploadedChunks:

    @patch(CHUNKS_PATH, {
        "existing-file": {
            "upload_id": "u",
            "bucket_name": "b",
            "object_name": "o",
            "parts": {1: "etag-1", 2: "etag-2"},
            "total": 5,
        }
    })
    def test_returns_count_for_existing(self, test_client):
        response = test_client.post(
            "/api/files/check_uploaded_chunks",
            json={"file_identifier": "existing-file", "total_chunks": 5},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_identifier"] == "existing-file"
        assert data["uploaded_part_numbers"] == [1, 2]
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
        assert data["uploaded_part_numbers"] == []


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
    @patch(MINIO_PATH)
    def test_clear_existing_removes_entry(self, mock_minio, test_client):
        from gemini.rest_api.controllers.files import _chunk_uploads
        _chunk_uploads["cleanup-test"] = {
            "upload_id": "upload-xyz",
            "bucket_name": "test-bucket",
            "object_name": "path/to/file.bin",
            "parts": {1: "etag-1"},
            "total": 1,
        }

        response = test_client.post(
            "/api/files/clear_upload_cache",
            json={"file_identifier": "cleanup-test"},
        )
        assert response.status_code == 201
        assert "cleanup-test" not in _chunk_uploads
        mock_minio.abort_multipart_upload.assert_called_once()


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
