"""Tests for gemini.api.trait module - Trait class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.trait import Trait

MODULE = "gemini.api.trait"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "trait_name": "LeafArea", "trait_units": "cm2",
        "trait_level_id": 1, "trait_info": {"k": "v"}, "trait_metrics": None,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestTraitExists:
    @patch(f"{MODULE}.TraitModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Trait.exists(trait_name="LeafArea") is True

    @patch(f"{MODULE}.TraitModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Trait.exists(trait_name="X") is False

    @patch(f"{MODULE}.TraitModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Trait.exists(trait_name="X") is False


class TestTraitCreate:
    @patch(f"{MODULE}.TraitModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Trait.create(trait_name="LeafArea", trait_units="cm2")
        assert result is not None

    @patch(f"{MODULE}.TraitModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Trait.create(trait_name="X", trait_units="u") is None


class TestTraitGet:
    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Trait.get(trait_name="LeafArea") is not None

    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Trait.get(trait_name="X") is None


class TestTraitGetById:
    @patch(f"{MODULE}.TraitModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Trait.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.TraitModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Trait.get_by_id(uuid4()) is None


class TestTraitGetAll:
    @patch(f"{MODULE}.TraitModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Trait.get_all()) == 1

    @patch(f"{MODULE}.TraitModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Trait.get_all() is None


class TestTraitSearch:
    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Trait.search(trait_name="LeafArea")) == 1

    def test_no_params(self):
        assert Trait.search() is None

    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Trait.search(trait_name="X") is None


class TestTraitUpdate:
    @patch(f"{MODULE}.TraitModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, trait_name="New")
        t = Trait(id=uid, trait_name="Old", trait_units="cm2")
        assert t.update(trait_name="New") is not None

    @patch(f"{MODULE}.TraitModel")
    def test_no_params(self, m):
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.update() is None

    @patch(f"{MODULE}.TraitModel")
    def test_not_found(self, m):
        m.get.return_value = None
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.update(trait_name="New") is None


class TestTraitDelete:
    @patch(f"{MODULE}.TraitModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.delete() is True

    @patch(f"{MODULE}.TraitModel")
    def test_not_found(self, m):
        m.get.return_value = None
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.delete() is False


class TestTraitRefresh:
    @patch(f"{MODULE}.TraitModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        t = Trait(id=uid, trait_name="X", trait_units="u")
        assert t.refresh() is t

    @patch(f"{MODULE}.TraitModel")
    def test_not_found(self, m):
        m.get.return_value = None
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.refresh() is t


class TestTraitGetSetInfo:
    @patch(f"{MODULE}.TraitModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(trait_info={"k": "v"})
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.get_info() == {"k": "v"}

    @patch(f"{MODULE}.TraitModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(trait_info=None)
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.get_info() is None

    @patch(f"{MODULE}.TraitModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        t = Trait(id=uid, trait_name="X", trait_units="u")
        assert t.set_info({"new": "v"}) is not None


class TestTraitAssociations:
    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = t.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.get_associated_experiments() is None

    @patch(f"{MODULE}.ExperimentTraitModel")
    def test_associate_experiment(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(t, "refresh"):
                result = t.associate_experiment("Exp1")

    def test_associate_experiment_not_found(self):
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert t.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentTraitModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(t, "refresh"):
                result = t.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentTraitModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert t.unassociate_experiment("Exp1") is None

    @patch(f"{MODULE}.ExperimentTraitModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert t.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentTraitModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert t.belongs_to_experiment("Exp1") is False

    @patch(f"{MODULE}.TraitDatasetsViewModel")
    def test_get_associated_datasets_found(self, m):
        m.search.return_value = [MagicMock()]
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        result = t.get_associated_datasets()
        m.search.assert_called_once()

    @patch(f"{MODULE}.TraitDatasetsViewModel")
    def test_get_associated_datasets_empty(self, m):
        m.search.return_value = []
        t = Trait(id=uuid4(), trait_name="X", trait_units="u")
        assert t.get_associated_datasets() is None
