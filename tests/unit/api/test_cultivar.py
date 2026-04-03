"""Tests for gemini.api.cultivar module - Cultivar class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.cultivar import Cultivar

MODULE = "gemini.api.cultivar"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "cultivar_population": "Wheat",
        "cultivar_accession": "ACC123",
        "cultivar_info": {"key": "val"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestCultivarExists:
    @patch(f"{MODULE}.CultivarModel")
    def test_exists_true(self, m):
        m.exists.return_value = True
        assert Cultivar.exists(cultivar_population="Wheat", cultivar_accession="ACC123") is True

    @patch(f"{MODULE}.CultivarModel")
    def test_exists_false(self, m):
        m.exists.return_value = False
        assert Cultivar.exists(cultivar_population="X", cultivar_accession="Y") is False

    @patch(f"{MODULE}.CultivarModel")
    def test_exists_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Cultivar.exists(cultivar_population="X", cultivar_accession="Y") is False


class TestCultivarCreate:
    @patch(f"{MODULE}.CultivarModel")
    def test_create_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Cultivar.create(cultivar_population="Wheat", cultivar_accession="ACC123")
        assert result is not None
        assert result.cultivar_population == "Wheat"

    @patch(f"{MODULE}.CultivarModel")
    def test_create_with_experiment(self, m):
        m.get_or_create.return_value = _make_db()
        with patch.object(Cultivar, "associate_experiment", return_value=MagicMock()):
            result = Cultivar.create(cultivar_population="Wheat", cultivar_accession="ACC123", experiment_name="Exp1")
            assert result is not None

    @patch(f"{MODULE}.CultivarModel")
    def test_create_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Cultivar.create(cultivar_population="Wheat", cultivar_accession="ACC123") is None


class TestCultivarGet:
    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Cultivar.get(cultivar_population="Wheat", cultivar_accession="ACC123")
        assert result is not None

    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Cultivar.get(cultivar_population="X", cultivar_accession="Y") is None

    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_get_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Cultivar.get(cultivar_population="X", cultivar_accession="Y") is None


class TestCultivarGetById:
    @patch(f"{MODULE}.CultivarModel")
    def test_found(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        assert Cultivar.get_by_id(uid) is not None

    @patch(f"{MODULE}.CultivarModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Cultivar.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.CultivarModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        assert Cultivar.get_by_id(uuid4()) is None


class TestCultivarGetAll:
    @patch(f"{MODULE}.CultivarModel")
    def test_returns_list(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        result = Cultivar.get_all()
        assert len(result) == 2

    @patch(f"{MODULE}.CultivarModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Cultivar.get_all() is None

    @patch(f"{MODULE}.CultivarModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert Cultivar.get_all() is None


class TestCultivarSearch:
    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        result = Cultivar.search(cultivar_population="Wheat")
        assert len(result) == 1

    def test_no_params(self):
        assert Cultivar.search() is None

    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Cultivar.search(cultivar_population="X") is None

    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_exception(self, m):
        m.search.side_effect = Exception("err")
        assert Cultivar.search(cultivar_population="X") is None


class TestCultivarUpdate:
    @patch(f"{MODULE}.CultivarModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, cultivar_accession="NEW")
        c = Cultivar(id=uid, cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.update(cultivar_accession="NEW") is not None

    @patch(f"{MODULE}.CultivarModel")
    def test_no_params(self, m):
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.update() is None

    @patch(f"{MODULE}.CultivarModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.update(cultivar_accession="NEW") is None


class TestCultivarDelete:
    @patch(f"{MODULE}.CultivarModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.delete() is True

    @patch(f"{MODULE}.CultivarModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.delete() is False


class TestCultivarRefresh:
    @patch(f"{MODULE}.CultivarModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid, cultivar_accession="Refreshed")
        c = Cultivar(id=uid, cultivar_population="Wheat", cultivar_accession="Old")
        result = c.refresh()
        assert result is c

    @patch(f"{MODULE}.CultivarModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.refresh() is c

    @patch(f"{MODULE}.CultivarModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.refresh() is None


class TestCultivarGetSetInfo:
    @patch(f"{MODULE}.CultivarModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(cultivar_info={"k": "v"})
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.get_info() == {"k": "v"}

    @patch(f"{MODULE}.CultivarModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(cultivar_info=None)
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.get_info() is None

    @patch(f"{MODULE}.CultivarModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, cultivar_info={"new": "val"})
        c = Cultivar(id=uid, cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.set_info({"new": "val"}) is not None


class TestCultivarAssociations:
    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = c.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentCultivarsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.get_associated_experiments() is None

    @patch(f"{MODULE}.ExperimentCultivarModel")
    def test_associate_experiment(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.associate_experiment("Exp1")

    @patch(f"{MODULE}.ExperimentCultivarModel")
    def test_belongs_to_experiment(self, m_assoc):
        m_assoc.exists.return_value = True
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.PlotCultivarViewModel")
    def test_get_associated_plots(self, m):
        m.search.return_value = [MagicMock()]
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True):
            result = c.get_associated_plots()
            m.search.assert_called_once()

    @patch(f"{MODULE}.PlotCultivarViewModel")
    def test_get_associated_plots_empty(self, m):
        m.search.return_value = []
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.get_associated_plots() is None

    @patch(f"{MODULE}.PlantViewModel")
    def test_get_associated_plants(self, m):
        m.search.return_value = [MagicMock()]
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plant.Plant", create=True):
            result = c.get_associated_plants()
            m.search.assert_called_once()

    @patch(f"{MODULE}.PlantViewModel")
    def test_get_associated_plants_empty(self, m):
        m.search.return_value = []
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.get_associated_plants() is None

    def test_associate_experiment_not_found(self):
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert c.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentCultivarModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentCultivarModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert c.unassociate_experiment("Exp1") is None

    @patch(f"{MODULE}.PlotCultivarModel")
    def test_associate_plot_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.associate_plot(1, 1, 1)
                assert result is not None

    @patch(f"{MODULE}.PlotCultivarModel")
    def test_associate_plot_not_found(self, m_assoc):
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = None
            assert c.associate_plot(1, 1, 1) is None

    @patch(f"{MODULE}.PlotCultivarModel")
    def test_unassociate_plot_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.unassociate_plot(1, 1, 1)
                assert result is not None

    @patch(f"{MODULE}.PlotCultivarModel")
    def test_belongs_to_plot_true(self, m_assoc):
        m_assoc.exists.return_value = True
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_plot(1, 1, 1) is True

    @patch(f"{MODULE}.PlotCultivarModel")
    def test_belongs_to_plot_not_found(self, m_assoc):
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = None
            assert c.belongs_to_plot(1, 1, 1) is False

    @patch(f"{MODULE}.PlantViewModel")
    def test_belongs_to_plant_true(self, m):
        m.exists.return_value = True
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        with patch("gemini.api.plant.Plant") as mock_plant:
            mock_plant.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_plant(1) is True

    @patch(f"{MODULE}.PlantViewModel")
    def test_belongs_to_plant_false(self, m):
        m.exists.return_value = False
        c = Cultivar(id=uuid4(), cultivar_population="Wheat", cultivar_accession="ACC123")
        assert c.belongs_to_plant(99) is False
