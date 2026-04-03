"""Tests for the root REST API handlers in gemini/rest_api/app.py."""
import pytest
from unittest.mock import patch, MagicMock


class TestRootHandler:
    """Tests for GET /."""

    def test_root_returns_welcome_message(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to the GEMINI API"
        assert data["version"] == "1.0.0"
        assert "author" in data
        assert "email" in data


class TestSettingsHandler:
    """Tests for GET /settings."""

    def test_settings_returns_dict(self, test_client):
        response = test_client.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
