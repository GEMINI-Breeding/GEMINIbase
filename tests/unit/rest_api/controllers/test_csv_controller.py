"""Tests for the CSV controller."""
import pytest
from unittest.mock import patch, MagicMock


MINIO_PATH = "gemini.rest_api.controllers.csv_data.minio_storage_provider"


class TestSaveCsv:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.upload_file.return_value = "http://minio/bucket/test.csv"
        response = test_client.post(
            "/api/csv/save",
            json={
                "file_path": "output/traits.csv",
                "headers": ["plot", "trait", "value"],
                "rows": [["1", "height", "1.5"], ["2", "height", "1.8"]],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["file_path"] == "output/traits.csv"
        assert data["size"] > 0
        mock_minio.upload_file.assert_called_once()

    @patch(MINIO_PATH)
    def test_empty_rows(self, mock_minio, test_client):
        mock_minio.upload_file.return_value = "http://minio/bucket/empty.csv"
        response = test_client.post(
            "/api/csv/save",
            json={"file_path": "output/empty.csv", "headers": ["a", "b"], "rows": []},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"

    @patch(MINIO_PATH)
    def test_upload_error(self, mock_minio, test_client):
        mock_minio.upload_file.side_effect = Exception("Connection refused")
        response = test_client.post(
            "/api/csv/save",
            json={"file_path": "output/fail.csv", "headers": ["x"], "rows": [["1"]]},
        )
        assert response.status_code == 500


class TestDownloadCsv:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_stream = MagicMock()
        mock_stream.stream.return_value = iter([b"plot,trait,value\n", b"1,height,1.5\n"])
        mock_minio.download_file_stream.return_value = mock_stream

        response = test_client.get("/api/csv/download/test-bucket/output/traits.csv")
        # Path pattern matches FileController: [1]=bucket, [2:]=object
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    @patch(MINIO_PATH)
    def test_file_not_found(self, mock_minio, test_client):
        mock_minio.download_file_stream.side_effect = Exception("NoSuchKey")
        response = test_client.get("/api/csv/download/test-bucket/missing.csv")
        assert response.status_code == 500
