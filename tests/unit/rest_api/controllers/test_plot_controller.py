"""Tests for the Plot controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    PlotOutput, CultivarOutput, ExperimentOutput, SeasonOutput, SiteOutput
)


PLOT_API_PATH = "gemini.rest_api.controllers.plot.Plot"


@pytest.fixture
def mock_plot_output():
    return {
        "id": "plot-uuid",
        "experiment_id": "exp-uuid",
        "season_id": "season-uuid",
        "site_id": "site-uuid",
        "plot_number": 1,
        "plot_row_number": 1,
        "plot_column_number": 1,
        "plot_info": {},
        "plot_geometry_info": {},
    }


class TestGetAllPlots:

    @patch(PLOT_API_PATH)
    def test_success(self, mock_cls, test_client, mock_plot_output):
        mock_cls.get_all.return_value = [PlotOutput(**mock_plot_output)]
        response = test_client.get("/api/plots/all")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/plots/all")
        assert response.status_code == 404

    @patch(PLOT_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/plots/all")
        assert response.status_code == 500


class TestGetPlots:

    @patch(PLOT_API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_plot_output):
        mock_cls.search.return_value = [PlotOutput(**mock_plot_output)]
        response = test_client.get("/api/plots", params={"plot_number": 1})
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/plots", params={"plot_number": 999})
        assert response.status_code == 404


class TestGetPlotById:

    @patch(PLOT_API_PATH)
    def test_success(self, mock_cls, test_client, mock_plot_output):
        mock_cls.get_by_id.return_value = PlotOutput(**mock_plot_output)
        response = test_client.get("/api/plots/id/plot-uuid")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/plots/id/missing")
        assert response.status_code == 404


class TestCreatePlot:

    @patch(PLOT_API_PATH)
    def test_success(self, mock_cls, test_client, mock_plot_output):
        mock_cls.create.return_value = PlotOutput(**mock_plot_output)
        response = test_client.post("/api/plots", json={
            "plot_number": 1,
            "plot_row_number": 1,
            "plot_column_number": 1,
        })
        assert response.status_code == 201

    @patch(PLOT_API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/plots", json={
            "plot_number": 1,
            "plot_row_number": 1,
            "plot_column_number": 1,
        })
        assert response.status_code == 500


class TestUpdatePlot:

    @patch(PLOT_API_PATH)
    def test_success(self, mock_cls, test_client, mock_plot_output):
        mock_plot = MagicMock()
        mock_plot.update.return_value = PlotOutput(**mock_plot_output)
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.patch("/api/plots/id/plot-uuid", json={
            "plot_number": 2,
        })
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/plots/id/missing", json={
            "plot_number": 2,
        })
        assert response.status_code == 404


class TestDeletePlot:

    @patch(PLOT_API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.delete("/api/plots/id/plot-uuid")
        assert response.status_code in (200, 204)

    @patch(PLOT_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/plots/id/missing")
        assert response.status_code == 404

    @patch(PLOT_API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.delete("/api/plots/id/plot-uuid")
        assert response.status_code == 500


class TestPlotAssociations:

    @patch(PLOT_API_PATH)
    def test_get_cultivars(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.get_associated_cultivars.return_value = [CultivarOutput(
            id="c1", cultivar_population="Pop", cultivar_accession="Acc", cultivar_info={}
        )]
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.get("/api/plots/id/plot-uuid/cultivars")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_get_experiment(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.get_associated_experiment.return_value = ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.get("/api/plots/id/plot-uuid/experiment")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_get_season(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.get_associated_season.return_value = SeasonOutput(
            id="s1", season_name="Season A", season_info={},
            season_start_date=None, season_end_date=None, experiment_id="e1"
        )
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.get("/api/plots/id/plot-uuid/season")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_get_site(self, mock_cls, test_client):
        mock_plot = MagicMock()
        mock_plot.get_associated_site.return_value = SiteOutput(
            id="s1", site_name="Site A", site_city="Davis",
            site_state="CA", site_country="US", site_info={}
        )
        mock_cls.get_by_id.return_value = mock_plot
        response = test_client.get("/api/plots/id/plot-uuid/site")
        assert response.status_code == 200

    @patch(PLOT_API_PATH)
    def test_get_experiment_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/plots/id/missing/experiment")
        assert response.status_code == 404
