"""Tests for gemini.api.script_record module - ScriptRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.script_record import ScriptRecord

MODULE = "gemini.api.script_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "script_id": uuid4(), "script_name": "Script1",
        "script_data": {"k": "v"}, "experiment_id": uuid4(),
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


class TestScriptRecordExists:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ScriptRecord.exists(timestamp=datetime.now(), script_name="S", dataset_name="D", experiment_name="E", season_name="S", site_name="S") is True

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ScriptRecord.exists(timestamp=datetime.now(), script_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S") is False

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        with pytest.raises(Exception):
            ScriptRecord.exists(timestamp=datetime.now(), script_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S")


class TestScriptRecordGetById:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ScriptRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ScriptRecord.get_by_id(uuid4()) is None


class TestScriptRecordGetAll:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ScriptRecord.get_all()) == 1

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ScriptRecord.get_all() is None


class TestScriptRecordUpdate:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = ScriptRecord(id=uid, timestamp=datetime.now(), script_name="S")
        assert sr.update(script_data={"new": "v"}) is not None

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_no_params(self, m):
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.update() is None

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.update(script_data={"new": "v"}) is None


class TestScriptRecordDelete:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.delete() is True

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.delete() is False


class TestScriptRecordRefresh:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        sr = ScriptRecord(id=uid, timestamp=datetime.now(), script_name="S")
        assert sr.refresh() is not None

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.refresh() is None


class TestScriptRecordGetSetInfo:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        sr = ScriptRecord(id=uuid4(), timestamp=datetime.now(), script_name="S")
        assert sr.get_info() is None

    @patch(f"{MODULE}.ScriptRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = ScriptRecord(id=uid, timestamp=datetime.now(), script_name="S")
        assert sr.set_info({"new": "v"}) is not None


class TestScriptRecordCreate:
    def test_create_success(self):
        with patch.object(ScriptRecord, "insert", return_value=(True, [uuid4()])):
            with patch.object(ScriptRecord, "get_by_id", return_value=MagicMock()):
                result = ScriptRecord.create(
                    timestamp=datetime.now(),
                    dataset_name="DS1",
                    script_name="S1",
                    script_data={"k": "v"},
                    experiment_name="Exp1"
                )
                assert result is not None

    def test_create_no_context_raises(self):
        with pytest.raises(TypeError):
            ScriptRecord.create(
                timestamp=datetime.now(),
                dataset_name="DS1",
                script_name="S1",
                script_data={"k": "v"}
            )

    def test_create_no_insert(self):
        result = ScriptRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            script_name="S1",
            script_data={"k": "v"},
            experiment_name="Exp1",
            insert_on_create=False
        )
        assert result is not None


class TestScriptRecordGet:
    @patch(f"{MODULE}.ScriptRecordsIMMVModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = ScriptRecord.get(
            timestamp=datetime.now(),
            script_name="S1",
            dataset_name="DS1",
            experiment_name="Exp1"
        )
        assert result is not None

    def test_get_no_timestamp(self):
        assert ScriptRecord.get(
            timestamp=None,
            script_name="S1",
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None


class TestScriptRecordSearch:
    @patch(f"{MODULE}.ScriptRecordsIMMVModel")
    def test_search_results(self, m):
        m.stream.return_value = [_make_db()]
        gen = ScriptRecord.search(script_name="S1")
        result = next(gen)
        assert result is not None

    def test_search_no_params_empty(self):
        gen = ScriptRecord.search()
        results = list(gen)
        assert results == []


class TestScriptRecordFilter:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_filter_results(self, m):
        m.filter_records.return_value = [_make_db()]
        gen = ScriptRecord.filter(script_names=["S1"])
        result = next(gen)
        assert result is not None

    def test_filter_no_params_empty(self):
        gen = ScriptRecord.filter()
        results = list(gen)
        assert results == []


class TestScriptRecordInsert:
    @patch(f"{MODULE}.ScriptRecordModel")
    def test_insert_empty(self, m):
        success, ids = ScriptRecord.insert([])
        assert success is False
        assert ids == []
