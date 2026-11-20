"""GET /api/files/presign must sign the URL for the lifetime it reports."""
from datetime import timedelta
from unittest.mock import patch


def test_presign_endpoint_honours_expires_seconds(test_client):
    with patch("gemini.rest_api.controllers.files.minio_storage_provider") as minio:
        minio.get_download_url.return_value = "https://signed"
        res = test_client.get("/api/files/presign/gemini/b/obj.jpg", params={"expires_seconds": 120})
    assert res.status_code == 200, res.text
    assert res.json()["expires_in_seconds"] == 120
    assert minio.get_download_url.call_args.kwargs["expires"] == timedelta(seconds=120)
