"""POST /api/plot_geometry/versions/save — new version vs overwrite in place."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

API = "gemini.rest_api.controllers.plot_geometry.PlotGeometryVersion"
DIR = "Processed/S/E/Davis/Cowpea/PlotMarkings"
SNAP = {"selections": [{"plot_id": 1, "start_image": "a.jpg", "end_image": "b.jpg"}]}


def row(version, name=None):
    return SimpleNamespace(
        version=version, name=name, is_active=True, created_at=datetime(2026, 9, 1)
    )


@patch(API)
def test_without_version_adds_one(mock_api, test_client):
    mock_api.save.return_value = row(3)
    res = test_client.post(
        "/api/plot_geometry/versions/save",
        json={"directory": DIR, "state_snapshot": SNAP, "name": "retry"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["version"] == 3
    mock_api.save.assert_called_once()
    mock_api.overwrite.assert_not_called()


@patch(API)
def test_with_version_overwrites_it(mock_api, test_client):
    mock_api.overwrite.return_value = row(2, "final")
    res = test_client.post(
        "/api/plot_geometry/versions/save",
        json={"directory": DIR, "state_snapshot": SNAP, "version": 2},
    )
    assert res.status_code == 201, res.text
    assert res.json() == {
        "version": 2, "name": "final", "is_active": True,
        "created_at": "2026-09-01T00:00:00",
    }
    mock_api.overwrite.assert_called_once_with(
        directory=DIR, version=2, state_snapshot=SNAP, name=None
    )
    mock_api.save.assert_not_called()


@patch(API)
def test_overwriting_a_missing_version_is_404(mock_api, test_client):
    mock_api.overwrite.return_value = None
    res = test_client.post(
        "/api/plot_geometry/versions/save",
        json={"directory": DIR, "state_snapshot": SNAP, "version": 9},
    )
    assert res.status_code == 404
    assert "No version 9" in res.text
