"""Tests for the Population controller."""
import types
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import PopulationOutput, ExperimentOutput, AccessionOutput


API_PATH = "gemini.rest_api.controllers.population.Population"


@pytest.fixture
def mock_output():
    return {
        "id": "cult-uuid",
        "population_name": "Population A",
        "population_type": "diversity_panel",
        "species": "Zea mays",
        "population_info": {},
    }


class TestGetAllPopulations:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [PopulationOutput(**mock_output)]
        response = test_client.get("/api/populations/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/populations/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/populations/all")
        assert response.status_code == 500


class TestGetPopulations:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [PopulationOutput(**mock_output)]
        response = test_client.get("/api/populations", params={"population_name": "Pop A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/populations", params={"population_name": "Missing"})
        assert response.status_code == 404


class TestGetPopulationById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = PopulationOutput(**mock_output)
        response = test_client.get("/api/populations/id/cult-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/populations/id/missing")
        assert response.status_code == 404


class TestCreatePopulation:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = PopulationOutput(**mock_output)
        response = test_client.post("/api/populations", json={
            "population_name": "Population A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/populations", json={
            "population_name": "Population A",
        })
        assert response.status_code == 500


class TestUpdatePopulation:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = PopulationOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/populations/id/cult-uuid", json={
            "population_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/populations/id/missing", json={
            "population_name": "Updated",
        })
        assert response.status_code == 404


class TestDeletePopulation:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/populations/id/cult-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/populations/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/populations/id/cult-uuid")
        assert response.status_code == 500


class TestPopulationAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/populations/id/cult-uuid/experiments")
        assert response.status_code == 200


    @patch(API_PATH)
    def test_get_experiments_population_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/populations/id/missing/experiments")
        assert response.status_code == 404
