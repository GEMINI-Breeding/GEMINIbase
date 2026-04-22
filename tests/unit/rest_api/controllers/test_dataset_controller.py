"""Tests for the Dataset controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import DatasetOutput, ExperimentOutput, DatasetRecordOutput


API_PATH = "gemini.rest_api.controllers.dataset.Dataset"
RECORD_PATH = "gemini.rest_api.controllers.dataset.DatasetRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "ds-uuid",
        "dataset_name": "Dataset A",
        "collection_date": None,
        "dataset_info": {},
        "dataset_type_id": 0,
    }


class TestGetAllDatasets:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [DatasetOutput(**mock_output)]
        response = test_client.get("/api/datasets/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/datasets/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/datasets/all")
        assert response.status_code == 500


class TestGetDatasets:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [DatasetOutput(**mock_output)]
        response = test_client.get("/api/datasets", params={"dataset_name": "Dataset A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/datasets", params={"dataset_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/datasets", params={"dataset_name": "Dataset A"})
        assert response.status_code == 500


class TestGetDatasetById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = DatasetOutput(**mock_output)
        response = test_client.get("/api/datasets/id/ds-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/datasets/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/datasets/id/ds-uuid")
        assert response.status_code == 500


class TestCreateDataset:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = DatasetOutput(**mock_output)
        response = test_client.post("/api/datasets", json={
            "dataset_name": "Dataset A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/datasets", json={
            "dataset_name": "Dataset A",
        })
        assert response.status_code == 500


class TestUpdateDataset:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = DatasetOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/datasets/id/ds-uuid", json={
            "dataset_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/datasets/id/missing", json={
            "dataset_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteDataset:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/datasets/id/ds-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/datasets/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/datasets/id/ds-uuid")
        assert response.status_code == 500


class TestDatasetAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/datasets/id/ds-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_experiments_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/datasets/id/missing/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_experiments_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/datasets/id/ds-uuid/experiments")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_experiments_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/datasets/id/ds-uuid/experiments")
        assert response.status_code == 500


class TestDatasetRecords:

    @patch(RECORD_PATH)
    def test_get_record_by_id_success(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = DatasetRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", dataset_id="d1",
            dataset_name="DS A", dataset_data={}, collection_date=None,
            experiment_id=None, experiment_name=None, season_id=None,
            season_name=None, site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        response = test_client.get("/api/datasets/records/id/r1")
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_get_record_by_id_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.get("/api/datasets/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_get_record_by_id_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/datasets/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = True
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/datasets/records/id/r1")
        assert response.status_code in (200, 204)

    @patch(RECORD_PATH)
    def test_delete_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.delete("/api/datasets/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_delete_record_fails(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = False
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/datasets/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/datasets/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_update_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.update.return_value = DatasetRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", dataset_id="d1",
            dataset_name="DS A", dataset_data={"updated": True}, collection_date=None,
            experiment_id=None, experiment_name=None, season_id=None,
            season_name=None, site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.patch("/api/datasets/records/id/r1", json={
            "dataset_data": {"updated": True},
        })
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_update_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.patch("/api/datasets/records/id/missing", json={
            "dataset_data": {},
        })
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_update_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/datasets/records/id/r1", json={
            "dataset_data": {},
        })
        assert response.status_code == 500
