"""Tests for gemini.api.population module - Population class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.population import Population

MODULE = "gemini.api.population"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "population_name": "Wheat",
        "population_accession": "ACC123",
        "population_info": {"key": "val"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestPopulationExists:
    @patch(f"{MODULE}.PopulationModel")
    def test_exists_true(self, m):
        m.exists.return_value = True
        assert Population.exists(population_name="Wheat", population_accession="ACC123") is True

    @patch(f"{MODULE}.PopulationModel")
    def test_exists_false(self, m):
        m.exists.return_value = False
        assert Population.exists(population_name="X", population_accession="Y") is False

    @patch(f"{MODULE}.PopulationModel")
    def test_exists_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Population.exists(population_name="X", population_accession="Y") is False


class TestPopulationCreate:
    @patch(f"{MODULE}.PopulationModel")
    def test_create_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Population.create(population_name="Wheat", population_accession="ACC123")
        assert result is not None
        assert result.population_name == "Wheat"

    @patch(f"{MODULE}.PopulationModel")
    def test_create_with_experiment(self, m):
        m.get_or_create.return_value = _make_db()
        with patch.object(Population, "associate_experiment", return_value=MagicMock()):
            result = Population.create(population_name="Wheat", population_accession="ACC123", experiment_name="Exp1")
            assert result is not None

    @patch(f"{MODULE}.PopulationModel")
    def test_create_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Population.create(population_name="Wheat", population_accession="ACC123") is None


class TestPopulationGet:
    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Population.get(population_name="Wheat", population_accession="ACC123")
        assert result is not None

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Population.get(population_name="X", population_accession="Y") is None

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Population.get(population_name="X", population_accession="Y") is None


class TestPopulationGetById:
    @patch(f"{MODULE}.PopulationModel")
    def test_found(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        assert Population.get_by_id(uid) is not None

    @patch(f"{MODULE}.PopulationModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Population.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.PopulationModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        assert Population.get_by_id(uuid4()) is None


class TestPopulationGetAll:
    @patch(f"{MODULE}.PopulationModel")
    def test_returns_list(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        result = Population.get_all()
        assert len(result) == 2

    @patch(f"{MODULE}.PopulationModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Population.get_all() is None

    @patch(f"{MODULE}.PopulationModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert Population.get_all() is None


class TestPopulationSearch:
    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        result = Population.search(population_name="Wheat")
        assert len(result) == 1

    def test_no_params(self):
        assert Population.search() is None

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Population.search(population_name="X") is None

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_exception(self, m):
        m.search.side_effect = Exception("err")
        assert Population.search(population_name="X") is None


class TestPopulationUpdate:
    @patch(f"{MODULE}.PopulationModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, population_accession="NEW")
        c = Population(id=uid, population_name="Wheat", population_accession="ACC123")
        assert c.update(population_accession="NEW") is not None

    @patch(f"{MODULE}.PopulationModel")
    def test_no_params(self, m):
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.update() is None

    @patch(f"{MODULE}.PopulationModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.update(population_accession="NEW") is None


class TestPopulationDelete:
    @patch(f"{MODULE}.PopulationModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.delete() is True

    @patch(f"{MODULE}.PopulationModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.delete() is False


class TestPopulationRefresh:
    @patch(f"{MODULE}.PopulationModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid, population_accession="Refreshed")
        c = Population(id=uid, population_name="Wheat", population_accession="Old")
        result = c.refresh()
        assert result is c

    @patch(f"{MODULE}.PopulationModel")
    def test_not_found(self, m):
        m.get.return_value = None
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.refresh() is c

    @patch(f"{MODULE}.PopulationModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.refresh() is None


class TestPopulationGetSetInfo:
    @patch(f"{MODULE}.PopulationModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(population_info={"k": "v"})
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.get_info() == {"k": "v"}

    @patch(f"{MODULE}.PopulationModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(population_info=None)
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.get_info() is None

    @patch(f"{MODULE}.PopulationModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, population_info={"new": "val"})
        c = Population(id=uid, population_name="Wheat", population_accession="ACC123")
        assert c.set_info({"new": "val"}) is not None


class TestPopulationAssociations:
    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = c.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.get_associated_experiments() is None

    @patch(f"{MODULE}.ExperimentPopulationModel")
    def test_associate_experiment(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.associate_experiment("Exp1")

    @patch(f"{MODULE}.ExperimentPopulationModel")
    def test_belongs_to_experiment(self, m_assoc):
        m_assoc.exists.return_value = True
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_get_associated_plots(self, m):
        m.search.return_value = [MagicMock()]
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True):
            result = c.get_associated_plots()
            m.search.assert_called_once()

    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_get_associated_plots_empty(self, m):
        m.search.return_value = []
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.get_associated_plots() is None

    @patch(f"{MODULE}.PlantViewModel")
    def test_get_associated_plants(self, m):
        m.search.return_value = [MagicMock()]
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plant.Plant", create=True):
            result = c.get_associated_plants()
            m.search.assert_called_once()

    @patch(f"{MODULE}.PlantViewModel")
    def test_get_associated_plants_empty(self, m):
        m.search.return_value = []
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.get_associated_plants() is None

    def test_associate_experiment_not_found(self):
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert c.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentPopulationModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentPopulationModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert c.unassociate_experiment("Exp1") is None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_associate_plot_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.associate_plot(1, 1, 1)
                assert result is not None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_associate_plot_not_found(self, m_assoc):
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = None
            assert c.associate_plot(1, 1, 1) is None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_unassociate_plot_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            with patch.object(c, "refresh"):
                result = c.unassociate_plot(1, 1, 1)
                assert result is not None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_belongs_to_plot_true(self, m_assoc):
        m_assoc.exists.return_value = True
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_plot(1, 1, 1) is True

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_belongs_to_plot_not_found(self, m_assoc):
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plot.Plot", create=True) as mock_plot:
            mock_plot.get.return_value = None
            assert c.belongs_to_plot(1, 1, 1) is False

    @patch(f"{MODULE}.PlantViewModel")
    def test_belongs_to_plant_true(self, m):
        m.exists.return_value = True
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        with patch("gemini.api.plant.Plant") as mock_plant:
            mock_plant.get.return_value = MagicMock(id=uuid4())
            assert c.belongs_to_plant(1) is True

    @patch(f"{MODULE}.PlantViewModel")
    def test_belongs_to_plant_false(self, m):
        m.exists.return_value = False
        c = Population(id=uuid4(), population_name="Wheat", population_accession="ACC123")
        assert c.belongs_to_plant(99) is False
