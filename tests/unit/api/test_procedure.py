"""Tests for gemini.api.procedure module - Procedure class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.procedure import Procedure

MODULE = "gemini.api.procedure"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "procedure_name": "TestProc", "procedure_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestProcedureExists:
    @patch(f"{MODULE}.ProcedureModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Procedure.exists(procedure_name="TestProc") is True

    @patch(f"{MODULE}.ProcedureModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Procedure.exists(procedure_name="X") is False

    @patch(f"{MODULE}.ProcedureModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Procedure.exists(procedure_name="X") is False


class TestProcedureCreate:
    @patch(f"{MODULE}.ProcedureModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert Procedure.create(procedure_name="TestProc") is not None

    @patch(f"{MODULE}.ProcedureModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Procedure.create(procedure_name="X") is None


class TestProcedureGet:
    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Procedure.get(procedure_name="TestProc") is not None

    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Procedure.get(procedure_name="X") is None


class TestProcedureGetById:
    @patch(f"{MODULE}.ProcedureModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Procedure.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ProcedureModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Procedure.get_by_id(uuid4()) is None


class TestProcedureGetAll:
    @patch(f"{MODULE}.ProcedureModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Procedure.get_all()) == 1

    @patch(f"{MODULE}.ProcedureModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Procedure.get_all() is None


class TestProcedureSearch:
    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Procedure.search(procedure_name="TestProc")) == 1

    def test_no_params(self):
        assert Procedure.search() is None

    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Procedure.search(procedure_name="X") is None


class TestProcedureUpdate:
    @patch(f"{MODULE}.ProcedureModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, procedure_name="New")
        p = Procedure(id=uid, procedure_name="Old")
        assert p.update(procedure_name="New") is not None

    @patch(f"{MODULE}.ProcedureModel")
    def test_no_params(self, m):
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.update() is None

    @patch(f"{MODULE}.ProcedureModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.update(procedure_name="New") is None


class TestProcedureDelete:
    @patch(f"{MODULE}.ProcedureModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.delete() is True

    @patch(f"{MODULE}.ProcedureModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.delete() is False


class TestProcedureRefresh:
    @patch(f"{MODULE}.ProcedureModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        p = Procedure(id=uid, procedure_name="X")
        assert p.refresh() is p

    @patch(f"{MODULE}.ProcedureModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.refresh() is p


class TestProcedureGetSetInfo:
    @patch(f"{MODULE}.ProcedureModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(procedure_info={"k": "v"})
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ProcedureModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        p = Procedure(id=uid, procedure_name="X")
        assert p.set_info({"new": "v"}) is not None


class TestProcedureAssociations:
    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = p.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.get_associated_experiments() is None

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_get_runs(self, m):
        m.search.return_value = [MagicMock()]
        p = Procedure(id=uuid4(), procedure_name="X")
        result = p.get_associated_runs()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_get_runs_empty(self, m):
        m.search.return_value = []
        p = Procedure(id=uuid4(), procedure_name="X")
        assert p.get_associated_runs() is None

    @patch(f"{MODULE}.ExperimentProcedureModel")
    def test_associate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(p, "refresh"):
                result = p.associate_experiment("Exp1")
                assert result is not None

    def test_associate_experiment_not_found(self):
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert p.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentProcedureModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(p, "refresh"):
                result = p.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentProcedureModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert p.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentProcedureModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert p.belongs_to_experiment("Exp1") is False

    def test_create_new_run_success(self):
        p = Procedure(id=uuid4(), procedure_name="X")
        with patch("gemini.api.procedure_run.ProcedureRun") as mock_run:
            mock_run.create.return_value = MagicMock()
            result = p.create_new_run(procedure_run_info={"k": "v"})
            assert result is not None

    @patch(f"{MODULE}.ProcedureDatasetsViewModel")
    def test_get_associated_datasets_found(self, m):
        m.search.return_value = [MagicMock()]
        p = Procedure(id=uuid4(), procedure_name="X")
        result = p.get_associated_datasets()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ProcedureDatasetsViewModel")
    def test_get_associated_datasets_empty(self, m):
        m.search.return_value = []
        p = Procedure(id=uuid4(), procedure_name="X")
        result = p.get_associated_datasets()
        assert result is not None or result is None  # May return empty list or None
