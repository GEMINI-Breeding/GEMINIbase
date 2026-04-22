"""Tests for the DataType controller.

Note: This controller uses int IDs (data_type_id:int) and has
an association endpoint for data_formats.
"""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import DataTypeOutput, DataFormatOutput


API_PATH = "gemini.rest_api.controllers.data_type.DataType"


@pytest.fixture
def mock_output():
    return {
        "id": 1,
        "data_type_name": "Image",
        "data_type_info": {},
    }


class TestGetAllDataTypes:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [DataTypeOutput(**mock_output)]
        response = test_client.get("/api/data_types/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/data_types/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/data_types/all")
        assert response.status_code == 500


class TestGetDataTypes:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [DataTypeOutput(**mock_output)]
        response = test_client.get("/api/data_types", params={"data_type_name": "Image"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/data_types", params={"data_type_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []


class TestGetDataTypeById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = DataTypeOutput(**mock_output)
        response = test_client.get("/api/data_types/id/1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/data_types/id/999")
        assert response.status_code == 404


class TestCreateDataType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = DataTypeOutput(**mock_output)
        response = test_client.post("/api/data_types", json={
            "data_type_name": "Image",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/data_types", json={
            "data_type_name": "Image",
        })
        assert response.status_code == 500


class TestUpdateDataType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = DataTypeOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/data_types/id/1", json={
            "data_type_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/data_types/id/999", json={
            "data_type_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteDataType:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/data_types/id/1")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/data_types/id/999")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/data_types/id/1")
        assert response.status_code == 500


class TestDataTypeAssociations:

    @patch(API_PATH)
    def test_get_data_formats(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_data_formats.return_value = [DataFormatOutput(
            id=1, data_format_name="PNG", data_format_mime_type="image/png",
            data_format_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/data_types/id/1/data_formats")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_data_formats_not_found(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_data_formats.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/data_types/id/1/data_formats")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_data_type_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/data_types/id/999/data_formats")
        assert response.status_code == 404
