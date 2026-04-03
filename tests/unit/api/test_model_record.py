"""Tests for gemini.api.model_record module - ModelRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.model_record import ModelRecord

MODULE = "gemini.api.model_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "model_id": uuid4(), "model_name": "Model1",
        "model_data": {"k": "v"}, "experiment_id": uuid4(),
        "experiment_name": "Exp1", "season_id": None, "season_name": None,
        "site_id": None, "site_name": None, "record_file": None,
        "record_info": {"note": "test"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestModelRecordExists:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ModelRecord.exists(timestamp=datetime.now(), model_name="Model1", dataset_name="DS1", experiment_name="Exp1", season_name="S", site_name="S") is True

    @patch(f"{MODULE}.ModelRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ModelRecord.exists(timestamp=datetime.now(), model_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S") is False

    @patch(f"{MODULE}.ModelRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert ModelRecord.exists(timestamp=datetime.now(), model_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S") is False


class TestModelRecordGetById:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ModelRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ModelRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ModelRecord.get_by_id(uuid4()) is None


class TestModelRecordGetAll:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ModelRecord.get_all()) == 1

    @patch(f"{MODULE}.ModelRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ModelRecord.get_all() is None


class TestModelRecordUpdate:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        mr = ModelRecord(id=uid, timestamp=datetime.now(), model_name="Model1")
        assert mr.update(model_data={"new": "v"}) is not None

    @patch(f"{MODULE}.ModelRecordModel")
    def test_no_params(self, m):
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.update() is None

    @patch(f"{MODULE}.ModelRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.update(model_data={"new": "v"}) is None


class TestModelRecordDelete:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.delete() is True

    @patch(f"{MODULE}.ModelRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.delete() is False


class TestModelRecordRefresh:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        mr = ModelRecord(id=uid, timestamp=datetime.now(), model_name="X")
        assert mr.refresh() is not None

    @patch(f"{MODULE}.ModelRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.refresh() is None


class TestModelRecordGetSetInfo:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ModelRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        mr = ModelRecord(id=uuid4(), timestamp=datetime.now(), model_name="X")
        assert mr.get_info() is None

    @patch(f"{MODULE}.ModelRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        mr = ModelRecord(id=uid, timestamp=datetime.now(), model_name="X")
        assert mr.set_info({"new": "v"}) is not None


class TestModelRecordCreate:
    def test_create_success(self):
        with patch.object(ModelRecord, "insert", return_value=(True, [uuid4()])):
            with patch.object(ModelRecord, "get_by_id", return_value=MagicMock()):
                result = ModelRecord.create(
                    timestamp=datetime.now(),
                    dataset_name="DS1",
                    model_name="M1",
                    model_data={"k": "v"},
                    experiment_name="Exp1"
                )
                assert result is not None

    def test_create_no_context_raises(self):
        with pytest.raises(TypeError):
            ModelRecord.create(
                timestamp=datetime.now(),
                dataset_name="DS1",
                model_name="M1",
                model_data={"k": "v"}
            )

    def test_create_no_data_raises(self):
        with pytest.raises(TypeError):
            ModelRecord.create(
                timestamp=datetime.now(),
                dataset_name="DS1",
                model_name="M1",
                model_data={},
                experiment_name="Exp1"
            )

    def test_create_no_insert(self):
        result = ModelRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            model_name="M1",
            model_data={"k": "v"},
            experiment_name="Exp1",
            insert_on_create=False
        )
        assert result is not None


class TestModelRecordGet:
    @patch(f"{MODULE}.ModelRecordsIMMVModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = ModelRecord.get(
            timestamp=datetime.now(),
            model_name="M1",
            dataset_name="DS1",
            experiment_name="Exp1"
        )
        assert result is not None

    @patch(f"{MODULE}.ModelRecordsIMMVModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert ModelRecord.get(
            timestamp=datetime.now(),
            model_name="M1",
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None

    def test_get_no_timestamp(self):
        assert ModelRecord.get(
            timestamp=None,
            model_name="M1",
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None


class TestModelRecordSearch:
    @patch(f"{MODULE}.ModelRecordsIMMVModel")
    def test_search_results(self, m):
        m.stream.return_value = [_make_db()]
        gen = ModelRecord.search(model_name="M1")
        result = next(gen)
        assert result is not None

    def test_search_no_params_empty(self):
        gen = ModelRecord.search()
        results = list(gen)
        assert results == []


class TestModelRecordFilter:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_filter_results(self, m):
        m.filter_records.return_value = [_make_db()]
        gen = ModelRecord.filter(model_names=["M1"])
        result = next(gen)
        assert result is not None

    def test_filter_no_params_empty(self):
        gen = ModelRecord.filter()
        results = list(gen)
        assert results == []


class TestModelRecordInsert:
    @patch(f"{MODULE}.ModelRecordModel")
    def test_insert_empty(self, m):
        success, ids = ModelRecord.insert([])
        assert success is False
        assert ids == []
