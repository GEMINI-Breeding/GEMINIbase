"""image-gps: a synced track beside the images outranks EXIF GPS."""
import io
from unittest.mock import MagicMock, patch

from gemini.rest_api.controllers import files

PROVIDER = "gemini.rest_api.controllers.files.minio_storage_provider"


def provider_with(objects: dict):
    p = MagicMock()
    p.file_exists.side_effect = lambda object_name, bucket_name: object_name in objects
    p.download_file_stream.side_effect = lambda object_name, bucket_name: io.BytesIO(
        objects[object_name].encode()
    )
    return p


def test_data_sync_track_by_image_name():
    csv = "image,timestamp,lat,lon,alt,gps_source\nIMG_1.jpg,1,38.5,-121.7,3.5,interpolated\nIMG_2.jpg,2,,,,none\n"
    with patch(PROVIDER, provider_with({"Raw/x/ds1/Metadata/msgs_synced.csv": csv})):
        got = files._synced_positions("gemini", "Raw/x/ds1/Images/")
    assert got == {"IMG_1.jpg": {"lat": 38.5, "lon": -121.7, "alt": 3.5}}


def test_amiga_extraction_track():
    csv = "/top/rgb,lat,lon,altitude,/top/rgb_file\n1,38.5,-121.7,15.9,/top/rgb-1.jpg\n"
    with patch(PROVIDER, provider_with({"Raw/x/ds2/RGB/Metadata/msgs_synced.csv": csv})):
        got = files._synced_positions("gemini", "Raw/x/ds2/RGB/Images/top/")
    assert got == {"rgb-1.jpg": {"lat": 38.5, "lon": -121.7, "alt": 15.9}}


def test_no_track_or_no_images_folder():
    with patch(PROVIDER, provider_with({})):
        assert files._synced_positions("gemini", "Raw/x/ds1/Images/") == {}
        assert files._synced_positions("gemini", "Raw/x/ds1/Orthomosaic/") == {}
