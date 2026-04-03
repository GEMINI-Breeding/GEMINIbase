"""Tests for gemini.api.trait_record module - TraitRecord class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime

from gemini.api.trait_record import TraitRecord

MODULE = "gemini.api.trait_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "timestamp": datetime(2024, 6, 1, 12, 0, 0),
        "collection_date": date(2024, 6, 1), "dataset_id": uuid4(),
        "dataset_name": "DS1", "trait_id": uuid4(), "trait_name": "LeafArea",
        "trait_value": 42.0, "experiment_id": uuid4(),
        "experiment_name": "Exp1", "season_id": uuid4(), "season_name": "Summer",
        "site_id": uuid4(), "site_name": "Site1", "plot_id": uuid4(),
        "plot_number": 1, "plot_row_number": 1, "plot_column_number": 1,
        "record_info": {"note": "test"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestTraitRecordExists:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert TraitRecord.exists(
            timestamp=datetime.now(), trait_name="T", dataset_name="D",
            experiment_name="E", season_name="S", site_name="Si",
            plot_number=1, plot_row_number=1, plot_column_number=1
        ) is True

    @patch(f"{MODULE}.TraitRecordModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert TraitRecord.exists(
            timestamp=datetime.now(), trait_name="X", dataset_name="Y",
            experiment_name="Z", season_name="S", site_name="S"
        ) is False

    @patch(f"{MODULE}.TraitRecordModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        with pytest.raises(Exception):
            TraitRecord.exists(
                timestamp=datetime.now(), trait_name="X", dataset_name="Y",
                experiment_name="Z", season_name="S", site_name="S"
            )


class TestTraitRecordGetById:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert TraitRecord.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert TraitRecord.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        assert TraitRecord.get_by_id(uuid4()) is None


class TestTraitRecordGetAll:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        result = TraitRecord.get_all(limit=10)
        assert len(result) == 1

    @patch(f"{MODULE}.TraitRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert TraitRecord.get_all() is None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert TraitRecord.get_all() is None


class TestTraitRecordSearch:
    @patch(f"{MODULE}.TraitRecordsIMMVModel")
    def test_yields_results(self, m):
        m.stream.return_value = iter([_make_db()])
        results = list(TraitRecord.search(trait_name="LeafArea"))
        assert len(results) == 1

    def test_no_params_yields_nothing(self):
        results = list(TraitRecord.search())
        assert len(results) == 0


class TestTraitRecordFilter:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_yields_results(self, m):
        m.filter_records.return_value = iter([_make_db()])
        results = list(TraitRecord.filter(trait_names=["LeafArea"]))
        assert len(results) == 1

    @patch(f"{MODULE}.TraitRecordModel")
    def test_exception(self, m):
        m.filter_records.side_effect = Exception("err")
        results = list(TraitRecord.filter(trait_names=["LeafArea"]))
        assert len(results) == 0


class TestTraitRecordUpdate:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        tr = TraitRecord(id=uid, timestamp=datetime.now(), trait_name="T")
        assert tr.update(trait_value=99.0) is not None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_no_params(self, m):
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.update() is None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.update(trait_value=99.0) is None


class TestTraitRecordDelete:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.delete() is True

    @patch(f"{MODULE}.TraitRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.delete() is False


class TestTraitRecordRefresh:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        tr = TraitRecord(id=uid, timestamp=datetime.now(), trait_name="T")
        result = tr.refresh()
        assert result is tr

    @patch(f"{MODULE}.TraitRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.refresh() is None


class TestTraitRecordGetSetInfo:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(record_info={"k": "v"})
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.TraitRecordModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(record_info=None)
        tr = TraitRecord(id=uuid4(), timestamp=datetime.now(), trait_name="T")
        assert tr.get_info() is None

    @patch(f"{MODULE}.TraitRecordModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        tr = TraitRecord(id=uid, timestamp=datetime.now(), trait_name="T")
        assert tr.set_info({"new": "v"}) is not None


class TestTraitRecordInsert:
    @patch(f"{MODULE}.TraitRecordModel")
    def test_insert_success(self, m):
        m.insert_bulk.return_value = [str(uuid4())]
        record = TraitRecord(
            timestamp=datetime.now(), trait_name="T", dataset_name="D",
            trait_value=42.0, experiment_name="E"
        )
        success, ids = TraitRecord.insert([record])
        assert success is True
        assert len(ids) == 1

    @patch(f"{MODULE}.TraitRecordModel")
    def test_insert_empty(self, m):
        success, ids = TraitRecord.insert([])
        assert success is False
        assert ids == []
