"""Tests for the Plant controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import PlantOutput, CultivarOutput, PlotOutput


API_PATH = "gemini.rest_api.controllers.plant.Plant"


@pytest.fixture
def mock_output():
    return {
        "id": "plant-uuid",
        "plot_id": "plot-uuid",
        "cultivar_id": "cult-uuid",
        "plant_number": 1,
        "plant_info": {},
    }


class TestGetAllPlants:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [PlantOutput(**mock_output)]
        response = test_client.get("/api/plants/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/plants/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/plants/all")
        assert response.status_code == 500


class TestGetPlants:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [PlantOutput(**mock_output)]
        response = test_client.get("/api/plants", params={"plant_number": 1})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/plants", params={"plant_number": 999})
        assert response.status_code == 404


class TestGetPlantById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = PlantOutput(**mock_output)
        response = test_client.get("/api/plants/id/plant-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/plants/id/missing")
        assert response.status_code == 404


class TestCreatePlant:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = PlantOutput(**mock_output)
        response = test_client.post("/api/plants", json={
            "plant_number": 1,
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/plants", json={
            "plant_number": 1,
        })
        assert response.status_code == 500


class TestUpdatePlant:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = PlantOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/plants/id/plant-uuid", json={
            "plant_number": 2,
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/plants/id/missing", json={
            "plant_number": 2,
        })
        assert response.status_code == 404


class TestDeletePlant:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/plants/id/plant-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/plants/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/plants/id/plant-uuid")
        assert response.status_code == 500


class TestPlantAssociations:

    @patch(API_PATH)
    def test_get_cultivar(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_cultivar.return_value = CultivarOutput(
            id="c1", cultivar_population="Pop", cultivar_accession="Acc",
            cultivar_info={}
        )
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/plants/id/plant-uuid/cultivar")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_cultivar_not_found(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_cultivar.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/plants/id/plant-uuid/cultivar")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_plot(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_plot.return_value = [PlotOutput(
            id="p1", plot_number=1, plot_row_number=1, plot_column_number=1,
            experiment_id=None, season_id=None, site_id=None,
            plot_info={}, plot_geometry_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/plants/id/plant-uuid/plot")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_plant_not_found_for_assoc(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/plants/id/missing/cultivar")
        assert response.status_code == 404
