"""Fixtures for REST API testing."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_client():
    """Create a Litestar TestClient with mocked dependencies.

    Stubs the DB health snapshot so the infrastructure_gate before_request
    hook doesn't 503 every request. Without this, TestClient has no real DB
    to probe and every handler short-circuits to an unavailable response.
    """
    from litestar.testing import TestClient
    from gemini.rest_api import infrastructure as _infra
    from gemini.rest_api.app import app

    healthy = _infra.HealthSnapshot(healthy=True, detail=None, checked_at=1e12)
    with patch.object(_infra.database_health, "status", return_value=healthy):
        with TestClient(app=app) as client:
            yield client
