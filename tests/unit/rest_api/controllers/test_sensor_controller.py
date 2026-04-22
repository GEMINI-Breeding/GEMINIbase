"""Tests for the Sensor controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    SensorOutput, ExperimentOutput, SensorPlatformOutput,
    DatasetOutput, SensorRecordOutput
)


API_PATH = "gemini.rest_api.controllers.sensor.Sensor"
RECORD_PATH = "gemini.rest_api.controllers.sensor.SensorRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "sensor-uuid",
        "sensor_name": "Sensor A",
        "sensor_type_id": 1,
        "sensor_data_type_id": 1,
        "sensor_data_format_id": 1,
        "sensor_info": {},
    }


class TestGetAllSensors:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [SensorOutput(**mock_output)]
        response = test_client.get("/api/sensors/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/sensors/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/all")
        assert response.status_code == 500


class TestGetSensors:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [SensorOutput(**mock_output)]
        response = test_client.get("/api/sensors", params={"sensor_name": "Sensor A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/sensors", params={"sensor_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors", params={"sensor_name": "Sensor A"})
        assert response.status_code == 500


class TestGetSensorById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = SensorOutput(**mock_output)
        response = test_client.get("/api/sensors/id/sensor-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensors/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/id/sensor-uuid")
        assert response.status_code == 500


class TestCreateSensor:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = SensorOutput(**mock_output)
        response = test_client.post("/api/sensors", json={
            "sensor_name": "Sensor A",
            "sensor_type_id": 0,
            "sensor_data_type_id": 0,
            "sensor_data_format_id": 0,
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/sensors", json={
            "sensor_name": "Sensor A",
            "sensor_type_id": 0,
            "sensor_data_type_id": 0,
            "sensor_data_format_id": 0,
        })
        assert response.status_code == 500


class TestUpdateSensor:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = SensorOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/sensors/id/sensor-uuid", json={
            "sensor_name": "Updated",
            "sensor_type_id": 1,
            "sensor_data_type_id": 1,
            "sensor_data_format_id": 1,
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/sensors/id/missing", json={
            "sensor_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteSensor:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensors/id/sensor-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/sensors/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/sensors/id/sensor-uuid")
        assert response.status_code == 500


class TestSensorAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_sensor_platforms(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_sensor_platforms.return_value = [SensorPlatformOutput(
            id="sp1", sensor_platform_name="Platform", sensor_platform_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/sensor_platforms")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_datasets(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = [DatasetOutput(
            id="d1", dataset_name="DS", collection_date=None,
            dataset_info={}, dataset_type_id=0
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/datasets")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_experiments_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensors/id/missing/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/experiments")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_experiments_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/id/sensor-uuid/experiments")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_sensor_platforms_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensors/id/missing/sensor_platforms")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_sensor_platforms_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_sensor_platforms.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/sensor_platforms")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_sensor_platforms_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/id/sensor-uuid/sensor_platforms")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_datasets_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensors/id/missing/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/sensors/id/sensor-uuid/datasets")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_datasets_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/id/sensor-uuid/datasets")
        assert response.status_code == 500


class TestSensorRecords:

    @patch(RECORD_PATH)
    def test_get_record_by_id_success(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = SensorRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", sensor_id="s1",
            sensor_name="Sensor A", sensor_data={}, collection_date=None,
            dataset_id=None, dataset_name=None, experiment_id=None,
            experiment_name=None, season_id=None, season_name=None,
            site_id=None, site_name=None, plot_id=None, plot_number=None,
            plot_row_number=None, plot_column_number=None,
            record_file=None, record_info=None
        )
        response = test_client.get("/api/sensors/records/id/r1")
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_get_record_by_id_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.get("/api/sensors/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_get_record_by_id_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sensors/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = True
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/sensors/records/id/r1")
        assert response.status_code in (200, 204)

    @patch(RECORD_PATH)
    def test_delete_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.delete("/api/sensors/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_delete_record_fails(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = False
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/sensors/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/sensors/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_update_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.update.return_value = SensorRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", sensor_id="s1",
            sensor_name="Sensor A", sensor_data={"updated": True}, collection_date=None,
            dataset_id=None, dataset_name=None, experiment_id=None,
            experiment_name=None, season_id=None, season_name=None,
            site_id=None, site_name=None, plot_id=None, plot_number=None,
            plot_row_number=None, plot_column_number=None,
            record_file=None, record_info=None
        )
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.patch("/api/sensors/records/id/r1", json={
            "sensor_data": {"updated": True},
        })
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_update_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.patch("/api/sensors/records/id/missing", json={
            "sensor_data": {},
        })
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_update_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/sensors/records/id/r1", json={
            "sensor_data": {},
        })
        assert response.status_code == 500
