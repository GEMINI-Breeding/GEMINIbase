"""Tests for gemini.api.sensor_record module - SensorRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.sensor_record import SensorRecord

MODULE = "gemini.api.sensor_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "sensor_id": uuid4(), "sensor_name": "Sensor1",
        "sensor_data": {"temp": 22.5}, "experiment_id": uuid4(),
        "experiment_name": "Exp1", "season_id": uuid4(), "season_name": "Summer",
        "site_id": uuid4(), "site_name": "Site1", "plot_id": uuid4(),
        "plot_number": 1, "plot_row_number": 1, "plot_column_number": 1,
        "record_file": None, "record_info": {"note": "test"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSensorRecordExists:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert SensorRecord.exists(
            timestamp=datetime.now(), sensor_name="S", dataset_name="D",
            experiment_name="E", season_name="Season", site_name="Site",
            plot_number=1, plot_row_number=1, plot_column_number=1
        ) is True

    @patch(f"{MODULE}.SensorRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert SensorRecord.exists(
            timestamp=datetime.now(), sensor_name="X", dataset_name="Y",
            experiment_name="Z", season_name="S", site_name="S"
        ) is False

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert SensorRecord.exists(
            timestamp=datetime.now(), sensor_name="X", dataset_name="Y",
            experiment_name="Z", season_name="S", site_name="S"
        ) is False


class TestSensorRecordGetById:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert SensorRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert SensorRecord.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        assert SensorRecord.get_by_id(uuid4()) is None


class TestSensorRecordGetAll:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        result = SensorRecord.get_all(limit=10)
        assert len(result) == 1

    @patch(f"{MODULE}.SensorRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert SensorRecord.get_all() is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert SensorRecord.get_all() is None


class TestSensorRecordGet:
    @patch(f"{MODULE}.SensorRecordsIMMVModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = SensorRecord.get(
            timestamp=datetime.now(), sensor_name="S", dataset_name="D",
            experiment_name="E", plot_number=1, plot_row_number=1, plot_column_number=1
        )
        assert result is not None

    @patch(f"{MODULE}.SensorRecordsIMMVModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        result = SensorRecord.get(
            timestamp=datetime.now(), sensor_name="S", dataset_name="D",
            experiment_name="E", plot_number=1, plot_row_number=1, plot_column_number=1
        )
        assert result is None

    def test_missing_timestamp(self):
        result = SensorRecord.get(
            timestamp=None, sensor_name="S", dataset_name="D",
            experiment_name="E", plot_number=1, plot_row_number=1, plot_column_number=1
        )
        assert result is None


class TestSensorRecordSearch:
    @patch(f"{MODULE}.SensorRecordsIMMVModel")
    def test_yields_results(self, m):
        m.stream.return_value = iter([_make_db()])
        results = list(SensorRecord.search(sensor_name="S"))
        assert len(results) == 1

    def test_no_params_yields_nothing(self):
        results = list(SensorRecord.search())
        assert len(results) == 0


class TestSensorRecordFilter:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_yields_results(self, m):
        m.filter_records.return_value = iter([_make_db()])
        results = list(SensorRecord.filter(sensor_names=["S"]))
        assert len(results) == 1

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.filter_records.side_effect = Exception("err")
        results = list(SensorRecord.filter(sensor_names=["S"]))
        assert len(results) == 0


class TestSensorRecordUpdate:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = SensorRecord(id=uid, timestamp=datetime.now(), sensor_name="S")
        assert sr.update(sensor_data={"new": "v"}) is not None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_no_params(self, m):
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.update() is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.update(sensor_data={"new": "v"}) is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.update(sensor_data={"new": "v"}) is None


class TestSensorRecordDelete:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.delete() is True

    @patch(f"{MODULE}.SensorRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.delete() is False

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.delete() is False


class TestSensorRecordRefresh:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        sr = SensorRecord(id=uid, timestamp=datetime.now(), sensor_name="S")
        result = sr.refresh()
        assert result is sr

    @patch(f"{MODULE}.SensorRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.refresh() is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.refresh() is None


class TestSensorRecordGetSetInfo:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.SensorRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.get_info() is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_get_info_not_found(self, m):
        m.get.return_value = None
        sr = SensorRecord(id=uuid4(), timestamp=datetime.now(), sensor_name="S")
        assert sr.get_info() is None

    @patch(f"{MODULE}.SensorRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = SensorRecord(id=uid, timestamp=datetime.now(), sensor_name="S")
        assert sr.set_info({"new": "v"}) is not None


class TestSensorRecordInsert:
    @patch(f"{MODULE}.SensorRecordModel")
    def test_insert_success(self, m):
        m.insert_bulk.return_value = [str(uuid4())]
        record = SensorRecord(
            timestamp=datetime.now(), sensor_name="S", dataset_name="D",
            sensor_data={"temp": 22.5}, experiment_name="E"
        )
        success, ids = SensorRecord.insert([record])
        assert success is True
        assert len(ids) == 1

    @patch(f"{MODULE}.SensorRecordModel")
    def test_insert_empty(self, m):
        success, ids = SensorRecord.insert([])
        assert success is False
        assert ids == []

    @patch(f"{MODULE}.SensorRecordModel")
    def test_insert_exception(self, m):
        m.insert_bulk.side_effect = Exception("err")
        record = SensorRecord(
            timestamp=datetime.now(), sensor_name="S", dataset_name="D",
            sensor_data={"temp": 22.5}, experiment_name="E"
        )
        success, ids = SensorRecord.insert([record])
        assert success is False
