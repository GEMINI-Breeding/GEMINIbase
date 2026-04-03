"""Tests for gemini.api.data_type module - DataType class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.data_type import DataType

MODULE = "gemini.api.data_type"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "data_type_name": "Temperature", "data_type_info": {"unit": "C"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestDataTypeExists:
    @patch(f"{MODULE}.DataTypeModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert DataType.exists(data_type_name="Temperature") is True

    @patch(f"{MODULE}.DataTypeModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert DataType.exists(data_type_name="X") is False

    @patch(f"{MODULE}.DataTypeModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert DataType.exists(data_type_name="X") is False


class TestDataTypeCreate:
    @patch(f"{MODULE}.DataTypeModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert DataType.create(data_type_name="Temperature") is not None

    @patch(f"{MODULE}.DataTypeModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert DataType.create(data_type_name="X") is None


class TestDataTypeGet:
    @patch(f"{MODULE}.DataTypeModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert DataType.get(data_type_name="Temperature") is not None

    @patch(f"{MODULE}.DataTypeModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert DataType.get(data_type_name="X") is None


class TestDataTypeGetById:
    @patch(f"{MODULE}.DataTypeModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert DataType.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.DataTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert DataType.get_by_id(uuid4()) is None


class TestDataTypeGetAll:
    @patch(f"{MODULE}.DataTypeModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(DataType.get_all()) == 1

    @patch(f"{MODULE}.DataTypeModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert DataType.get_all() is None


class TestDataTypeSearch:
    @patch(f"{MODULE}.DataTypeModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(DataType.search(data_type_name="Temperature")) == 1

    def test_no_params(self):
        assert DataType.search() is None

    @patch(f"{MODULE}.DataTypeModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert DataType.search(data_type_name="X") is None


class TestDataTypeUpdate:
    @patch(f"{MODULE}.DataTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, data_type_name="New")
        dt = DataType(id=uid, data_type_name="Old")
        assert dt.update(data_type_name="New") is not None

    @patch(f"{MODULE}.DataTypeModel")
    def test_no_params(self, m):
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.update() is None

    @patch(f"{MODULE}.DataTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.update(data_type_name="New") is None


class TestDataTypeDelete:
    @patch(f"{MODULE}.DataTypeModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.delete() is True

    @patch(f"{MODULE}.DataTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.delete() is False


class TestDataTypeRefresh:
    @patch(f"{MODULE}.DataTypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        dt = DataType(id=uid, data_type_name="X")
        assert dt.refresh() is dt

    @patch(f"{MODULE}.DataTypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.refresh() is dt


class TestDataTypeGetSetInfo:
    @patch(f"{MODULE}.DataTypeModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(data_type_info={"k": "v"})
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.get_info() == {"k": "v"}

    @patch(f"{MODULE}.DataTypeModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(data_type_info=None)
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.get_info() is None

    @patch(f"{MODULE}.DataTypeModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        dt = DataType(id=uid, data_type_name="X")
        assert dt.set_info({"new": "v"}) is not None


class TestDataTypeAssociations:
    @patch(f"{MODULE}.DataTypeFormatsViewModel")
    def test_get_associated_data_formats(self, m):
        m.search.return_value = [MagicMock()]
        dt = DataType(id=uuid4(), data_type_name="X")
        with patch(f"{MODULE}.DataFormat", create=True):
            result = dt.get_associated_data_formats()
            m.search.assert_called_once()

    @patch(f"{MODULE}.DataTypeFormatsViewModel")
    def test_get_associated_data_formats_empty(self, m):
        m.search.return_value = []
        dt = DataType(id=uuid4(), data_type_name="X")
        assert dt.get_associated_data_formats() is None

    @patch(f"{MODULE}.DataTypeFormatModel")
    def test_associate_data_format(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        dt = DataType(id=uuid4(), data_type_name="X")
        with patch(f"{MODULE}.DataFormat", create=True) as mock_df:
            mock_df.get.return_value = MagicMock(id=uuid4())
            with patch.object(dt, "refresh"):
                result = dt.associate_data_format("CSV")

    @patch(f"{MODULE}.DataTypeFormatModel")
    def test_belongs_to_data_format(self, m_assoc):
        m_assoc.exists.return_value = True
        dt = DataType(id=uuid4(), data_type_name="X")
        with patch("gemini.api.data_format.DataFormat") as mock_df:
            mock_df.get.return_value = MagicMock(id=uuid4())
            assert dt.belongs_to_data_format("CSV") is True
