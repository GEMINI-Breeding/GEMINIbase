"""Tests for the Site controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import SiteOutput, ExperimentOutput, PlotOutput


SITE_API_PATH = "gemini.rest_api.controllers.site.Site"


@pytest.fixture
def mock_site_output():
    return {
        "id": "test-uuid",
        "site_name": "Test Site",
        "site_city": "Davis",
        "site_state": "CA",
        "site_country": "US",
        "site_info": {},
    }


class TestGetAllSites:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client, mock_site_output):
        mock_site_cls.get_all.return_value = [SiteOutput(**mock_site_output)]
        response = test_client.get("/api/sites/all")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch(SITE_API_PATH)
    def test_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_all.return_value = None
        response = test_client.get("/api/sites/all")
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_server_error(self, mock_site_cls, test_client):
        mock_site_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/sites/all")
        assert response.status_code == 500


class TestGetSites:

    @patch(SITE_API_PATH)
    def test_search_success(self, mock_site_cls, test_client, mock_site_output):
        mock_site_cls.search.return_value = [SiteOutput(**mock_site_output)]
        response = test_client.get("/api/sites", params={"site_name": "Test"})
        assert response.status_code == 200

    @patch(SITE_API_PATH)
    def test_search_not_found(self, mock_site_cls, test_client):
        mock_site_cls.search.return_value = None
        response = test_client.get("/api/sites", params={"site_name": "Missing"})
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_search_error(self, mock_site_cls, test_client):
        mock_site_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/sites", params={"site_name": "Test"})
        assert response.status_code == 500


class TestGetSiteById:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client, mock_site_output):
        mock_site_cls.get_by_id.return_value = SiteOutput(**mock_site_output)
        response = test_client.get("/api/sites/id/test-uuid")
        assert response.status_code == 200

    @patch(SITE_API_PATH)
    def test_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.return_value = None
        response = test_client.get("/api/sites/id/missing-uuid")
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_error(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/sites/id/test-uuid")
        assert response.status_code == 500


class TestCreateSite:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client, mock_site_output):
        mock_site_cls.create.return_value = SiteOutput(**mock_site_output)
        response = test_client.post("/api/sites", json={
            "site_name": "Test Site",
            "site_city": "Davis",
            "site_state": "CA",
            "site_country": "US",
        })
        assert response.status_code == 201

    @patch(SITE_API_PATH)
    def test_create_returns_none(self, mock_site_cls, test_client):
        mock_site_cls.create.return_value = None
        response = test_client.post("/api/sites", json={
            "site_name": "Test Site",
        })
        assert response.status_code == 500

    @patch(SITE_API_PATH)
    def test_create_error(self, mock_site_cls, test_client):
        mock_site_cls.create.side_effect = Exception("DB error")
        response = test_client.post("/api/sites", json={
            "site_name": "Test Site",
        })
        assert response.status_code == 500


class TestUpdateSite:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client, mock_site_output):
        mock_site = MagicMock()
        mock_site.update.return_value = SiteOutput(**mock_site_output)
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.patch("/api/sites/id/test-uuid", json={
            "site_name": "Updated Site",
        })
        assert response.status_code == 200

    @patch(SITE_API_PATH)
    def test_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.return_value = None
        response = test_client.patch("/api/sites/id/missing-uuid", json={
            "site_name": "Updated Site",
        })
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_error(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/sites/id/test-uuid", json={
            "site_name": "Updated Site",
        })
        assert response.status_code == 500


class TestDeleteSite:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client):
        mock_site = MagicMock()
        mock_site.delete.return_value = True
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.delete("/api/sites/id/test-uuid")
        assert response.status_code in (200, 204)

    @patch(SITE_API_PATH)
    def test_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.return_value = None
        response = test_client.delete("/api/sites/id/missing-uuid")
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_delete_fails(self, mock_site_cls, test_client):
        mock_site = MagicMock()
        mock_site.delete.return_value = False
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.delete("/api/sites/id/test-uuid")
        assert response.status_code == 500

    @patch(SITE_API_PATH)
    def test_error(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/sites/id/test-uuid")
        assert response.status_code == 500


class TestGetSiteExperiments:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client):
        mock_site = MagicMock()
        mock_site.get_associated_experiments.return_value = [ExperimentOutput(
            id="exp-1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.get("/api/sites/id/test-uuid/experiments")
        assert response.status_code == 200

    @patch(SITE_API_PATH)
    def test_site_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.return_value = None
        response = test_client.get("/api/sites/id/missing/experiments")
        assert response.status_code == 404

    @patch(SITE_API_PATH)
    def test_no_experiments(self, mock_site_cls, test_client):
        mock_site = MagicMock()
        mock_site.get_associated_experiments.return_value = None
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.get("/api/sites/id/test-uuid/experiments")
        assert response.status_code == 404


class TestGetSitePlots:

    @patch(SITE_API_PATH)
    def test_success(self, mock_site_cls, test_client):
        mock_site = MagicMock()
        mock_site.get_associated_plots.return_value = [PlotOutput(
            id="plot-1", plot_number=1, plot_row_number=1, plot_column_number=1,
            experiment_id=None, season_id=None, site_id=None,
            plot_info={}, plot_geometry_info={}
        )]
        mock_site_cls.get_by_id.return_value = mock_site
        response = test_client.get("/api/sites/id/test-uuid/plots")
        assert response.status_code == 200

    @patch(SITE_API_PATH)
    def test_site_not_found(self, mock_site_cls, test_client):
        mock_site_cls.get_by_id.return_value = None
        response = test_client.get("/api/sites/id/missing/plots")
        assert response.status_code == 404
