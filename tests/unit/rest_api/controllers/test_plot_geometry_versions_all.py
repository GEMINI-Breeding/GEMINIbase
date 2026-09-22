"""GET /api/plot_geometry/versions/all — the "Import boundaries from…" list."""
from datetime import datetime
from unittest.mock import patch

API = "gemini.rest_api.controllers.plot_geometry.PlotGeometryVersion"


@patch(API)
def test_lists_every_directory(mock_api, test_client):
    mock_api.list_all.return_value = [
        {
            "directory": "Processed/S/E/Davis/Cowpea/2024-06-01/D/RGB/",
            "version": 2,
            "name": "final",
            "is_active": True,
            "created_at": datetime(2024, 6, 2, 12, 0),
            "plot_count": 150,
        },
        {
            "directory": "Processed/S/E/Davis/Cowpea/2024-05-01/D/RGB/",
            "version": 1,
            "name": None,
            "is_active": False,
            "created_at": None,
            "plot_count": None,
        },
    ]
    res = test_client.get("/api/plot_geometry/versions/all")
    assert res.status_code == 200, res.text
    body = res.json()
    assert [b["version"] for b in body] == [2, 1]
    assert body[0]["created_at"] == "2024-06-02T12:00:00"
    assert body[0]["plot_count"] == 150
    assert body[1]["created_at"] is None
    assert body[1]["plot_count"] == 0
