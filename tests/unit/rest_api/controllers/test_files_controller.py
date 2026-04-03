"""Tests for the File controller.

This controller is special: it uses minio_storage_provider (a module-level
variable) rather than an API class. We mock the minio_storage_provider
directly.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


MINIO_PATH = "gemini.rest_api.controllers.files.minio_storage_provider"


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
