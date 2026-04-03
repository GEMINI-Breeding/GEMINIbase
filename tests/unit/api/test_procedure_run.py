"""Tests for gemini.api.procedure_run module - ProcedureRun class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.procedure_run import ProcedureRun

MODULE = "gemini.api.procedure_run"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "procedure_id": uuid4(), "procedure_run_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestProcedureRunExists:
    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert ProcedureRun.exists(procedure_run_info={}, procedure_name="P") is True

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert ProcedureRun.exists(procedure_run_info={}, procedure_name="P") is False

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert ProcedureRun.exists(procedure_run_info={}, procedure_name="P") is False


class TestProcedureRunCreate:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = ProcedureRun.create(procedure_run_info={})
        assert result is not None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert ProcedureRun.create(procedure_run_info={}) is None


class TestProcedureRunGetById:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert ProcedureRun.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert ProcedureRun.get_by_id(uuid4()) is None


class TestProcedureRunGetAll:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(ProcedureRun.get_all()) == 1

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert ProcedureRun.get_all() is None


class TestProcedureRunSearch:
    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(ProcedureRun.search(procedure_name="P")) == 1

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert ProcedureRun.search(procedure_name="P") is None


class TestProcedureRunUpdate:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        pr = ProcedureRun(id=uid, procedure_id=uuid4(), procedure_run_info={})
        assert pr.update(procedure_run_info={"new": "v"}) is not None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        assert pr.update(procedure_run_info={"new": "v"}) is None


class TestProcedureRunDelete:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        assert pr.delete() is True

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        assert pr.delete() is False


class TestProcedureRunRefresh:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        pr = ProcedureRun(id=uid, procedure_id=uuid4(), procedure_run_info={})
        assert pr.refresh() is pr

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_not_found(self, m):
        m.get.return_value = None
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        assert pr.refresh() is pr


class TestProcedureRunGetSetInfo:
    @patch(f"{MODULE}.ProcedureRunModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(procedure_run_info={"k": "v"})
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        assert pr.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        pr = ProcedureRun(id=uid, procedure_id=uuid4(), procedure_run_info={})
        assert pr.set_info({"new": "v"}) is not None


class TestProcedureRunAssociations:
    def test_get_associated_procedure_success(self):
        proc_id = uuid4()
        pr = ProcedureRun(id=uuid4(), procedure_id=proc_id, procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get_by_id.return_value = MagicMock()
            result = pr.get_associated_procedure()
            assert result is not None

    def test_get_associated_procedure_not_found(self):
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get_by_id.return_value = None
            assert pr.get_associated_procedure() is None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_associate_procedure_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = MagicMock(id=uuid4())
            with patch.object(pr, "refresh"):
                result = pr.associate_procedure("Proc1")
                assert result is not None

    def test_associate_procedure_not_found(self):
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = None
            assert pr.associate_procedure("Missing") is None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_unassociate_procedure_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get_by_id.return_value = MagicMock()
            with patch.object(pr, "refresh"):
                result = pr.unassociate_procedure()
                assert result is not None

    @patch(f"{MODULE}.ProcedureRunModel")
    def test_belongs_to_procedure_true(self, m_model):
        m_model.exists.return_value = True
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = MagicMock(id=uuid4())
            assert pr.belongs_to_procedure("Proc1") is True

    @patch(f"{MODULE}.ProcedureRunsViewModel")
    def test_belongs_to_procedure_not_found(self, m_view):
        pr = ProcedureRun(id=uuid4(), procedure_id=uuid4(), procedure_run_info={})
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = None
            assert pr.belongs_to_procedure("Missing") is False
