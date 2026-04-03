"""Tests for gemini.api.dataset_type module - DatasetType class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.dataset_type import DatasetType

MODULE = "gemini.api.dataset_type"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "dataset_type_name": "Sensor", "dataset_type_info": {"desc": "sensor data"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestDatasetTypeExists:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert DatasetType.exists(dataset_type_name="Sensor") is True

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert DatasetType.exists(dataset_type_name="X") is False

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert DatasetType.exists(dataset_type_name="X") is False


class TestDatasetTypeCreate:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert DatasetType.create(dataset_type_name="Sensor") is not None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert DatasetType.create(dataset_type_name="X") is None


class TestDatasetTypeGet:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert DatasetType.get(dataset_type_name="Sensor") is not None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert DatasetType.get(dataset_type_name="X") is None


class TestDatasetTypeGetById:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert DatasetType.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert DatasetType.get_by_id(uuid4()) is None


class TestDatasetTypeGetAll:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(DatasetType.get_all()) == 1

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert DatasetType.get_all() is None


class TestDatasetTypeSearch:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(DatasetType.search(dataset_type_name="Sensor")) == 1

    def test_no_params(self):
        assert DatasetType.search() is None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert DatasetType.search(dataset_type_name="X") is None


class TestDatasetTypeUpdate:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, dataset_type_name="New")
        dt = DatasetType(id=uid, dataset_type_name="Old")
        assert dt.update(dataset_type_name="New") is not None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_no_params(self, m):
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.update() is None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.update(dataset_type_name="New") is None


class TestDatasetTypeDelete:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.delete() is True

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.delete() is False


class TestDatasetTypeRefresh:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        dt = DatasetType(id=uid, dataset_type_name="X")
        assert dt.refresh() is dt

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.refresh() is dt


class TestDatasetTypeGetSetInfo:
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(dataset_type_info={"k": "v"})
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.get_info() == {"k": "v"}

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(dataset_type_info=None)
        dt = DatasetType(id=uuid4(), dataset_type_name="X")
        assert dt.get_info() is None

    @patch(f"{MODULE}.DatasetTypeModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        dt = DatasetType(id=uid, dataset_type_name="X")
        assert dt.set_info({"new": "v"}) is not None
