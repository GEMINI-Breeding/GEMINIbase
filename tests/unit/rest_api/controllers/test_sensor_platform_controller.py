"""Tests for the SensorPlatform controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import SensorPlatformOutput, ExperimentOutput, SensorOutput


API_PATH = "gemini.rest_api.controllers.sensor_platform.SensorPlatform"


@pytest.fixture
def mock_output():
    return {
        "id": "sp-uuid",
        "sensor_platform_name": "Platform A",
        "sensor_platform_info": {},
    }


class TestGetAllSensorPlatforms:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [SensorPlatformOutput(**mock_output)]
        response = test_client.get("/api/sensor_platforms/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/sensor_platforms/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/sensor_platforms/all")
        assert response.status_code == 500


class TestGetSensorPlatforms:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [SensorPlatformOutput(**mock_output)]
        response = test_client.get("/api/sensor_platforms", params={"sensor_platform_name": "Platform A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/sensor_platforms", params={"sensor_platform_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetSensorPlatformById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = SensorPlatformOutput(**mock_output)
        response = test_client.get("/api/sensor_platforms/id/sp-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensor_platforms/id/missing")
        assert response.status_code == 404


class TestCreateSensorPlatform:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = SensorPlatformOutput(**mock_output)
        response = test_client.post("/api/sensor_platforms", json={
            "sensor_platform_name": "Platform A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/sensor_platforms", json={
            "sensor_platform_name": "Platform A",
        })
        assert response.status_code == 500


class TestUpdateSensorPlatform:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = SensorPlatformOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/sensor_platforms/id/sp-uuid", json={
            "sensor_platform_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/sensor_platforms/id/missing", json={
            "sensor_platform_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteSensorPlatform:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensor_platforms/id/sp-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/sensor_platforms/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensor_platforms/id/sp-uuid")
        assert response.status_code == 500


class TestSensorPlatformAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensor_platforms/id/sp-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_sensors(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_sensors.return_value = [SensorOutput(
            id="s1", sensor_name="Sensor A", sensor_type_id=1,
            sensor_data_type_id=1, sensor_data_format_id=1, sensor_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensor_platforms/id/sp-uuid/sensors")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_association_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensor_platforms/id/missing/experiments")
        assert response.status_code == 404
