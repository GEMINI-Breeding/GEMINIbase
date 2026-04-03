"""Tests for gemini.api.season module - Season class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date

from gemini.api.season import Season

MODULE = "gemini.api.season"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "season_name": "Summer 2024",
        "season_start_date": date(2024, 6, 1),
        "season_end_date": date(2024, 8, 31),
        "season_info": {"desc": "summer"},
        "experiment_id": uuid4(),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSeasonExists:
    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Season.exists(season_name="Summer", experiment_name="Exp") is True

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Season.exists(season_name="X", experiment_name="Y") is False

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Season.exists(season_name="X", experiment_name="Y") is False


class TestSeasonCreate:
    @patch(f"{MODULE}.SeasonModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Season.create(season_name="Summer 2024")
        assert result is not None

    @patch(f"{MODULE}.SeasonModel")
    def test_with_experiment(self, m):
        m.get_or_create.return_value = _make_db()
        with patch.object(Season, "associate_experiment", return_value=MagicMock()):
            result = Season.create(season_name="Summer 2024", experiment_name="Exp1")
            assert result is not None

    @patch(f"{MODULE}.SeasonModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Season.create(season_name="X") is None


class TestSeasonGet:
    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Season.get(season_name="Summer") is not None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Season.get(season_name="Missing") is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Season.get(season_name="X") is None


class TestSeasonGetById:
    @patch(f"{MODULE}.SeasonModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Season.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.SeasonModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Season.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.SeasonModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        assert Season.get_by_id(uuid4()) is None


class TestSeasonGetAll:
    @patch(f"{MODULE}.SeasonModel")
    def test_list(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        assert len(Season.get_all()) == 2

    @patch(f"{MODULE}.SeasonModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Season.get_all() is None

    @patch(f"{MODULE}.SeasonModel")
    def test_exception(self, m):
        m.all.side_effect = Exception("err")
        assert Season.get_all() is None


class TestSeasonSearch:
    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Season.search(season_name="Summer")) == 1

    def test_no_params(self):
        assert Season.search() is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Season.search(season_name="X") is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_exception(self, m):
        m.search.side_effect = Exception("err")
        assert Season.search(season_name="X") is None


class TestSeasonUpdate:
    @patch(f"{MODULE}.SeasonModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, season_name="Updated")
        s = Season(id=uid, season_name="Old", season_start_date=date.today(), season_end_date=date.today())
        assert s.update(season_name="Updated") is not None

    @patch(f"{MODULE}.SeasonModel")
    def test_no_params(self, m):
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.update() is None

    @patch(f"{MODULE}.SeasonModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.update(season_name="New") is None


class TestSeasonDelete:
    @patch(f"{MODULE}.SeasonModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.delete() is True

    @patch(f"{MODULE}.SeasonModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.delete() is False

    @patch(f"{MODULE}.SeasonModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.delete() is False


class TestSeasonRefresh:
    @patch(f"{MODULE}.SeasonModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        s = Season(id=uid, season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.refresh() is s

    @patch(f"{MODULE}.SeasonModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.refresh() is s

    @patch(f"{MODULE}.SeasonModel")
    def test_exception(self, m):
        m.get.side_effect = Exception("err")
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.refresh() is None


class TestSeasonGetSetInfo:
    @patch(f"{MODULE}.SeasonModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(season_info={"k": "v"})
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.get_info() == {"k": "v"}

    @patch(f"{MODULE}.SeasonModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(season_info=None)
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.get_info() is None

    @patch(f"{MODULE}.SeasonModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, season_info={"new": "v"})
        s = Season(id=uid, season_name="X", season_start_date=date.today(), season_end_date=date.today())
        assert s.set_info({"new": "v"}) is not None


class TestSeasonAssociations:
    def test_get_associated_experiment_no_id(self):
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today(), experiment_id=None)
        assert s.get_associated_experiment() is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    @patch(f"{MODULE}.SeasonModel")
    def test_associate_experiment(self, m_season, m_view):
        m_view.exists.return_value = False
        m_season.get.return_value = _make_db()
        m_season.update.return_value = _make_db()
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        with patch(f"{MODULE}.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            result = s.associate_experiment("Exp1")

    def test_unassociate_experiment_no_id(self):
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today(), experiment_id=None)
        assert s.unassociate_experiment() is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_belongs_to_experiment(self, m_view):
        m_view.exists.return_value = True
        s = Season(id=uuid4(), season_name="X", season_start_date=date.today(), season_end_date=date.today())
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert s.belongs_to_experiment("Exp1") is True
