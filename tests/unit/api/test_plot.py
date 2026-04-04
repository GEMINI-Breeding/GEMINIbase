"""Tests for gemini.api.plot module - Plot class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.plot import Plot

MODULE = "gemini.api.plot"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "plot_number": 1,
        "plot_row_number": 1,
        "plot_column_number": 1,
        "plot_geometry_info": None,
        "plot_info": {"key": "val"},
        "experiment_id": uuid4(),
        "season_id": uuid4(),
        "site_id": uuid4(),
        "experiment_name": "Exp1",
        "season_name": "Summer",
        "site_name": "Site1",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestPlotExists:
    @patch(f"{MODULE}.PlotViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Plot.exists(plot_number=1, plot_row_number=1, plot_column_number=1) is True

    @patch(f"{MODULE}.PlotViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Plot.exists(plot_number=99, plot_row_number=99, plot_column_number=99) is False

    @patch(f"{MODULE}.PlotViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Plot.exists(plot_number=1, plot_row_number=1, plot_column_number=1) is False


class TestPlotCreate:
    @patch(f"{MODULE}.PlotModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Plot.create(plot_number=1, plot_row_number=1, plot_column_number=1)
        assert result is not None

    @patch(f"{MODULE}.PlotModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Plot.create(plot_number=1, plot_row_number=1, plot_column_number=1) is None


class TestPlotGet:
    @patch(f"{MODULE}.PlotViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Plot.get(plot_number=1, plot_row_number=1, plot_column_number=1)
        assert result is not None

    @patch(f"{MODULE}.PlotViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Plot.get(plot_number=99, plot_row_number=99, plot_column_number=99) is None

    @patch(f"{MODULE}.PlotViewModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Plot.get(plot_number=1, plot_row_number=1, plot_column_number=1) is None


class TestPlotGetById:
    @patch(f"{MODULE}.PlotViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Plot.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.PlotViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Plot.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.PlotViewModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Plot.get_by_id(uuid4()) is None


class TestPlotGetAll:
    @patch(f"{MODULE}.PlotModel")
    def test_list(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        assert len(Plot.get_all()) == 2

    @patch(f"{MODULE}.PlotModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Plot.get_all() is None

    @patch(f"{MODULE}.PlotModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert Plot.get_all() is None


class TestPlotSearch:
    @patch(f"{MODULE}.PlotViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        result = Plot.search(plot_number=1)
        assert result is not None

    @patch(f"{MODULE}.PlotViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Plot.search(plot_number=99) is None

    @patch(f"{MODULE}.PlotViewModel")
    def test_exception(self, m):
        m.search.side_effect = Exception("err")
        assert Plot.search(plot_number=1) is None


class TestPlotUpdate:
    @patch(f"{MODULE}.PlotModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        p = Plot(id=uid, plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.update(plot_info={"new": "val"}) is not None

    @patch(f"{MODULE}.PlotModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.update(plot_info={"new": "val"}) is None


class TestPlotDelete:
    @patch(f"{MODULE}.PlotModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.delete() is True

    @patch(f"{MODULE}.PlotModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.delete() is False

    @patch(f"{MODULE}.PlotModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.delete() is False


class TestPlotRefresh:
    @patch(f"{MODULE}.PlotViewModel")
    def test_success(self, m):
        uid = uuid4()
        m.get_by_parameters.return_value = _make_db(id=uid)
        p = Plot(id=uid, plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.refresh() is p

    @patch(f"{MODULE}.PlotViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.refresh() is p

    @patch(f"{MODULE}.PlotViewModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.refresh() is None


class TestPlotGetSetInfo:
    @patch(f"{MODULE}.PlotModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(plot_info={"k": "v"})
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.get_info() == {"k": "v"}

    @patch(f"{MODULE}.PlotModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(plot_info=None)
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.get_info() is None

    @patch(f"{MODULE}.PlotModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, plot_info={"new": "v"})
        p = Plot(id=uid, plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.set_info({"new": "v"}) is not None


class TestPlotAssociations:
    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_get_associated_populations(self, m):
        m.search.return_value = [MagicMock()]
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        result = p.get_associated_populations()
        m.search.assert_called_once()

    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_get_associated_populations_empty(self, m):
        m.search.return_value = []
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.get_associated_populations() is None

    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_get_associated_populations_exception(self, m):
        m.search.side_effect = Exception("err")
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        assert p.get_associated_populations() is None

    # --- Experiment associations ---
    def test_get_associated_experiment_success(self):
        exp_id = uuid4()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=exp_id)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get_by_id.return_value = MagicMock()
            result = p.get_associated_experiment()
            assert result is not None

    def test_get_associated_experiment_no_id(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=None)
        assert p.get_associated_experiment() is None

    def test_get_associated_experiment_not_found(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=uuid4())
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get_by_id.return_value = None
            assert p.get_associated_experiment() is None

    def test_get_associated_experiment_exception(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=uuid4())
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get_by_id.side_effect = Exception("err")
            assert p.get_associated_experiment() is None

    @patch(f"{MODULE}.PlotViewModel")
    def test_belongs_to_experiment_true(self, m_view):
        m_view.exists.return_value = True
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert p.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.PlotViewModel")
    def test_belongs_to_experiment_exp_not_found(self, m_view):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = None
            assert p.belongs_to_experiment("Missing") is False

    @patch(f"{MODULE}.PlotModel")
    @patch(f"{MODULE}.PlotViewModel")
    def test_associate_experiment_success(self, m_view, m_model):
        m_view.get_by_parameters.return_value = None
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(p, "refresh"):
                result = p.associate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.PlotViewModel")
    def test_associate_experiment_already_associated(self, m_view):
        m_view.get_by_parameters.return_value = MagicMock()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            result = p.associate_experiment("Exp1")
            assert result is p

    def test_associate_experiment_not_found(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = None
            assert p.associate_experiment("Missing") is None

    @patch(f"{MODULE}.PlotModel")
    def test_unassociate_experiment_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        exp_id = uuid4()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=exp_id)
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get_by_id.return_value = MagicMock()
            with patch.object(p, "refresh"):
                result = p.unassociate_experiment()
                assert result is not None

    def test_unassociate_experiment_no_exp(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, experiment_id=None)
        assert p.unassociate_experiment() is None

    # --- Season associations ---
    def test_get_associated_season_success(self):
        season_id = uuid4()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, season_id=season_id)
        with patch("gemini.api.season.Season") as mock_season:
            mock_season.get_by_id.return_value = MagicMock()
            result = p.get_associated_season()
            assert result is not None

    def test_get_associated_season_no_id(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, season_id=None)
        assert p.get_associated_season() is None

    # --- Site associations ---
    def test_get_associated_site_success(self):
        site_id = uuid4()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, site_id=site_id)
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.get_by_id.return_value = MagicMock()
            result = p.get_associated_site()
            assert result is not None

    def test_get_associated_site_no_id(self):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1, site_id=None)
        assert p.get_associated_site() is None

    # --- Population associate/unassociate ---
    @patch(f"{MODULE}.PlotPopulationModel")
    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_associate_population_success(self, m_view, m_assoc):
        m_view.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = MagicMock(id=uuid4())
            with patch.object(Plot, "refresh"):
                result = p.associate_population("Pop1", "Acc1")
                assert result is not None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_associate_population_not_found(self, m_assoc):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert p.associate_population("Pop1", "Acc1") is None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_unassociate_population_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = MagicMock(id=uuid4())
            with patch.object(Plot, "refresh"):
                result = p.unassociate_population("Pop1", "Acc1")
                assert result is not None

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_unassociate_population_not_found(self, m_assoc):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert p.unassociate_population("Pop1", "Acc1") is None

    @patch(f"{MODULE}.PlotPopulationViewModel")
    def test_belongs_to_population_true(self, m_view):
        m_view.exists.return_value = True
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = MagicMock(id=uuid4())
            assert p.belongs_to_population("Pop1", "Acc1") is True

    @patch(f"{MODULE}.PlotPopulationModel")
    def test_belongs_to_population_cult_not_found(self, m_assoc):
        p = Plot(id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert p.belongs_to_population("Pop1", "Acc1") is False
