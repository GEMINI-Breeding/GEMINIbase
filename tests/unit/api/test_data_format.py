"""Tests for gemini.api.data_format module - DataFormat class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.data_format import DataFormat

MODULE = "gemini.api.data_format"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "data_format_name": "CSV", "data_format_mime_type": "text/csv", "data_format_info": {"desc": "comma separated"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestDataFormatExists:
    @patch(f"{MODULE}.DataFormatModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert DataFormat.exists(data_format_name="CSV") is True

    @patch(f"{MODULE}.DataFormatModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert DataFormat.exists(data_format_name="X") is False

    @patch(f"{MODULE}.DataFormatModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert DataFormat.exists(data_format_name="X") is False


class TestDataFormatCreate:
    @patch(f"{MODULE}.DataFormatModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert DataFormat.create(data_format_name="CSV") is not None

    @patch(f"{MODULE}.DataFormatModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert DataFormat.create(data_format_name="X") is None


class TestDataFormatGet:
    @patch(f"{MODULE}.DataFormatModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert DataFormat.get(data_format_name="CSV") is not None

    @patch(f"{MODULE}.DataFormatModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert DataFormat.get(data_format_name="X") is None


class TestDataFormatGetById:
    @patch(f"{MODULE}.DataFormatModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert DataFormat.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.DataFormatModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert DataFormat.get_by_id(uuid4()) is None


class TestDataFormatGetAll:
    @patch(f"{MODULE}.DataFormatModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(DataFormat.get_all()) == 1

    @patch(f"{MODULE}.DataFormatModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert DataFormat.get_all() is None


class TestDataFormatSearch:
    @patch(f"{MODULE}.DataFormatModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(DataFormat.search(data_format_name="CSV")) == 1

    def test_no_params(self):
        assert DataFormat.search() is None

    @patch(f"{MODULE}.DataFormatModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert DataFormat.search(data_format_name="X") is None


class TestDataFormatUpdate:
    @patch(f"{MODULE}.DataFormatModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, data_format_name="New")
        df = DataFormat(id=uid, data_format_name="Old")
        assert df.update(data_format_name="New") is not None

    @patch(f"{MODULE}.DataFormatModel")
    def test_no_params(self, m):
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.update() is None

    @patch(f"{MODULE}.DataFormatModel")
    def test_not_found(self, m):
        m.get.return_value = None
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.update(data_format_name="New") is None


class TestDataFormatDelete:
    @patch(f"{MODULE}.DataFormatModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.delete() is True

    @patch(f"{MODULE}.DataFormatModel")
    def test_not_found(self, m):
        m.get.return_value = None
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.delete() is False


class TestDataFormatRefresh:
    @patch(f"{MODULE}.DataFormatModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        df = DataFormat(id=uid, data_format_name="X")
        assert df.refresh() is df

    @patch(f"{MODULE}.DataFormatModel")
    def test_not_found(self, m):
        m.get.return_value = None
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.refresh() is df


class TestDataFormatGetSetInfo:
    @patch(f"{MODULE}.DataFormatModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(data_format_info={"k": "v"})
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.get_info() == {"k": "v"}

    @patch(f"{MODULE}.DataFormatModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(data_format_info=None)
        df = DataFormat(id=uuid4(), data_format_name="X")
        assert df.get_info() is None

    @patch(f"{MODULE}.DataFormatModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        df = DataFormat(id=uid, data_format_name="X")
        assert df.set_info({"new": "v"}) is not None


class TestDataFormatAssociations:
    @patch(f"{MODULE}.DataTypeFormatsViewModel")
    def test_get_associated_data_types(self, m):
        m.search.return_value = [MagicMock()]
        df = DataFormat(id=uuid4(), data_format_name="CSV")
        with patch(f"{MODULE}.DataType", create=True):
            result = df.get_associated_data_types()
            m.search.assert_called_once()

    @patch(f"{MODULE}.DataTypeFormatsViewModel")
    def test_get_associated_data_types_empty(self, m):
        m.search.return_value = []
        df = DataFormat(id=uuid4(), data_format_name="CSV")
        assert df.get_associated_data_types() is None

    @patch(f"{MODULE}.DataTypeFormatModel")
    def test_belongs_to_data_type(self, m_assoc):
        m_assoc.exists.return_value = True
        df = DataFormat(id=uuid4(), data_format_name="CSV")
        with patch("gemini.api.data_type.DataType") as mock_dt:
            mock_dt.get.return_value = MagicMock(id=uuid4())
            assert df.belongs_to_data_type("Temperature") is True
