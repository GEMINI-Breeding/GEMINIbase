"""Tests for the Model controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    ModelOutput, ExperimentOutput, ModelRunOutput,
    DatasetOutput, ModelRecordOutput
)


API_PATH = "gemini.rest_api.controllers.model.Model"
RECORD_PATH = "gemini.rest_api.controllers.model.ModelRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "model-uuid",
        "model_name": "Model A",
        "model_url": "http://example.com",
        "model_info": {},
    }


class TestGetAllModels:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [ModelOutput(**mock_output)]
        response = test_client.get("/api/models/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/models/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/models/all")
        assert response.status_code == 500


class TestGetModels:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [ModelOutput(**mock_output)]
        response = test_client.get("/api/models", params={"model_name": "Model A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/models", params={"model_name": "Missing"})
        assert response.status_code == 404

    @patch(API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/models", params={"model_name": "Model A"})
        assert response.status_code == 500


class TestGetModelById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = ModelOutput(**mock_output)
        response = test_client.get("/api/models/id/model-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/models/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/models/id/model-uuid")
        assert response.status_code == 500


class TestCreateModel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = ModelOutput(**mock_output)
        response = test_client.post("/api/models", json={
            "model_name": "Model A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/models", json={
            "model_name": "Model A",
        })
        assert response.status_code == 500


class TestUpdateModel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = ModelOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/models/id/model-uuid", json={
            "model_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/models/id/missing", json={
            "model_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteModel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/models/id/model-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/models/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/models/id/model-uuid")
        assert response.status_code == 500


class TestModelAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_runs(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_runs.return_value = [ModelRunOutput(
            id="r1", model_name="Model A", model_run_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/runs")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_datasets(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = [DatasetOutput(
            id="d1", dataset_name="DS", collection_date=None,
            dataset_info={}, dataset_type_id=0
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/datasets")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_association_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/models/id/missing/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/models/id/model-uuid/experiments")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_runs_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/models/id/missing/runs")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_runs_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_runs.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/runs")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_runs_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/models/id/model-uuid/runs")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_datasets_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/models/id/missing/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/models/id/model-uuid/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/models/id/model-uuid/datasets")
        assert response.status_code == 500


class TestModelRecords:

    @patch(RECORD_PATH)
    def test_get_record_by_id_success(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = ModelRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", model_id="m1",
            model_name="Model A", model_data={}, dataset_id="d1",
            dataset_name="DS", collection_date=None,
            experiment_id=None, experiment_name=None,
            season_id=None, season_name=None,
            site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        response = test_client.get("/api/models/records/id/r1")
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_get_record_by_id_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.get("/api/models/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_get_record_by_id_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/models/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = True
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/models/records/id/r1")
        assert response.status_code in (200, 204)

    @patch(RECORD_PATH)
    def test_delete_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.delete("/api/models/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_delete_record_fails(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = False
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/models/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/models/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_update_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.update.return_value = ModelRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", model_id="m1",
            model_name="Model A", model_data={"updated": True}, dataset_id="d1",
            dataset_name="DS", collection_date=None,
            experiment_id=None, experiment_name=None,
            season_id=None, season_name=None,
            site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.patch("/api/models/records/id/r1", json={
            "model_data": {"updated": True},
        })
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_update_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.patch("/api/models/records/id/missing", json={
            "model_data": {},
        })
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_update_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/models/records/id/r1", json={
            "model_data": {},
        })
        assert response.status_code == 500
