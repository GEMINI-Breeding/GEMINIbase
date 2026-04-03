"""Tests for gemini.api.parsers.amiga — AMIGAPhoneParser.

All file-reading, JSON parsing, timestamp extraction, and data-map construction
run against real fixture data on disk. Only DB-layer calls (Experiment.get,
SensorPlatform.get, Sensor.get, sensor.add_records) are patched because they
require a live PostgreSQL connection.
"""
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from gemini.api.parsers.amiga import AMIGAPhoneParser

FIXTURES_DIR = Path(__file__).parents[3] / "fixtures"

# Epoch timestamps embedded in the 3 fixture JSON files
FIXTURE_EPOCH_TIMES = [
    1721058398.531859,
    1721058398.837060,
    1721058399.153331,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_parser(mock_db_boundary) -> AMIGAPhoneParser:
    """Construct a real AMIGAPhoneParser with the DB boundary patched."""
    return AMIGAPhoneParser()


# ---------------------------------------------------------------------------
# TestAMIGAPhoneParserValidate
# ---------------------------------------------------------------------------

class TestAMIGAPhoneParserValidate:
    """validate() exercises real os.path calls against fixture dirs."""

    def test_valid_directory(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        assert parser.validate(amiga_phone_dir) is True

    def test_invalid_path_pattern(self, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        assert parser.validate("/some/random/path") is False

    def test_missing_meta_json(self, amiga_phone_dir, mock_db_boundary, tmp_path):
        # Copy fixture tree but omit meta_json
        shutil.copytree(amiga_phone_dir, tmp_path / "Phone")
        shutil.rmtree(tmp_path / "Phone" / "meta_json")
        parser = make_parser(mock_db_boundary)
        assert parser.validate(str(tmp_path / "Phone")) is False

    def test_path_without_amiga_phone_segment_is_invalid(self, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        assert parser.validate("Dataset_2024/Davis/2024-07-15/Phone") is False

    def test_missing_optional_dirs_still_valid(self, amiga_phone_dir, mock_db_boundary, tmp_path):
        # Copy fixture tree under a path that satisfies the regex structure
        dest = tmp_path / "Dataset_2024" / "Davis" / "2024-07-15" / "Amiga_Phone" / "Phone"
        shutil.copytree(amiga_phone_dir, dest)
        for d in ("confidence_tiff", "depth_tiff", "flir_jpg", "rgb_jpeg"):
            target = dest / d
            if target.exists():
                shutil.rmtree(target)
        parser = make_parser(mock_db_boundary)
        assert parser.validate(str(dest)) is True


# ---------------------------------------------------------------------------
# TestAMIGAPhoneParserParse
# ---------------------------------------------------------------------------

class TestAMIGAPhoneParserParse:
    """parse() reads real JSON and image files; DB calls are patched."""

    def test_parse_produces_three_records(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        # Intercept upload to capture the data_map passed in
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(amiga_phone_dir)

        assert "data_map" in captured
        assert len(captured["data_map"]["data"]) == 3

    def test_parse_data_map_structure(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(amiga_phone_dir)

        dm = captured["data_map"]
        assert dm["collection_date"] == "2024-07-15"
        assert dm["season"] == "2024"
        assert dm["site"] == "Davis"

        for record in dm["data"]:
            assert isinstance(record["timestamp"], datetime)
            assert isinstance(record["metadata"], dict)
            assert "metadata_file" in record
            assert Path(record["metadata_file"]).is_absolute()

    def test_parse_timestamps_match_json_epoch_values(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(amiga_phone_dir)

        actual_timestamps = sorted(r["timestamp"] for r in captured["data_map"]["data"])
        expected_timestamps = sorted(datetime.fromtimestamp(e) for e in FIXTURE_EPOCH_TIMES)
        assert actual_timestamps == expected_timestamps

    def test_parse_metadata_fields_present(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(amiga_phone_dir)

        for record in captured["data_map"]["data"]:
            meta = record["metadata"]
            for key in ("attitude", "climate", "gps", "info", "thermal"):
                assert key in meta, f"Missing key '{key}' in metadata"

    def test_parse_rgb_files_linked_to_records(self, amiga_phone_dir, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(amiga_phone_dir)

        for record in captured["data_map"]["data"]:
            assert "rgb_file" in record
            assert Path(record["rgb_file"]).is_absolute()

    def test_parse_skips_collection_files(self, amiga_phone_dir, mock_db_boundary, tmp_path):
        # Must mirror the required regex path structure
        dest = tmp_path / "Dataset_2024" / "Davis" / "2024-07-15" / "Amiga_Phone" / "Phone"
        shutil.copytree(amiga_phone_dir, dest)
        # Add a collection-named JSON that should be skipped
        (dest / "meta_json" / "collection_summary.json").write_text(
            json.dumps({"info": {"epochTime": "9999999999.0"}})
        )

        parser = make_parser(mock_db_boundary)
        captured = {}

        def capture_metadata(data_map):
            captured["data_map"] = data_map

        parser.upload_metadata_files = capture_metadata
        parser.upload_confidence_files = lambda dm: None
        parser.upload_depth_files = lambda dm: None
        parser.upload_flir_files = lambda dm: None
        parser.upload_rgb_files = lambda dm: None

        parser.parse(str(dest))

        # Still only 3 records — the collection file was skipped
        assert len(captured["data_map"]["data"]) == 3

    def test_parse_invalid_dir_calls_no_uploads(self, mock_db_boundary):
        parser = make_parser(mock_db_boundary)
        upload_calls = []

        for method in (
            "upload_metadata_files",
            "upload_confidence_files",
            "upload_depth_files",
            "upload_flir_files",
            "upload_rgb_files",
        ):
            setattr(parser, method, lambda dm, m=method: upload_calls.append(m))

        parser.parse("/not/a/valid/path")
        assert upload_calls == []

    def test_parse_empty_optional_dirs_completes_without_error(self, amiga_phone_dir, mock_db_boundary):
        # Fixture already has empty confidence_tiff, depth_tiff, flir_jpg dirs — parse must succeed
        parser = make_parser(mock_db_boundary)
        # Real upload methods run through to Sensor.get (which is patched)
        parser.parse(amiga_phone_dir)
        # Verify each sensor's add_records was called
        for sensor_mock in mock_db_boundary.values():
            sensor_mock.add_records.assert_called_once()


# ---------------------------------------------------------------------------
# TestUploadMethods
# ---------------------------------------------------------------------------

class TestUploadMethods:
    """Upload methods run for real against in-memory data_map dicts."""

    def _make_data_map(self, n: int) -> dict:
        """Build a data_map with n records using real timestamp objects."""
        import random
        base = datetime(2024, 7, 15, 15, 46, 37)
        records = []
        for i in range(n):
            ts = datetime.fromtimestamp(base.timestamp() + i * 0.3)
            records.append({
                "timestamp": ts,
                "metadata": {"info": {"epochTime": str(base.timestamp() + i * 0.3)}},
                "metadata_file": f"/fake/path/meta_{i:05d}.json",
                "confidence_file": f"/fake/path/conf_{i:05d}.tiff",
                "depth_file": f"/fake/path/depth_{i:05d}.tiff",
                "flir_file": f"/fake/path/flir_{i:05d}.jpg",
                "rgb_file": f"/fake/path/rgb_{i:05d}.jpg",
            })
        # Shuffle to ensure sort is actually tested
        random.shuffle(records)
        return {
            "collection_date": "2024-07-15",
            "season": "2024",
            "site": "Davis",
            "data": records,
        }

    def test_upload_metadata_sorts_by_timestamp(self, mock_db_boundary):
        parser = AMIGAPhoneParser()
        data_map = self._make_data_map(10)

        parser.upload_metadata_files(data_map)

        sensor = mock_db_boundary["AMIGA Phone Camera Metadata"]
        sensor.add_records.assert_called_once()
        call_kwargs = sensor.add_records.call_args.kwargs
        timestamps = call_kwargs["timestamps"]
        assert timestamps == sorted(timestamps)

    def test_upload_limits_to_100_records(self, mock_db_boundary):
        parser = AMIGAPhoneParser()
        data_map = self._make_data_map(150)

        parser.upload_metadata_files(data_map)

        sensor = mock_db_boundary["AMIGA Phone Camera Metadata"]
        call_kwargs = sensor.add_records.call_args.kwargs
        assert len(call_kwargs["timestamps"]) == 100

    def test_upload_rgb_excludes_records_missing_rgb_file(self, mock_db_boundary):
        parser = AMIGAPhoneParser()
        data_map = self._make_data_map(3)
        # Remove rgb_file from all records to simulate empty rgb_jpeg dir
        for record in data_map["data"]:
            del record["rgb_file"]

        parser.upload_rgb_files(data_map)

        sensor = mock_db_boundary["AMIGA Phone RGB Camera"]
        call_kwargs = sensor.add_records.call_args.kwargs
        assert call_kwargs["record_files"] == []
        # Timestamps are still passed (3 records)
        assert len(call_kwargs["timestamps"]) == 3

    def test_upload_confidence_excludes_records_missing_confidence_file(self, mock_db_boundary):
        parser = AMIGAPhoneParser()
        data_map = self._make_data_map(3)
        for record in data_map["data"]:
            del record["confidence_file"]

        parser.upload_confidence_files(data_map)

        sensor = mock_db_boundary["AMIGA Phone Confidence"]
        call_kwargs = sensor.add_records.call_args.kwargs
        assert call_kwargs["record_files"] == []
        assert len(call_kwargs["timestamps"]) == 3


# ---------------------------------------------------------------------------
# TestDroneFixtures
# ---------------------------------------------------------------------------

class TestDroneFixtures:
    """Validates the drone fixture data files are well-formed."""

    def test_field_design_csv_structure(self, drone_dir):
        csv_path = drone_dir / "field_design.csv"
        assert csv_path.exists(), "field_design.csv fixture is missing"

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 100, f"Expected >100 rows, got {len(rows)}"
        required_columns = {"Location", "Line ID", "Field.plot.number", "Crop", "Rep", "Bed", "Tier"}
        assert required_columns.issubset(set(reader.fieldnames)), (
            f"Missing columns. Got: {reader.fieldnames}"
        )

    def test_gcp_locations_csv_structure(self, drone_dir):
        csv_path = drone_dir / "gcp_locations.csv"
        assert csv_path.exists(), "gcp_locations.csv fixture is missing"

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 16, f"Expected 16 GCP rows, got {len(rows)}"
        for col in ("Label", "Lat_dec", "Lon_dec"):
            assert col in reader.fieldnames, f"Missing column '{col}'"

        # Lat/Lon values should be plausible floats for Davis, CA
        for row in rows:
            lat = float(row["Lat_dec"])
            lon = float(row["Lon_dec"])
            assert 38.0 < lat < 39.0, f"Unexpected latitude: {lat}"
            assert -122.5 < lon < -121.0, f"Unexpected longitude: {lon}"

    def test_drone_images_are_valid_jpegs(self, drone_dir):
        image_files = list(drone_dir.rglob("*.JPG")) + list(drone_dir.rglob("*.jpg"))
        assert len(image_files) == 2, f"Expected 2 drone fixture images, found {len(image_files)}"

        for img_path in image_files:
            with Image.open(img_path) as img:
                assert img.mode == "RGB", f"{img_path.name}: expected RGB, got {img.mode}"
                assert img.size == (64, 64), f"{img_path.name}: expected 64×64, got {img.size}"

    def test_amiga_rgb_fixture_images_are_valid_jpegs(self):
        rgb_dir = (
            FIXTURES_DIR
            / "amiga"
            / "Dataset_2024"
            / "Davis"
            / "2024-07-15"
            / "Amiga_Phone"
            / "Phone"
            / "rgb_jpeg"
        )
        image_files = sorted(rgb_dir.glob("*.jpg"))
        assert len(image_files) == 3, f"Expected 3 AMIGA RGB fixture images, found {len(image_files)}"

        for img_path in image_files:
            with Image.open(img_path) as img:
                assert img.mode == "RGB", f"{img_path.name}: expected RGB, got {img.mode}"
                assert img.size == (64, 64), f"{img_path.name}: expected 64×64, got {img.size}"
