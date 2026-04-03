"""Tests for the Season controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import SeasonOutput, ExperimentOutput


API_PATH = "gemini.rest_api.controllers.season.Season"


@pytest.fixture
def mock_output():
    return {
        "id": "season-uuid",
        "season_name": "Season 2024",
        "season_info": {},
        "season_start_date": None,
        "season_end_date": None,
        "experiment_id": "exp-uuid",
    }


class TestGetAllSeasons:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [SeasonOutput(**mock_output)]
        response = test_client.get("/api/seasons/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/seasons/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/seasons/all")
        assert response.status_code == 500


class TestGetSeasons:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [SeasonOutput(**mock_output)]
        response = test_client.get("/api/seasons", params={"season_name": "Season 2024"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/seasons", params={"season_name": "Missing"})
        assert response.status_code == 404


class TestGetSeasonById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = SeasonOutput(**mock_output)
        response = test_client.get("/api/seasons/id/season-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/seasons/id/missing")
        assert response.status_code == 404


class TestCreateSeason:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = SeasonOutput(**mock_output)
        response = test_client.post("/api/seasons", json={
            "season_name": "Season 2024",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/seasons", json={
            "season_name": "Season 2024",
        })
        assert response.status_code == 500


class TestUpdateSeason:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = SeasonOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/seasons/id/season-uuid", json={
            "season_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/seasons/id/missing", json={
            "season_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteSeason:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/seasons/id/season-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/seasons/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/seasons/id/season-uuid")
        assert response.status_code == 500


class TestSeasonAssociations:

    @patch(API_PATH)
    def test_get_experiment(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiment.return_value = ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/seasons/id/season-uuid/experiment")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_experiment_not_found(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiment.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/seasons/id/season-uuid/experiment")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_season_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/seasons/id/missing/experiment")
        assert response.status_code == 404
