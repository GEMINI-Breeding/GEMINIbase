"""Tests for the DataFormat controller.

Note: This controller uses int IDs (data_format_id:int) and has
an association endpoint for data_types.
"""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import DataFormatOutput, DataTypeOutput


API_PATH = "gemini.rest_api.controllers.data_format.DataFormat"


@pytest.fixture
def mock_output():
    return {
        "id": 1,
        "data_format_name": "PNG",
        "data_format_mime_type": "image/png",
        "data_format_info": {},
    }


class TestGetAllDataFormats:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [DataFormatOutput(**mock_output)]
        response = test_client.get("/api/data_formats/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/data_formats/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/data_formats/all")
        assert response.status_code == 500


class TestGetDataFormats:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [DataFormatOutput(**mock_output)]
        response = test_client.get("/api/data_formats", params={"data_format_name": "PNG"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/data_formats", params={"data_format_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetDataFormatById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = DataFormatOutput(**mock_output)
        response = test_client.get("/api/data_formats/id/1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/data_formats/id/999")
        assert response.status_code == 404


class TestCreateDataFormat:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = DataFormatOutput(**mock_output)
        response = test_client.post("/api/data_formats", json={
            "data_format_name": "PNG",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/data_formats", json={
            "data_format_name": "PNG",
        })
        assert response.status_code == 500


class TestUpdateDataFormat:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = DataFormatOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/data_formats/id/1", json={
            "data_format_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/data_formats/id/999", json={
            "data_format_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteDataFormat:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/data_formats/id/1")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/data_formats/id/999")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/data_formats/id/1")
        assert response.status_code == 500


class TestDataFormatAssociations:

    @patch(API_PATH)
    def test_get_data_types(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_data_types.return_value = [DataTypeOutput(
            id=1, data_type_name="Image", data_type_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/data_formats/id/1/data_types")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_data_types_not_found(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_data_types.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/data_formats/id/1/data_types")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_data_format_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/data_formats/id/999/data_types")
        assert response.status_code == 404
