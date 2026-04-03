"""Tests for gemini.api.sensor_type module - SensorType class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.sensor_type import SensorType

MODULE = "gemini.api.sensor_type"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "sensor_type_name": "Temperature", "sensor_type_info": {"unit": "C"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSensorTypeExists:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert SensorType.exists(sensor_type_name="Temperature") is True

    @patch(f"{MODULE}.SensorTypeModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert SensorType.exists(sensor_type_name="X") is False

    @patch(f"{MODULE}.SensorTypeModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert SensorType.exists(sensor_type_name="X") is False


class TestSensorTypeCreate:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert SensorType.create(sensor_type_name="Temperature") is not None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert SensorType.create(sensor_type_name="X") is None


class TestSensorTypeGet:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert SensorType.get(sensor_type_name="Temperature") is not None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert SensorType.get(sensor_type_name="X") is None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert SensorType.get(sensor_type_name="X") is None


class TestSensorTypeGetById:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert SensorType.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert SensorType.get_by_id(uuid4()) is None


class TestSensorTypeGetAll:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(SensorType.get_all()) == 1

    @patch(f"{MODULE}.SensorTypeModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert SensorType.get_all() is None


class TestSensorTypeSearch:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(SensorType.search(sensor_type_name="Temperature")) == 1

    def test_no_params(self):
        assert SensorType.search() is None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert SensorType.search(sensor_type_name="X") is None


class TestSensorTypeUpdate:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, sensor_type_name="New")
        st = SensorType(id=uid, sensor_type_name="Old")
        assert st.update(sensor_type_name="New") is not None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_no_params(self, m):
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.update() is None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.update(sensor_type_name="New") is None


class TestSensorTypeDelete:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.delete() is True

    @patch(f"{MODULE}.SensorTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.delete() is False


class TestSensorTypeRefresh:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        st = SensorType(id=uid, sensor_type_name="X")
        assert st.refresh() is st

    @patch(f"{MODULE}.SensorTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.refresh() is st


class TestSensorTypeGetSetInfo:
    @patch(f"{MODULE}.SensorTypeModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(sensor_type_info={"k": "v"})
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.get_info() == {"k": "v"}

    @patch(f"{MODULE}.SensorTypeModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(sensor_type_info=None)
        st = SensorType(id=uuid4(), sensor_type_name="X")
        assert st.get_info() is None

    @patch(f"{MODULE}.SensorTypeModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        st = SensorType(id=uid, sensor_type_name="X")
        assert st.set_info({"new": "v"}) is not None
