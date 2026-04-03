"""Tests for gemini.api.script module - Script class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.script import Script

MODULE = "gemini.api.script"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "script_name": "TestScript", "script_url": "http://script", "script_extension": ".py", "script_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestScriptExists:
    @patch(f"{MODULE}.ScriptModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Script.exists(script_name="TestScript") is True

    @patch(f"{MODULE}.ScriptModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Script.exists(script_name="X") is False

    @patch(f"{MODULE}.ScriptModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Script.exists(script_name="X") is False


class TestScriptCreate:
    @patch(f"{MODULE}.ScriptModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert Script.create(script_name="TestScript") is not None

    @patch(f"{MODULE}.ScriptModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Script.create(script_name="X") is None


class TestScriptGet:
    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Script.get(script_name="TestScript") is not None

    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Script.get(script_name="X") is None


class TestScriptGetById:
    @patch(f"{MODULE}.ScriptModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Script.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ScriptModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Script.get_by_id(uuid4()) is None


class TestScriptGetAll:
    @patch(f"{MODULE}.ScriptModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Script.get_all()) == 1

    @patch(f"{MODULE}.ScriptModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Script.get_all() is None


class TestScriptSearch:
    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Script.search(script_name="TestScript")) == 1

    def test_no_params(self):
        assert Script.search() is None

    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Script.search(script_name="X") is None


class TestScriptUpdate:
    @patch(f"{MODULE}.ScriptModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, script_name="New")
        s = Script(id=uid, script_name="Old")
        assert s.update(script_name="New") is not None

    @patch(f"{MODULE}.ScriptModel")
    def test_no_params(self, m):
        s = Script(id=uuid4(), script_name="X")
        assert s.update() is None

    @patch(f"{MODULE}.ScriptModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Script(id=uuid4(), script_name="X")
        assert s.update(script_name="New") is None


class TestScriptDelete:
    @patch(f"{MODULE}.ScriptModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        s = Script(id=uuid4(), script_name="X")
        assert s.delete() is True

    @patch(f"{MODULE}.ScriptModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Script(id=uuid4(), script_name="X")
        assert s.delete() is False


class TestScriptRefresh:
    @patch(f"{MODULE}.ScriptModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        s = Script(id=uid, script_name="X")
        assert s.refresh() is s

    @patch(f"{MODULE}.ScriptModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Script(id=uuid4(), script_name="X")
        assert s.refresh() is s


class TestScriptGetSetInfo:
    @patch(f"{MODULE}.ScriptModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(script_info={"k": "v"})
        s = Script(id=uuid4(), script_name="X")
        assert s.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ScriptModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        s = Script(id=uid, script_name="X")
        assert s.set_info({"new": "v"}) is not None


class TestScriptAssociations:
    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = s.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        s = Script(id=uuid4(), script_name="X")
        assert s.get_associated_experiments() is None

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_get_runs(self, m):
        m.search.return_value = [MagicMock()]
        s = Script(id=uuid4(), script_name="X")
        result = s.get_associated_runs()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ScriptRunsViewModel")
    def test_get_runs_empty(self, m):
        m.search.return_value = []
        s = Script(id=uuid4(), script_name="X")
        assert s.get_associated_runs() is None

    @patch(f"{MODULE}.ExperimentScriptModel")
    def test_associate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.associate_experiment("Exp1")
                assert result is not None

    def test_associate_experiment_not_found(self):
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert s.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentScriptModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentScriptModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert s.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentScriptModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert s.belongs_to_experiment("Exp1") is False

    def test_create_new_run_success(self):
        s = Script(id=uuid4(), script_name="X")
        with patch("gemini.api.script_run.ScriptRun") as mock_run:
            mock_run.create.return_value = MagicMock()
            result = s.create_new_run(script_run_info={"k": "v"})
            assert result is not None

    @patch(f"{MODULE}.ScriptDatasetsViewModel")
    def test_get_associated_datasets_found(self, m):
        m.search.return_value = [MagicMock()]
        s = Script(id=uuid4(), script_name="X")
        result = s.get_associated_datasets()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ScriptDatasetsViewModel")
    def test_get_associated_datasets_empty(self, m):
        m.search.return_value = []
        s = Script(id=uuid4(), script_name="X")
        assert s.get_associated_datasets() is None
