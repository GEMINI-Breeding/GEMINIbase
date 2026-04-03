"""Tests for gemini.api.model module - Model class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.model import Model

MODULE = "gemini.api.model"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "model_name": "TestModel", "model_url": "http://model", "model_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestModelExists:
    @patch(f"{MODULE}.ModelModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Model.exists(model_name="TestModel") is True

    @patch(f"{MODULE}.ModelModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Model.exists(model_name="X") is False

    @patch(f"{MODULE}.ModelModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Model.exists(model_name="X") is False


class TestModelCreate:
    @patch(f"{MODULE}.ModelModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert Model.create(model_name="TestModel") is not None

    @patch(f"{MODULE}.ModelModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Model.create(model_name="X") is None


class TestModelGet:
    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Model.get(model_name="TestModel") is not None

    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Model.get(model_name="X") is None


class TestModelGetById:
    @patch(f"{MODULE}.ModelModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Model.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.ModelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Model.get_by_id(uuid4()) is None


class TestModelGetAll:
    @patch(f"{MODULE}.ModelModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Model.get_all()) == 1

    @patch(f"{MODULE}.ModelModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Model.get_all() is None


class TestModelSearch:
    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Model.search(model_name="TestModel")) == 1

    def test_no_params(self):
        assert Model.search() is None

    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Model.search(model_name="X") is None


class TestModelUpdate:
    @patch(f"{MODULE}.ModelModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, model_name="New")
        md = Model(id=uid, model_name="Old")
        assert md.update(model_name="New") is not None

    @patch(f"{MODULE}.ModelModel")
    def test_no_params(self, m):
        md = Model(id=uuid4(), model_name="X")
        assert md.update() is None

    @patch(f"{MODULE}.ModelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        md = Model(id=uuid4(), model_name="X")
        assert md.update(model_name="New") is None


class TestModelDelete:
    @patch(f"{MODULE}.ModelModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        md = Model(id=uuid4(), model_name="X")
        assert md.delete() is True

    @patch(f"{MODULE}.ModelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        md = Model(id=uuid4(), model_name="X")
        assert md.delete() is False


class TestModelRefresh:
    @patch(f"{MODULE}.ModelModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        md = Model(id=uid, model_name="X")
        assert md.refresh() is md

    @patch(f"{MODULE}.ModelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        md = Model(id=uuid4(), model_name="X")
        assert md.refresh() is md


class TestModelGetSetInfo:
    @patch(f"{MODULE}.ModelModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(model_info={"k": "v"})
        md = Model(id=uuid4(), model_name="X")
        assert md.get_info() == {"k": "v"}

    @patch(f"{MODULE}.ModelModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(model_info=None)
        md = Model(id=uuid4(), model_name="X")
        assert md.get_info() is None

    @patch(f"{MODULE}.ModelModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        md = Model(id=uid, model_name="X")
        assert md.set_info({"new": "v"}) is not None


class TestModelAssociations:
    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = md.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        md = Model(id=uuid4(), model_name="X")
        assert md.get_associated_experiments() is None

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_get_runs(self, m):
        m.search.return_value = [MagicMock()]
        md = Model(id=uuid4(), model_name="X")
        result = md.get_associated_runs()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ModelRunsViewModel")
    def test_get_runs_empty(self, m):
        m.search.return_value = []
        md = Model(id=uuid4(), model_name="X")
        assert md.get_associated_runs() is None

    @patch(f"{MODULE}.ExperimentModelModel")
    def test_associate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(md, "refresh"):
                result = md.associate_experiment("Exp1")
                assert result is not None

    def test_associate_experiment_not_found(self):
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert md.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentModelModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(md, "refresh"):
                result = md.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentModelModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert md.unassociate_experiment("Exp1") is None

    @patch(f"{MODULE}.ExperimentModelModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert md.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentModelModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert md.belongs_to_experiment("Exp1") is False

    def test_create_new_run_success(self):
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.model_run.ModelRun") as mock_run:
            mock_run.create.return_value = MagicMock()
            result = md.create_new_run(model_run_info={"k": "v"})
            assert result is not None

    def test_create_new_run_failure(self):
        md = Model(id=uuid4(), model_name="X")
        with patch("gemini.api.model_run.ModelRun") as mock_run:
            mock_run.create.return_value = None
            assert md.create_new_run(model_run_info={"k": "v"}) is None

    @patch(f"{MODULE}.ModelDatasetsViewModel")
    def test_get_associated_datasets_found(self, m):
        m.search.return_value = [MagicMock()]
        md = Model(id=uuid4(), model_name="X")
        result = md.get_associated_datasets()
        m.search.assert_called_once()

    @patch(f"{MODULE}.ModelDatasetsViewModel")
    def test_get_associated_datasets_empty(self, m):
        m.search.return_value = []
        md = Model(id=uuid4(), model_name="X")
        assert md.get_associated_datasets() is None
