"""EXIF GPS is read from a ranged header, and "no GPS" is cached.

Finalizing an upload and /image-gps used to download whole objects (a
multi-GB orthomosaic .tif into the API's memory) and re-read every image
without GPS on every call.
"""
import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from gemini.rest_api.controllers import files

PROVIDER = "gemini.rest_api.controllers.files.minio_storage_provider"


def _jpeg_with_gps(pixels: int = 1500) -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (pixels, pixels, 3), dtype=np.uint8))
    exif = Image.Exif()
    gps = exif.get_ifd(34853)
    gps.update({1: "N", 2: (38.0, 32.0, 24.0), 3: "W", 4: (121.0, 45.0, 0.0), 5: 0, 6: 18.5})
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif, quality=95)
    return buf.getvalue()


def _provider(blobs: dict) -> MagicMock:
    p = MagicMock()
    p.download_file_range.side_effect = (
        lambda object_name, offset, length, bucket_name: blobs[object_name][offset : offset + length]
    )
    p.get_file_metadata.side_effect = lambda object_name, bucket_name: {"size": len(blobs[object_name])}
    return p


def test_gps_comes_from_the_header_of_a_large_jpeg():
    blob = _jpeg_with_gps()
    assert len(blob) > files._EXIF_HEADER_BYTES * 2
    p = _provider({"a.jpg": blob})
    with patch(PROVIDER, p):
        gps = files._read_image_gps("b", "a.jpg")
    assert round(gps["lat"], 4) == 38.54 and round(gps["lon"], 4) == -121.75
    p.download_file_stream.assert_not_called()


def test_large_tiff_without_gps_in_the_header_is_not_downloaded():
    p = _provider({"ortho.tif": b"\0" * files._EXIF_HEADER_BYTES})
    p.get_file_metadata.side_effect = lambda **kw: {"size": 3 * 1024**3}
    with patch(PROVIDER, p):
        assert files._read_image_gps("b", "ortho.tif") is None
    p.download_file_stream.assert_not_called()


def _call_image_gps(provider, cached_rows):
    session = MagicMock()
    session.__enter__.return_value.execute.return_value.all.return_value = cached_rows
    engine = MagicMock()
    engine.get_session.return_value = session
    provider.bucket_exists.return_value = True
    provider.list_files_with_metadata.return_value = [
        {"object_name": "Raw/x/Images/nogps.jpg"},
        {"object_name": "Raw/x/Images/checked.jpg"},
    ]
    updates = []
    with patch(PROVIDER, provider), patch("gemini.db.core.base.db_engine", engine), patch.object(
        files, "_synced_positions", return_value={}
    ), patch.object(
        files, "_update_experiment_file_metadata", side_effect=lambda **kw: updates.append(kw)
    ):
        handler = files.FileController.list_image_gps.fn
        resp = handler(MagicMock(), file_path="gemini/Raw/x/Images/")
    return resp, updates


def test_no_gps_is_cached_and_cached_misses_are_not_reread():
    plain = io.BytesIO()
    Image.new("RGB", (10, 10)).save(plain, format="JPEG")
    p = _provider({"Raw/x/Images/nogps.jpg": plain.getvalue()})
    rows = [SimpleNamespace(object_name="Raw/x/Images/checked.jpg", metadata_json={"gps": None})]
    resp, updates = _call_image_gps(p, rows)
    # Only the never-checked image was read, and its miss was cached.
    read = [c.kwargs["object_name"] for c in p.download_file_range.call_args_list]
    assert read == ["Raw/x/Images/nogps.jpg"]
    assert updates == [
        {"bucket": "gemini", "object_name": "Raw/x/Images/nogps.jpg", "patch": {"gps": None}}
    ]
    assert [i.name for i in resp.images] == ["nogps.jpg", "checked.jpg"]
