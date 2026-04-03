"""Tests for the TraitLevel controller.

Note: This controller uses int IDs (trait_level_id:int).
"""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import TraitLevelOutput


API_PATH = "gemini.rest_api.controllers.trait_level.TraitLevel"


@pytest.fixture
def mock_output():
    return {
        "id": 1,
        "trait_level_name": "Plot",
        "trait_level_info": {},
    }


class TestGetAllTraitLevels:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [TraitLevelOutput(**mock_output)]
        response = test_client.get("/api/trait_levels/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/trait_levels/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/trait_levels/all")
        assert response.status_code == 500


class TestGetTraitLevels:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [TraitLevelOutput(**mock_output)]
        response = test_client.get("/api/trait_levels", params={"trait_level_name": "Plot"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/trait_levels", params={"trait_level_name": "Missing"})
        assert response.status_code == 404


class TestGetTraitLevelById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = TraitLevelOutput(**mock_output)
        response = test_client.get("/api/trait_levels/id/1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/trait_levels/id/999")
        assert response.status_code == 404


class TestCreateTraitLevel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = TraitLevelOutput(**mock_output)
        response = test_client.post("/api/trait_levels", json={
            "trait_level_name": "Plot",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/trait_levels", json={
            "trait_level_name": "Plot",
        })
        assert response.status_code == 500


class TestUpdateTraitLevel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = TraitLevelOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/trait_levels/id/1", json={
            "trait_level_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/trait_levels/id/999", json={
            "trait_level_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteTraitLevel:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/trait_levels/id/1")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/trait_levels/id/999")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/trait_levels/id/1")
        assert response.status_code == 500
