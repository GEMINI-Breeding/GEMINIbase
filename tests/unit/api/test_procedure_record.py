"""Tests for gemini.api.procedure_record module - ProcedureRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.procedure_record import ProcedureRecord

MODULE = "gemini.api.procedure_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "procedure_id": uuid4(), "procedure_name": "Proc1",
        "procedure_data": {"k": "v"}, "experiment_id": uuid4(),
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


class TestProcedureRecordExists:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ProcedureRecord.exists(timestamp=datetime.now(), procedure_name="P", dataset_name="D", experiment_name="E", season_name="S", site_name="S") is True

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ProcedureRecord.exists(timestamp=datetime.now(), procedure_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S") is False

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        with pytest.raises(Exception):
            ProcedureRecord.exists(timestamp=datetime.now(), procedure_name="X", dataset_name="Y", experiment_name="Z", season_name="S", site_name="S")


class TestProcedureRecordGetById:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ProcedureRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ProcedureRecord.get_by_id(uuid4()) is None


class TestProcedureRecordGetAll:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ProcedureRecord.get_all()) == 1

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ProcedureRecord.get_all() is None


class TestProcedureRecordUpdate:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        pr = ProcedureRecord(id=uid, timestamp=datetime.now(), procedure_name="P")
        assert pr.update(procedure_data={"new": "v"}) is not None

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_no_params(self, m):
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.update() is None

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.update(procedure_data={"new": "v"}) is None


class TestProcedureRecordDelete:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.delete() is True

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.delete() is False


class TestProcedureRecordRefresh:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        pr = ProcedureRecord(id=uid, timestamp=datetime.now(), procedure_name="P")
        assert pr.refresh() is not None

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.refresh() is None


class TestProcedureRecordGetSetInfo:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        pr = ProcedureRecord(id=uuid4(), timestamp=datetime.now(), procedure_name="P")
        assert pr.get_info() is None

    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        pr = ProcedureRecord(id=uid, timestamp=datetime.now(), procedure_name="P")
        assert pr.set_info({"new": "v"}) is not None


class TestProcedureRecordCreate:
    def test_create_success(self):
        with patch.object(ProcedureRecord, "insert", return_value=(True, [uuid4()])):
            with patch.object(ProcedureRecord, "get_by_id", return_value=MagicMock()):
                result = ProcedureRecord.create(
                    timestamp=datetime.now(),
                    dataset_name="DS1",
                    procedure_name="P1",
                    procedure_data={"k": "v"},
                    experiment_name="Exp1"
                )
                assert result is not None

    def test_create_no_context_raises(self):
        with pytest.raises(TypeError):
            ProcedureRecord.create(
                timestamp=datetime.now(),
                dataset_name="DS1",
                procedure_name="P1",
                procedure_data={"k": "v"}
            )

    def test_create_no_insert(self):
        result = ProcedureRecord.create(
            timestamp=datetime.now(),
            dataset_name="DS1",
            procedure_name="P1",
            procedure_data={"k": "v"},
            experiment_name="Exp1",
            insert_on_create=False
        )
        assert result is not None


class TestProcedureRecordGet:
    @patch(f"{MODULE}.ProcedureRecordsIMMVModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = ProcedureRecord.get(
            timestamp=datetime.now(),
            procedure_name="P1",
            dataset_name="DS1",
            experiment_name="Exp1"
        )
        assert result is not None

    def test_get_no_timestamp(self):
        assert ProcedureRecord.get(
            timestamp=None,
            procedure_name="P1",
            dataset_name="DS1",
            experiment_name="Exp1"
        ) is None


class TestProcedureRecordSearch:
    @patch(f"{MODULE}.ProcedureRecordsIMMVModel")
    def test_search_results(self, m):
        m.stream.return_value = [_make_db()]
        gen = ProcedureRecord.search(procedure_name="P1")
        result = next(gen)
        assert result is not None

    def test_search_no_params_empty(self):
        gen = ProcedureRecord.search()
        results = list(gen)
        assert results == []


class TestProcedureRecordFilter:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_filter_results(self, m):
        m.filter_records.return_value = [_make_db()]
        gen = ProcedureRecord.filter(procedure_names=["P1"])
        result = next(gen)
        assert result is not None

    def test_filter_no_params_empty(self):
        gen = ProcedureRecord.filter()
        results = list(gen)
        assert results == []


class TestProcedureRecordInsert:
    @patch(f"{MODULE}.ProcedureRecordModel")
    def test_insert_empty(self, m):
        success, ids = ProcedureRecord.insert([])
        assert success is False
        assert ids == []
