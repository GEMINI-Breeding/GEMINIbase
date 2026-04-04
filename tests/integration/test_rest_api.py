"""
Integration tests for the REST API against real PostgreSQL.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
Run with: pytest tests/integration/ -v -m integration
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(setup_real_db):
    """Litestar TestClient backed by the real test DB."""
    from litestar.testing import TestClient
    from gemini.rest_api.app import app
    with TestClient(app=app) as c:
        yield c


class TestExperimentEndpoints:

    def test_create_experiment(self, client, setup_real_db):
        resp = client.post("/api/experiments", json={
            "experiment_name": "REST Experiment",
            "experiment_info": {"crop": "rice"},
        })
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["experiment_name"] == "REST Experiment"

    def test_get_all_experiments(self, client, setup_real_db):
        # Create some data first
        client.post("/api/experiments", json={"experiment_name": "List A"})
        client.post("/api/experiments", json={"experiment_name": "List B"})

        resp = client.get("/api/experiments/all")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_all_with_pagination(self, client, setup_real_db):
        for i in range(5):
            client.post("/api/experiments", json={"experiment_name": f"Page {i}"})

        resp = client.get("/api/experiments/all?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        resp2 = client.get("/api/experiments/all?limit=2&offset=2")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2) == 2

    def test_get_experiment_not_found(self, client, setup_real_db):
        resp = client.get("/api/experiments/id/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (404, 500)

    def test_search_experiments(self, client, setup_real_db):
        client.post("/api/experiments", json={"experiment_name": "Search Target"})

        resp = client.get("/api/experiments?experiment_name=Search Target")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(e["experiment_name"] == "Search Target" for e in data)


class TestSiteEndpoints:

    def test_create_and_get_site(self, client, setup_real_db):
        resp = client.post("/api/sites", json={
            "site_name": "REST Site",
            "site_city": "Davis",
            "site_state": "CA",
            "site_country": "USA",
        })
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["site_name"] == "REST Site"

        # Get by ID
        site_id = data.get("id") or data.get("site_id")
        resp2 = client.get(f"/api/sites/id/{site_id}")
        assert resp2.status_code == 200

    def test_update_site(self, client, setup_real_db):
        resp = client.post("/api/sites", json={
            "site_name": "Update Site",
            "site_city": "Old City",
            "site_state": "CA",
            "site_country": "USA",
        })
        site_id = resp.json().get("id") or resp.json().get("site_id")

        resp2 = client.patch(f"/api/sites/id/{site_id}", json={
            "site_city": "New City",
        })
        assert resp2.status_code == 200
        assert resp2.json()["site_city"] == "New City"

    def test_delete_site(self, client, setup_real_db):
        resp = client.post("/api/sites", json={
            "site_name": "Delete Site",
            "site_city": "C", "site_state": "S", "site_country": "US",
        })
        site_id = resp.json().get("id") or resp.json().get("site_id")

        resp2 = client.delete(f"/api/sites/id/{site_id}")
        assert resp2.status_code in (200, 204)

        # Verify gone
        resp3 = client.get(f"/api/sites/id/{site_id}")
        assert resp3.status_code in (404, 500)


class TestPopulationEndpoints:

    def test_create_population(self, client, setup_real_db):
        resp = client.post("/api/populations", json={
            "population_name": "Pop A",
            "population_accession": "Acc 001",
        })
        assert resp.status_code in (200, 201), resp.text


class TestDataTypeEndpoints:

    def test_get_all_data_types(self, client, setup_real_db):
        """Seed data should be present from init SQL."""
        resp = client.get("/api/data_types/all")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_data_type_by_id(self, client, setup_real_db):
        resp = client.get("/api/data_types/id/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_type_name"] == "Text"


class TestRootEndpoints:

    def test_root(self, client, setup_real_db):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Welcome to the GEMINI API"

    def test_settings(self, client, setup_real_db):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)
