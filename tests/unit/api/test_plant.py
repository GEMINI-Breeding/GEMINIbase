"""Tests for gemini.api.plant module - Plant class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.plant import Plant

MODULE = "gemini.api.plant"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "plant_number": 1, "plant_info": {"k": "v"}, "plot_id": uuid4(), "population_id": uuid4()}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestPlantExists:
    @patch(f"{MODULE}.PlantViewModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Plant.exists(plant_number=1) is True

    @patch(f"{MODULE}.PlantViewModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Plant.exists(plant_number=99) is False

    @patch(f"{MODULE}.PlantViewModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Plant.exists(plant_number=1) is False


class TestPlantCreate:
    @patch(f"{MODULE}.PlantModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Plant.create(plant_number=1, plot_number=1, plot_row_number=1, plot_column_number=1)
        assert result is not None

    @patch(f"{MODULE}.PlantModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Plant.create(plant_number=1, plot_number=1, plot_row_number=1, plot_column_number=1) is None


class TestPlantGet:
    @patch(f"{MODULE}.PlantViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Plant.get(plant_number=1) is not None

    @patch(f"{MODULE}.PlantViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Plant.get(plant_number=99) is None


class TestPlantGetById:
    @patch(f"{MODULE}.PlantModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Plant.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.PlantModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Plant.get_by_id(uuid4()) is None


class TestPlantGetAll:
    @patch(f"{MODULE}.PlantModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Plant.get_all()) == 1

    @patch(f"{MODULE}.PlantModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Plant.get_all() is None


class TestPlantSearch:
    @patch(f"{MODULE}.PlantViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        result = Plant.search(plant_number=1)
        assert result is not None

    @patch(f"{MODULE}.PlantViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Plant.search(plant_number=99) is None


class TestPlantUpdate:
    @patch(f"{MODULE}.PlantModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        p = Plant(id=uid, plant_number=1)
        assert p.update(plant_info={"new": "v"}) is not None

    @patch(f"{MODULE}.PlantModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Plant(id=uuid4(), plant_number=1)
        assert p.update(plant_info={"new": "v"}) is None


class TestPlantDelete:
    @patch(f"{MODULE}.PlantModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        p = Plant(id=uuid4(), plant_number=1)
        assert p.delete() is True

    @patch(f"{MODULE}.PlantModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Plant(id=uuid4(), plant_number=1)
        assert p.delete() is False


class TestPlantRefresh:
    @patch(f"{MODULE}.PlantModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        p = Plant(id=uid, plant_number=1)
        assert p.refresh() is p

    @patch(f"{MODULE}.PlantModel")
    def test_not_found(self, m):
        m.get.return_value = None
        p = Plant(id=uuid4(), plant_number=1)
        assert p.refresh() is p


class TestPlantGetSetInfo:
    @patch(f"{MODULE}.PlantModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(plant_info={"k": "v"})
        p = Plant(id=uuid4(), plant_number=1)
        assert p.get_info() == {"k": "v"}

    @patch(f"{MODULE}.PlantModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(plant_info=None)
        p = Plant(id=uuid4(), plant_number=1)
        assert p.get_info() is None

    @patch(f"{MODULE}.PlantModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        p = Plant(id=uid, plant_number=1)
        assert p.set_info({"new": "v"}) is not None


class TestPlantAssociations:
    def test_get_associated_population_success(self):
        cult_id = uuid4()
        p = Plant(id=uuid4(), plant_number=1, population_id=cult_id)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get_by_id.return_value = MagicMock()
            result = p.get_associated_population()
            assert result is not None

    def test_get_associated_population_no_id(self):
        p = Plant(id=uuid4(), plant_number=1, population_id=None)
        assert p.get_associated_population() is None

    def test_get_associated_population_not_found(self):
        p = Plant(id=uuid4(), plant_number=1, population_id=uuid4())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get_by_id.return_value = None
            assert p.get_associated_population() is None

    def test_get_associated_plot_success(self):
        plot_id = uuid4()
        p = Plant(id=uuid4(), plant_number=1, plot_id=plot_id)
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get_by_id.return_value = MagicMock()
            result = p.get_associated_plot()
            assert result is not None

    def test_get_associated_plot_no_id(self):
        p = Plant(id=uuid4(), plant_number=1, plot_id=None)
        assert p.get_associated_plot() is None

    @patch(f"{MODULE}.PlantModel")
    def test_associate_population_success(self, m_model):
        m_model.exists.return_value = False
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = MagicMock(id=uuid4())
            with patch.object(Plant, "refresh"):
                result = p.associate_population("Pop1", "Acc1")
                assert result is not None

    def test_associate_population_not_found(self):
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert p.associate_population("Pop1", "Acc1") is None

    @patch(f"{MODULE}.PlantModel")
    def test_unassociate_population_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        cult_id = uuid4()
        p = Plant(id=uuid4(), plant_number=1, population_id=cult_id)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get_by_id.return_value = MagicMock()
            with patch.object(p, "refresh"):
                result = p.unassociate_population()
                assert result is not None

    def test_unassociate_population_no_id(self):
        p = Plant(id=uuid4(), plant_number=1, population_id=None)
        assert p.unassociate_population() is False

    @patch(f"{MODULE}.PlantModel")
    def test_belongs_to_population_true(self, m):
        m.exists.return_value = True
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = MagicMock(id=uuid4())
            assert p.belongs_to_population("Pop1", "Acc1") is True

    @patch(f"{MODULE}.PlantViewModel")
    def test_belongs_to_population_not_found(self, m):
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert p.belongs_to_population("Pop1", "Acc1") is False

    @patch(f"{MODULE}.PlantModel")
    def test_associate_plot_success(self, m_model):
        m_model.get_by_parameters.return_value = None
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get.return_value = MagicMock(id=uuid4())
            with patch.object(Plant, "refresh"):
                result = p.associate_plot(1, 1, 1)
                assert result is not None

    def test_associate_plot_not_found(self):
        p = Plant(id=uuid4(), plant_number=1)
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get.return_value = None
            assert p.associate_plot(1, 1, 1) is None

    @patch(f"{MODULE}.PlantModel")
    def test_unassociate_plot_success(self, m_model):
        m_model.get.return_value = MagicMock()
        m_model.update_parameter.return_value = MagicMock()
        p = Plant(id=uuid4(), plant_number=1, plot_id=uuid4())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get_by_id.return_value = MagicMock()
            with patch.object(p, "refresh"):
                result = p.unassociate_plot()
                assert result is not None

    def test_unassociate_plot_no_id(self):
        p = Plant(id=uuid4(), plant_number=1, plot_id=None)
        assert p.unassociate_plot() is None
