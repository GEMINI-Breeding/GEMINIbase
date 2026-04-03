"""Tests for gemini.api.dataset_record module - DatasetRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.dataset_record import DatasetRecord

MODULE = "gemini.api.dataset_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "dataset_data": {"k": "v"},
        "experiment_name": "Exp1", "experiment_id": uuid4(),
        "season_name": None, "season_id": None,
        "site_name": None, "site_id": None,
        "record_file": None, "record_info": {"note": "test"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestDatasetRecordExists:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert DatasetRecord.exists(timestamp=datetime.now(), dataset_name="D", experiment_name="E", season_name="S", site_name="S") is True

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert DatasetRecord.exists(timestamp=datetime.now(), dataset_name="X", experiment_name="Y", season_name="S", site_name="S") is False

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert DatasetRecord.exists(timestamp=datetime.now(), dataset_name="X", experiment_name="Y", season_name="S", site_name="S") is False


class TestDatasetRecordGetById:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert DatasetRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert DatasetRecord.get_by_id(uuid4()) is None


class TestDatasetRecordGetAll:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(DatasetRecord.get_all()) == 1

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert DatasetRecord.get_all() is None


class TestDatasetRecordUpdate:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        dr = DatasetRecord(id=uid, timestamp=datetime.now(), dataset_name="D")
        assert dr.update(dataset_data={"new": "v"}) is not None

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_no_params(self, m):
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.update() is None

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.update(dataset_data={"new": "v"}) is None


class TestDatasetRecordDelete:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.delete() is True

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.delete() is False


class TestDatasetRecordRefresh:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        dr = DatasetRecord(id=uid, timestamp=datetime.now(), dataset_name="D")
        assert dr.refresh() is not None

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.refresh() is None


class TestDatasetRecordGetSetInfo:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        dr = DatasetRecord(id=uuid4(), timestamp=datetime.now(), dataset_name="D")
        assert dr.get_info() is None

    @patch(f"{MODULE}.DatasetRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        dr = DatasetRecord(id=uid, timestamp=datetime.now(), dataset_name="D")
        assert dr.set_info({"new": "v"}) is not None


class TestDatasetRecordCreate:
    def test_create_success(self):
        with patch.object(DatasetRecord, "insert", return_value=(True, [uuid4()])):
            with patch.object(DatasetRecord, "get_by_id", return_value=MagicMock()):
                result = DatasetRecord.create(
                    timestamp=datetime.now(),
                    dataset_name="DS1",
                    dataset_data={"k": "v"},
                    experiment_name="Exp1"
                )
                assert result is not None

    def test_create_no_context(self):
        result = DatasetRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            dataset_data={"k": "v"}
        )
        assert result is None

    def test_create_no_dataset_name(self):
        result = DatasetRecord.create(
            timestamp=datetime.now(),
            dataset_data={"k": "v"},
            experiment_name="Exp1"
        )
        assert result is None

    def test_create_no_data(self):
        result = DatasetRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            dataset_data={},
            experiment_name="Exp1"
        )
        assert result is None

    def test_create_insert_failure(self):
        with patch.object(DatasetRecord, "insert", return_value=(False, [])):
            result = DatasetRecord.create(
                timestamp=datetime.now(),
                dataset_name="DS1",
                dataset_data={"k": "v"},
                experiment_name="Exp1"
            )
            assert result is None

    def test_create_no_insert(self):
        result = DatasetRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            dataset_data={"k": "v"},
            experiment_name="Exp1",
            insert_on_create=False
        )
        assert result is not None


class TestDatasetRecordGet:
    @patch(f"{MODULE}.DatasetRecordsIMMVModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = DatasetRecord.get(
            timestamp=datetime.now(),
            dataset_name="DS1",
            experiment_name="Exp1"
        )
        assert result is not None

    @patch(f"{MODULE}.DatasetRecordsIMMVModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert DatasetRecord.get(
            timestamp=datetime.now(),
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None

    def test_get_no_timestamp(self):
        assert DatasetRecord.get(
            timestamp=None,
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None

    def test_get_no_dataset_name(self):
        assert DatasetRecord.get(
            timestamp=datetime.now(),
            dataset_name=None,
            experiment_name="Exp1"
        ) is None

    def test_get_no_context(self):
        assert DatasetRecord.get(
            timestamp=datetime.now(),
            dataset_name="DS1"
        ) is None


class TestDatasetRecordSearch:
    @patch(f"{MODULE}.DatasetRecordsIMMVModel")
    def test_search_results(self, m):
        m.stream.return_value = [_make_db()]
        gen = DatasetRecord.search(dataset_name="DS1")
        result = next(gen)
        assert result is not None

    def test_search_no_params(self):
        gen = DatasetRecord.search()
        result = next(gen)
        assert result is None


class TestDatasetRecordFilter:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_filter_results(self, m):
        m.filter_records.return_value = [_make_db()]
        gen = DatasetRecord.filter(dataset_names=["DS1"])
        result = next(gen)
        assert result is not None

    def test_filter_no_params(self):
        gen = DatasetRecord.filter()
        result = next(gen)
        assert result is None


class TestDatasetRecordInsert:
    @patch(f"{MODULE}.DatasetRecordModel")
    def test_insert_empty(self, m):
        success, ids = DatasetRecord.insert([])
        assert success is False
        assert ids == []
