"""
Integration tests for record table inserts against real PostgreSQL.
These are the core data tables for phenotyping — sensor readings,
trait measurements, etc. No mocks.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest
import uuid
from datetime import datetime, date

pytestmark = pytest.mark.integration


# ============================================================
# Sensor Records
# ============================================================

class TestSensorRecords:

    def test_create_single_record(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        rec = SensorRecordModel.create(
            timestamp=datetime(2024, 6, 15, 10, 30, 0),
            collection_date=date(2024, 6, 15),
            sensor_name="RGB Camera",
            sensor_data={"file_path": "/data/img001.jpg", "resolution": "4K"},
            experiment_name="Field Trial",
            season_name="2024",
            site_name="Davis",
        )
        assert rec.id is not None
        assert rec.sensor_data["resolution"] == "4K"

    def test_bulk_insert_sensor_records(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        records = []
        base = datetime(2024, 6, 15, 10, 0, 0)
        for i in range(50):
            ts = datetime(2024, 6, 15, 10 + i // 60, i % 60, 0)
            records.append({
                "id": str(uuid.uuid4()),
                "timestamp": ts,
                "collection_date": date(2024, 6, 15),
                "sensor_name": "Bulk Sensor",
                "sensor_data": {"frame": i},
                "experiment_name": "Bulk Exp",
                "season_name": "2024",
                "site_name": "Davis",
            })
        ids = SensorRecordModel.insert_bulk(
            constraint="sensor_records_unique", data=records
        )
        assert len(ids) == 50

    def test_search_sensor_records(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        SensorRecordModel.create(
            timestamp=datetime(2024, 7, 1, 8, 0, 0),
            collection_date=date(2024, 7, 1),
            sensor_name="Search Sensor",
            sensor_data={"val": 1},
            experiment_name="Search Exp",
            season_name="2024",
            site_name="Davis",
        )
        results = SensorRecordModel.search(sensor_name="Search Sensor")
        assert len(results) >= 1
        assert results[0].sensor_data["val"] == 1

    def test_sensor_record_with_plot(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        rec = SensorRecordModel.create(
            timestamp=datetime(2024, 6, 15, 12, 0, 0),
            collection_date=date(2024, 6, 15),
            sensor_name="Plot Sensor",
            sensor_data={"ndvi": 0.75},
            experiment_name="Plot Exp",
            season_name="2024",
            site_name="Davis",
            plot_number=42,
            plot_row_number=3,
            plot_column_number=7,
        )
        fetched = SensorRecordModel.get(rec.id)
        assert fetched.plot_number == 42
        assert fetched.plot_row_number == 3

    def test_record_with_file_reference(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        rec = SensorRecordModel.create(
            timestamp=datetime(2024, 6, 15, 14, 0, 0),
            collection_date=date(2024, 6, 15),
            sensor_name="File Sensor",
            sensor_data={},
            experiment_name="File Exp",
            season_name="2024",
            site_name="Davis",
            record_file="gemini/images/scan_001.tiff",
            record_info={"size_mb": 250, "format": "GeoTIFF"},
        )
        fetched = SensorRecordModel.get(rec.id)
        assert fetched.record_file == "gemini/images/scan_001.tiff"
        assert fetched.record_info["size_mb"] == 250


# ============================================================
# Trait Records
# ============================================================

class TestTraitRecords:

    def test_create_trait_record(self, setup_real_db):
        from gemini.db.models.columnar.trait_records import TraitRecordModel
        rec = TraitRecordModel.create(
            timestamp=datetime(2024, 6, 15, 9, 0, 0),
            collection_date=date(2024, 6, 15),
            trait_name="Plant Height",
            trait_value=125.5,
            experiment_name="Trait Exp",
            season_name="2024",
            site_name="Davis",
            plot_number=1, plot_row_number=1, plot_column_number=1,
        )
        assert rec.trait_value == 125.5

    def test_bulk_insert_trait_records(self, setup_real_db):
        from gemini.db.models.columnar.trait_records import TraitRecordModel
        records = []
        for i in range(100):
            ts = datetime(2024, 6, 15, 9 + i // 60, i % 60, 0)
            records.append({
                "id": str(uuid.uuid4()),
                "timestamp": ts,
                "collection_date": date(2024, 6, 15),
                "trait_name": "Bulk Height",
                "trait_value": 100.0 + i * 0.5,
                "experiment_name": "Bulk Trait Exp",
                "season_name": "2024",
                "site_name": "Davis",
                "plot_number": i,
                "plot_row_number": i // 10,
                "plot_column_number": i % 10,
            })
        ids = TraitRecordModel.insert_bulk(
            constraint="trait_records_unique", data=records
        )
        assert len(ids) == 100

    def test_search_trait_by_name(self, setup_real_db):
        from gemini.db.models.columnar.trait_records import TraitRecordModel
        TraitRecordModel.create(
            timestamp=datetime(2024, 7, 2, 10, 0, 0),
            collection_date=date(2024, 7, 2),
            trait_name="Leaf Width",
            trait_value=3.2,
            experiment_name="Search Trait Exp",
            season_name="2024",
            site_name="Davis",
        )
        results = TraitRecordModel.search(trait_name="Leaf Width")
        assert len(results) >= 1
        assert results[0].trait_value == pytest.approx(3.2, abs=0.01)

    def test_stream_trait_records(self, setup_real_db):
        from gemini.db.models.columnar.trait_records import TraitRecordModel
        for i in range(5):
            TraitRecordModel.create(
                timestamp=datetime(2024, 8, 1, 10, 0, i),
                collection_date=date(2024, 8, 1),
                trait_name="Stream Trait",
                trait_value=float(i),
                experiment_name="Stream Exp",
                season_name="2024",
                site_name="Davis",
            )
        streamed = list(TraitRecordModel.stream(trait_name="Stream Trait"))
        assert len(streamed) == 5


# ============================================================
# Dataset Records
# ============================================================

class TestDatasetRecords:

    def test_create_dataset_record(self, setup_real_db):
        from gemini.db.models.columnar.dataset_records import DatasetRecordModel
        rec = DatasetRecordModel.create(
            timestamp=datetime(2024, 6, 15, 10, 0, 0),
            collection_date=date(2024, 6, 15),
            dataset_name="Weather Data",
            dataset_data={"temp_c": 32.1, "humidity": 65},
            experiment_name="DS Exp",
            season_name="2024",
            site_name="Davis",
        )
        assert rec.dataset_data["temp_c"] == 32.1

    def test_bulk_insert_dataset_records(self, setup_real_db):
        from gemini.db.models.columnar.dataset_records import DatasetRecordModel
        records = [{
            "id": str(uuid.uuid4()),
            "timestamp": datetime(2024, 6, 15, 10, i % 60, i // 60),
            "collection_date": date(2024, 6, 15),
            "dataset_name": "Bulk DS",
            "dataset_data": {"reading": i},
            "experiment_name": "Bulk DS Exp",
            "season_name": "2024",
            "site_name": "Davis",
        } for i in range(25)]
        ids = DatasetRecordModel.insert_bulk(
            constraint="dataset_records_unique", data=records
        )
        assert len(ids) == 25


# ============================================================
# Model Records
# ============================================================

class TestModelRecords:

    def test_create_model_record(self, setup_real_db):
        from gemini.db.models.columnar.model_records import ModelRecordModel
        rec = ModelRecordModel.create(
            timestamp=datetime(2024, 6, 15, 10, 0, 0),
            collection_date=date(2024, 6, 15),
            model_name="YOLOv8",
            model_data={"predictions": [{"class": "weed", "confidence": 0.92}]},
            experiment_name="Model Exp",
            season_name="2024",
            site_name="Davis",
            record_file="results/yolo_output.json",
        )
        assert rec.model_data["predictions"][0]["confidence"] == 0.92


# ============================================================
# Procedure Records
# ============================================================

class TestProcedureRecords:

    def test_create_procedure_record(self, setup_real_db):
        from gemini.db.models.columnar.procedure_records import ProcedureRecordModel
        rec = ProcedureRecordModel.create(
            timestamp=datetime(2024, 6, 15, 10, 0, 0),
            collection_date=date(2024, 6, 15),
            procedure_name="Irrigation",
            procedure_data={"volume_liters": 500, "duration_min": 30},
            experiment_name="Proc Exp",
            season_name="2024",
            site_name="Davis",
        )
        assert rec.procedure_data["volume_liters"] == 500


# ============================================================
# Script Records
# ============================================================

class TestScriptRecords:

    def test_create_script_record(self, setup_real_db):
        from gemini.db.models.columnar.script_records import ScriptRecordModel
        rec = ScriptRecordModel.create(
            timestamp=datetime(2024, 6, 15, 10, 0, 0),
            collection_date=date(2024, 6, 15),
            script_name="preprocess.py",
            script_data={"input_files": 42, "output_format": "csv"},
            experiment_name="Script Exp",
            season_name="2024",
            site_name="Davis",
        )
        assert rec.script_data["input_files"] == 42


# ============================================================
# Cross-cutting: pagination on records
# ============================================================

class TestRecordPagination:

    def test_sensor_records_pagination(self, setup_real_db):
        from gemini.db.models.columnar.sensor_records import SensorRecordModel
        for i in range(10):
            SensorRecordModel.create(
                timestamp=datetime(2024, 9, 1, 10, 0, i),
                collection_date=date(2024, 9, 1),
                sensor_name="Paginate Sensor",
                sensor_data={"idx": i},
                experiment_name="Page Exp",
                season_name="2024",
                site_name="Davis",
            )
        page1 = SensorRecordModel.all(limit=3, offset=0)
        page2 = SensorRecordModel.all(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3

    def test_count_records(self, setup_real_db):
        from gemini.db.models.columnar.trait_records import TraitRecordModel
        assert TraitRecordModel.count() == 0
        for i in range(5):
            TraitRecordModel.create(
                timestamp=datetime(2024, 9, 2, 10, 0, i),
                collection_date=date(2024, 9, 2),
                trait_name="Count Trait",
                trait_value=float(i),
                experiment_name="Count Exp",
                season_name="2024",
                site_name="Davis",
            )
        assert TraitRecordModel.count() == 5
