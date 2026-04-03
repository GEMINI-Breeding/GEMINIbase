"""Tests for the Cultivar controller."""
import types
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import CultivarOutput, ExperimentOutput, PlotOutput, PlantOutput


API_PATH = "gemini.rest_api.controllers.cultivar.Cultivar"


@pytest.fixture
def mock_output():
    return {
        "id": "cult-uuid",
        "cultivar_population": "Population A",
        "cultivar_accession": "Accession 1",
        "cultivar_info": {},
    }


class TestGetAllCultivars:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [CultivarOutput(**mock_output)]
        response = test_client.get("/api/cultivars/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/cultivars/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/cultivars/all")
        assert response.status_code == 500


class TestGetCultivars:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [CultivarOutput(**mock_output)]
        response = test_client.get("/api/cultivars", params={"cultivar_population": "Pop A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/cultivars", params={"cultivar_population": "Missing"})
        assert response.status_code == 404


class TestGetCultivarById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = CultivarOutput(**mock_output)
        response = test_client.get("/api/cultivars/id/cult-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/cultivars/id/missing")
        assert response.status_code == 404


class TestCreateCultivar:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = CultivarOutput(**mock_output)
        response = test_client.post("/api/cultivars", json={
            "cultivar_population": "Population A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/cultivars", json={
            "cultivar_population": "Population A",
        })
        assert response.status_code == 500


class TestUpdateCultivar:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = CultivarOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/cultivars/id/cult-uuid", json={
            "cultivar_population": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/cultivars/id/missing", json={
            "cultivar_population": "Updated",
        })
        assert response.status_code == 404


class TestDeleteCultivar:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/cultivars/id/cult-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/cultivars/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/cultivars/id/cult-uuid")
        assert response.status_code == 500


class TestCultivarAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/cultivars/id/cult-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_plots(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_plots.return_value = [PlotOutput(
            id="p1", plot_number=1, plot_row_number=1, plot_column_number=1,
            experiment_id=None, season_id=None, site_id=None,
            plot_info={}, plot_geometry_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/cultivars/id/cult-uuid/plots")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_plants(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_plants.return_value = [PlantOutput(
            id="pl1", plot_id="p1", cultivar_id="c1",
            plant_number=1, plant_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/cultivars/id/cult-uuid/plants")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_experiments_cultivar_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/cultivars/id/missing/experiments")
        assert response.status_code == 404
