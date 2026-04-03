"""Fixtures for REST API testing."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_client():
    """Create a Litestar TestClient with mocked dependencies."""
    from litestar.testing import TestClient
    from gemini.rest_api.app import app
    with TestClient(app=app) as client:
        yield client
