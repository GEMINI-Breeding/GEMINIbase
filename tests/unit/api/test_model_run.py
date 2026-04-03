"""Tests for gemini.api.model_run module - ModelRun class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.model_run import ModelRun

MODULE = "gemini.api.model_run"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "model_id": uuid4(), "model_run_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestModelRunExists:
    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ModelRun.exists(model_run_info={}, model_name="M") is True

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ModelRun.exists(model_run_info={}, model_name="M") is False

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert ModelRun.exists(model_run_info={}, model_name="M") is False


class TestModelRunCreate:
    @patch(f"{MODULE}.ModelRunModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = ModelRun.create(model_run_info={})
        assert result is not None

    @patch(f"{MODULE}.ModelRunModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert ModelRun.create(model_run_info={}) is None


class TestModelRunGetById:
    @patch(f"{MODULE}.ModelRunModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ModelRun.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ModelRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ModelRun.get_by_id(uuid4()) is None


class TestModelRunGetAll:
    @patch(f"{MODULE}.ModelRunModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ModelRun.get_all()) == 1

    @patch(f"{MODULE}.ModelRunModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ModelRun.get_all() is None


class TestModelRunSearch:
    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(ModelRun.search(model_name="M")) == 1

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert ModelRun.search(model_name="M") is None


class TestModelRunUpdate:
    @patch(f"{MODULE}.ModelRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        mr = ModelRun(id=uid, model_id=uuid4(), model_run_info={})
        assert mr.update(model_run_info={"new": "v"}) is not None

    @patch(f"{MODULE}.ModelRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        assert mr.update(model_run_info={"new": "v"}) is None


class TestModelRunDelete:
    @patch(f"{MODULE}.ModelRunModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        assert mr.delete() is True

    @patch(f"{MODULE}.ModelRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        assert mr.delete() is False


class TestModelRunRefresh:
    @patch(f"{MODULE}.ModelRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        mr = ModelRun(id=uid, model_id=uuid4(), model_run_info={})
        assert mr.refresh() is mr

    @patch(f"{MODULE}.ModelRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        assert mr.refresh() is mr


class TestModelRunGetSetInfo:
    @patch(f"{MODULE}.ModelRunModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(model_run_info={"k": "v"})
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        assert mr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ModelRunModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        mr = ModelRun(id=uid, model_id=uuid4(), model_run_info={})
        assert mr.set_info({"new": "v"}) is not None


class TestModelRunAssociations:
    def test_get_associated_model_success(self):
        model_id = uuid4()
        mr = ModelRun(id=uuid4(), model_id=model_id, model_run_info={})
        with patch("gemini.api.model.Model") as mock_model:
            mock_model.get_by_id.return_value = MagicMock()
            result = mr.get_associated_model()
            assert result is not None

    def test_get_associated_model_not_found(self):
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        with patch("gemini.api.model.Model") as mock_model:
            mock_model.get_by_id.return_value = None
            assert mr.get_associated_model() is None

    @patch(f"{MODULE}.ModelRunModel")
    def test_associate_model_success(self, m_model):
        m_model.get_by_parameters.return_value = None
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = MagicMock(id=uuid4())
            with patch.object(ModelRun, "refresh"):
                result = mr.associate_model("Model1")
                assert result is not None

    def test_associate_model_not_found(self):
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = None
            assert mr.associate_model("Missing") is None

    @patch(f"{MODULE}.ModelRunModel")
    def test_unassociate_model_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        model_id = uuid4()
        mr = ModelRun(id=uuid4(), model_id=model_id, model_run_info={})
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get_by_id.return_value = MagicMock()
            with patch.object(mr, "refresh"):
                result = mr.unassociate_model()
                assert result is not None

    @patch(f"{MODULE}.ModelRunModel")
    def test_belongs_to_model_true(self, m_model):
        m_model.exists.return_value = True
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = MagicMock(id=uuid4())
            assert mr.belongs_to_model("Model1") is True

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_belongs_to_model_not_found(self, m_view):
        mr = ModelRun(id=uuid4(), model_id=uuid4(), model_run_info={})
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = None
            assert mr.belongs_to_model("Missing") is False
