"""Tests for gemini.api.dataset module - Dataset class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date

from gemini.api.dataset import Dataset

MODULE = "gemini.api.dataset"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "dataset_name": "TestDS",
        "collection_date": date(2024, 6, 1),
        "dataset_info": {"k": "v"}, "dataset_type_id": 1,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestDatasetExists:
    @patch(f"{MODULE}.DatasetModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Dataset.exists(dataset_name="TestDS") is True

    @patch(f"{MODULE}.DatasetModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Dataset.exists(dataset_name="X") is False

    @patch(f"{MODULE}.DatasetModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Dataset.exists(dataset_name="X") is False


class TestDatasetCreate:
    @patch(f"{MODULE}.DatasetModel")
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_success(self, m_type, m_ds):
        m_type.get_or_create.return_value = MagicMock(id=1)
        m_ds.get_or_create.return_value = _make_db()
        result = Dataset.create(dataset_name="TestDS")
        assert result is not None

    @patch(f"{MODULE}.DatasetModel")
    @patch(f"{MODULE}.DatasetTypeModel")
    def test_exception(self, m_type, m_ds):
        m_type.get_or_create.side_effect = Exception("err")
        assert Dataset.create(dataset_name="X") is None


class TestDatasetGet:
    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Dataset.get(dataset_name="TestDS") is not None

    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Dataset.get(dataset_name="X") is None


class TestDatasetGetById:
    @patch(f"{MODULE}.DatasetModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Dataset.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.DatasetModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Dataset.get_by_id(uuid4()) is None


class TestDatasetGetAll:
    @patch(f"{MODULE}.DatasetModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Dataset.get_all()) == 1

    @patch(f"{MODULE}.DatasetModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Dataset.get_all() is None


class TestDatasetSearch:
    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Dataset.search(dataset_name="TestDS")) == 1

    def test_no_params(self):
        assert Dataset.search() is None

    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Dataset.search(dataset_name="X") is None


class TestDatasetUpdate:
    @patch(f"{MODULE}.DatasetModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, dataset_name="New")
        ds = Dataset(id=uid, dataset_name="Old", collection_date=date.today(), dataset_type_id=1)
        assert ds.update(dataset_name="New") is not None

    @patch(f"{MODULE}.DatasetModel")
    def test_no_params(self, m):
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.update() is None

    @patch(f"{MODULE}.DatasetModel")
    def test_not_found(self, m):
        m.get.return_value = None
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.update(dataset_name="New") is None


class TestDatasetDelete:
    @patch(f"{MODULE}.DatasetModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.delete() is True

    @patch(f"{MODULE}.DatasetModel")
    def test_not_found(self, m):
        m.get.return_value = None
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.delete() is False


class TestDatasetRefresh:
    @patch(f"{MODULE}.DatasetModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        ds = Dataset(id=uid, dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.refresh() is ds

    @patch(f"{MODULE}.DatasetModel")
    def test_not_found(self, m):
        m.get.return_value = None
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.refresh() is ds


class TestDatasetGetSetInfo:
    @patch(f"{MODULE}.DatasetModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(dataset_info={"k": "v"})
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.get_info() == {"k": "v"}

    @patch(f"{MODULE}.DatasetModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(dataset_info=None)
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.get_info() is None

    @patch(f"{MODULE}.DatasetModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        ds = Dataset(id=uid, dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.set_info({"new": "v"}) is not None


class TestDatasetAssociations:
    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True):
            result = ds.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        assert ds.get_associated_experiments() is None

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_associate_experiment(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(ds, "refresh"):
                result = ds.associate_experiment("Exp1")

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_associate_experiment_already_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            result = ds.associate_experiment("Exp1")
            assert result is not None

    def test_associate_experiment_exp_not_found(self):
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert ds.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_associate_experiment_exception(self, m_assoc):
        m_assoc.get_by_parameters.side_effect = Exception("err")
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert ds.associate_experiment("Exp1") is None

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(ds, "refresh"):
                result = ds.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert ds.unassociate_experiment("Exp1") is None

    def test_unassociate_experiment_exp_not_found(self):
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert ds.unassociate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert ds.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentDatasetModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert ds.belongs_to_experiment("Exp1") is False

    def test_belongs_to_experiment_exp_not_found(self):
        ds = Dataset(id=uuid4(), dataset_name="X", collection_date=date.today(), dataset_type_id=1)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert ds.belongs_to_experiment("Missing") is False
