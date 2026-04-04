"""Tests for the GeoJSON controller."""
import io
import json
import pytest
from unittest.mock import patch, MagicMock


MINIO_PATH = "gemini.rest_api.controllers.geojson.minio_storage_provider"


class TestLoadGeoJson:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        geojson = {"type": "FeatureCollection", "features": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(geojson).encode("utf-8")
        mock_response.close = MagicMock()
        mock_response.release_conn = MagicMock()
        mock_minio.download_file_stream.return_value = mock_response

        response = test_client.post(
            "/api/geojson/load",
            json={"file_path": "data/test.geojson"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []

    @patch(MINIO_PATH)
    def test_file_not_found(self, mock_minio, test_client):
        mock_minio.download_file_stream.side_effect = Exception("NoSuchKey")
        response = test_client.post(
            "/api/geojson/load",
            json={"file_path": "data/missing.geojson"},
        )
        assert response.status_code == 500

    @patch(MINIO_PATH)
    def test_custom_bucket(self, mock_minio, test_client):
        geojson = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(geojson).encode("utf-8")
        mock_response.close = MagicMock()
        mock_response.release_conn = MagicMock()
        mock_minio.download_file_stream.return_value = mock_response

        response = test_client.post(
            "/api/geojson/load",
            json={"file_path": "data/test.geojson", "bucket_name": "custom-bucket"},
        )
        assert response.status_code == 201
        mock_minio.download_file_stream.assert_called_once_with(
            object_name="data/test.geojson",
            bucket_name="custom-bucket",
        )


class TestSaveGeoJson:

    @patch(MINIO_PATH)
    def test_success(self, mock_minio, test_client):
        mock_minio.upload_file.return_value = "http://minio/bucket/test.geojson"
        geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}}]}

        response = test_client.post(
            "/api/geojson/save",
            json={"file_path": "output/test.geojson", "geojson": geojson},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["file_path"] == "output/test.geojson"
        assert data["size"] > 0
        mock_minio.upload_file.assert_called_once()

    @patch(MINIO_PATH)
    def test_upload_error(self, mock_minio, test_client):
        mock_minio.upload_file.side_effect = Exception("Storage full")
        response = test_client.post(
            "/api/geojson/save",
            json={"file_path": "output/test.geojson", "geojson": {}},
        )
        assert response.status_code == 500
