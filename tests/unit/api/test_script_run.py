"""Tests for gemini.api.script_run module - ScriptRun class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.script_run import ScriptRun

MODULE = "gemini.api.script_run"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "script_id": uuid4(), "script_run_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestScriptRunExists:
    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ScriptRun.exists(script_run_info={}, script_name="S") is True

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ScriptRun.exists(script_run_info={}, script_name="S") is False

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert ScriptRun.exists(script_run_info={}, script_name="S") is False


class TestScriptRunCreate:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = ScriptRun.create(script_run_info={})
        assert result is not None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert ScriptRun.create(script_run_info={}) is None


class TestScriptRunGetById:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ScriptRun.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ScriptRun.get_by_id(uuid4()) is None


class TestScriptRunGetAll:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ScriptRun.get_all()) == 1

    @patch(f"{MODULE}.ScriptRunModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ScriptRun.get_all() is None


class TestScriptRunSearch:
    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(ScriptRun.search(script_name="S")) == 1

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert ScriptRun.search(script_name="S") is None


class TestScriptRunUpdate:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = ScriptRun(id=uid, script_id=uuid4(), script_run_info={})
        assert sr.update(script_run_info={"new": "v"}) is not None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        assert sr.update(script_run_info={"new": "v"}) is None


class TestScriptRunDelete:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        assert sr.delete() is True

    @patch(f"{MODULE}.ScriptRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        assert sr.delete() is False


class TestScriptRunRefresh:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        sr = ScriptRun(id=uid, script_id=uuid4(), script_run_info={})
        assert sr.refresh() is sr

    @patch(f"{MODULE}.ScriptRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        assert sr.refresh() is sr


class TestScriptRunGetSetInfo:
    @patch(f"{MODULE}.ScriptRunModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(script_run_info={"k": "v"})
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        assert sr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ScriptRunModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sr = ScriptRun(id=uid, script_id=uuid4(), script_run_info={})
        assert sr.set_info({"new": "v"}) is not None


class TestScriptRunAssociations:
    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_get_associated_script_success(self, m_view):
        m_view.get_by_parameters.return_value = MagicMock(script_id=uuid4())
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_script:
            mock_script.get_by_id.return_value = MagicMock()
            result = sr.get_associated_script()
            assert result is not None

    def test_get_associated_script_not_found(self):
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_script:
            mock_script.get_by_id.return_value = None
            assert sr.get_associated_script() is None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_associate_script_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = MagicMock(id=uuid4())
            with patch.object(sr, "refresh"):
                result = sr.associate_script("Script1")
                assert result is not None

    def test_associate_script_not_found(self):
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = None
            assert sr.associate_script("Missing") is None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_unassociate_script_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get_by_id.return_value = MagicMock()
            with patch.object(sr, "refresh"):
                result = sr.unassociate_script()
                assert result is not None

    @patch(f"{MODULE}.ScriptRunModel")
    def test_belongs_to_script_true(self, m_model):
        m_model.exists.return_value = True
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = MagicMock(id=uuid4())
            assert sr.belongs_to_script("Script1") is True

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_belongs_to_script_not_found(self, m_view):
        sr = ScriptRun(id=uuid4(), script_id=uuid4(), script_run_info={})
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = None
            assert sr.belongs_to_script("Missing") is False
