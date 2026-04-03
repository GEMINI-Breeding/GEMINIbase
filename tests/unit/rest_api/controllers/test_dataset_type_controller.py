"""Tests for the DatasetType controller.

Note: This controller uses int IDs (dataset_type_id:int).
"""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import DatasetTypeOutput


API_PATH = "gemini.rest_api.controllers.dataset_type.DatasetType"


@pytest.fixture
def mock_output():
    return {
        "id": 1,
        "dataset_type_name": "Sensor Data",
        "dataset_type_info": {},
    }


class TestGetAllDatasetTypes:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [DatasetTypeOutput(**mock_output)]
        response = test_client.get("/api/dataset_types/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/dataset_types/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/dataset_types/all")
        assert response.status_code == 500


class TestGetDatasetTypes:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [DatasetTypeOutput(**mock_output)]
        response = test_client.get("/api/dataset_types", params={"dataset_type_name": "Sensor Data"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/dataset_types", params={"dataset_type_name": "Missing"})
        assert response.status_code == 404


class TestGetDatasetTypeById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = DatasetTypeOutput(**mock_output)
        response = test_client.get("/api/dataset_types/id/1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/dataset_types/id/999")
        assert response.status_code == 404


class TestCreateDatasetType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = DatasetTypeOutput(**mock_output)
        response = test_client.post("/api/dataset_types", json={
            "dataset_type_name": "Sensor Data",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/dataset_types", json={
            "dataset_type_name": "Sensor Data",
        })
        assert response.status_code == 500


class TestUpdateDatasetType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = DatasetTypeOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/dataset_types/id/1", json={
            "dataset_type_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/dataset_types/id/999", json={
            "dataset_type_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteDatasetType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/dataset_types/id/1")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/dataset_types/id/999")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/dataset_types/id/1")
        assert response.status_code == 500
