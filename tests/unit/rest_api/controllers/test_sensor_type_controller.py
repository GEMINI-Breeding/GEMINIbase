"""Tests for the SensorType controller.

Note: This controller uses int IDs (sensor_type_id:int) rather than string UUIDs.
"""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import SensorTypeOutput


API_PATH = "gemini.rest_api.controllers.sensor_type.SensorType"


@pytest.fixture
def mock_output():
    return {
        "id": 1,
        "sensor_type_name": "Type A",
        "sensor_type_info": {},
    }


class TestGetAllSensorTypes:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [SensorTypeOutput(**mock_output)]
        response = test_client.get("/api/sensor_types/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/sensor_types/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/sensor_types/all")
        assert response.status_code == 500


class TestGetSensorTypes:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [SensorTypeOutput(**mock_output)]
        response = test_client.get("/api/sensor_types", params={"sensor_type_name": "Type A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/sensor_types", params={"sensor_type_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetSensorTypeById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = SensorTypeOutput(**mock_output)
        response = test_client.get("/api/sensor_types/id/1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensor_types/id/999")
        assert response.status_code == 404


class TestCreateSensorType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = SensorTypeOutput(**mock_output)
        response = test_client.post("/api/sensor_types", json={
            "sensor_type_name": "Type A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/sensor_types", json={
            "sensor_type_name": "Type A",
        })
        assert response.status_code == 500


class TestUpdateSensorType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = SensorTypeOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/sensor_types/id/1", json={
            "sensor_type_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/sensor_types/id/999", json={
            "sensor_type_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteSensorType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensor_types/id/1")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/sensor_types/id/999")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensor_types/id/1")
        assert response.status_code == 500
