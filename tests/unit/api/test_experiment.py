"""Tests for gemini.api.experiment module - Experiment class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date

from gemini.api.experiment import Experiment


MODULE = "gemini.api.experiment"


def _make_exp_db(**overrides):
    defaults = {
        "id": uuid4(),
        "experiment_name": "Test Experiment",
        "experiment_info": {"desc": "test"},
        "experiment_start_date": date(2024, 1, 1),
        "experiment_end_date": date(2024, 12, 31),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestExperimentExists:
    @patch(f"{MODULE}.ExperimentModel")
    def test_exists_true(self, mock_model):
        mock_model.exists.return_value = True
        assert Experiment.exists(experiment_name="Test") is True

    @patch(f"{MODULE}.ExperimentModel")
    def test_exists_false(self, mock_model):
        mock_model.exists.return_value = False
        assert Experiment.exists(experiment_name="Missing") is False

    @patch(f"{MODULE}.ExperimentModel")
    def test_exists_exception(self, mock_model):
        mock_model.exists.side_effect = Exception("err")
        assert Experiment.exists(experiment_name="Test") is False


class TestExperimentCreate:
    @patch(f"{MODULE}.ExperimentModel")
    def test_create_success(self, mock_model):
        mock_model.get_or_create.return_value = _make_exp_db()
        exp = Experiment.create(experiment_name="Test")
        assert exp is not None
        assert exp.experiment_name == "Test Experiment"

    @patch(f"{MODULE}.ExperimentModel")
    def test_create_exception(self, mock_model):
        mock_model.get_or_create.side_effect = Exception("err")
        result = Experiment.create(experiment_name="Test")
        assert result is None


class TestExperimentGet:
    @patch(f"{MODULE}.ExperimentModel")
    def test_get_found(self, mock_model):
        mock_model.get_by_parameters.return_value = _make_exp_db()
        exp = Experiment.get(experiment_name="Test")
        assert exp is not None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_not_found(self, mock_model):
        mock_model.get_by_parameters.return_value = None
        assert Experiment.get(experiment_name="Missing") is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_exception(self, mock_model):
        mock_model.get_by_parameters.side_effect = Exception("err")
        assert Experiment.get(experiment_name="Test") is None


class TestExperimentGetById:
    @patch(f"{MODULE}.ExperimentModel")
    def test_get_by_id_found(self, mock_model):
        uid = uuid4()
        mock_model.get.return_value = _make_exp_db(id=uid)
        exp = Experiment.get_by_id(uid)
        assert exp is not None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_by_id_not_found(self, mock_model):
        mock_model.get.return_value = None
        assert Experiment.get_by_id(uuid4()) is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_by_id_exception(self, mock_model):
        mock_model.get.side_effect = Exception("err")
        assert Experiment.get_by_id(uuid4()) is None


class TestExperimentGetAll:
    @patch(f"{MODULE}.ExperimentModel")
    def test_get_all_returns_list(self, mock_model):
        mock_model.all.return_value = [_make_exp_db(), _make_exp_db()]
        result = Experiment.get_all()
        assert result is not None
        assert len(result) == 2

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_all_empty(self, mock_model):
        mock_model.all.return_value = []
        assert Experiment.get_all() is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_all_exception(self, mock_model):
        mock_model.all.side_effect = Exception("err")
        assert Experiment.get_all() is None


class TestExperimentSearch:
    @patch(f"{MODULE}.ExperimentModel")
    def test_search_results(self, mock_model):
        mock_model.search.return_value = [_make_exp_db()]
        result = Experiment.search(experiment_name="Test")
        assert result is not None
        assert len(result) == 1

    def test_search_no_params(self):
        assert Experiment.search() is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_search_empty(self, mock_model):
        mock_model.search.return_value = []
        assert Experiment.search(experiment_name="Missing") is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_search_exception(self, mock_model):
        mock_model.search.side_effect = Exception("err")
        assert Experiment.search(experiment_name="Test") is None


class TestExperimentUpdate:
    @patch(f"{MODULE}.ExperimentModel")
    def test_update_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_exp_db(id=uid)
        mock_model.get.return_value = db_inst
        mock_model.update.return_value = _make_exp_db(id=uid, experiment_name="Updated")
        exp = Experiment(id=uid, experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        result = exp.update(experiment_name="Updated")
        assert result is not None

    @patch(f"{MODULE}.ExperimentModel")
    def test_update_no_params(self, mock_model):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.update() is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_update_not_found(self, mock_model):
        mock_model.get.return_value = None
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.update(experiment_name="New") is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_update_exception(self, mock_model):
        mock_model.get.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.update(experiment_name="New") is None


class TestExperimentDelete:
    @patch(f"{MODULE}.ExperimentModel")
    def test_delete_success(self, mock_model):
        uid = uuid4()
        mock_model.get.return_value = _make_exp_db(id=uid)
        exp = Experiment(id=uid, experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.delete() is True

    @patch(f"{MODULE}.ExperimentModel")
    def test_delete_not_found(self, mock_model):
        mock_model.get.return_value = None
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.delete() is False

    @patch(f"{MODULE}.ExperimentModel")
    def test_delete_exception(self, mock_model):
        mock_model.get.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.delete() is False


class TestExperimentRefresh:
    @patch(f"{MODULE}.ExperimentModel")
    def test_refresh_success(self, mock_model):
        uid = uuid4()
        mock_model.get.return_value = _make_exp_db(id=uid, experiment_name="Refreshed")
        exp = Experiment(id=uid, experiment_name="Old", experiment_start_date=date.today(), experiment_end_date=date.today())
        result = exp.refresh()
        assert result is exp

    @patch(f"{MODULE}.ExperimentModel")
    def test_refresh_not_found(self, mock_model):
        mock_model.get.return_value = None
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        result = exp.refresh()
        assert result is exp

    @patch(f"{MODULE}.ExperimentModel")
    def test_refresh_exception(self, mock_model):
        mock_model.get.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.refresh() is None


class TestExperimentGetSetInfo:
    @patch(f"{MODULE}.ExperimentModel")
    def test_get_info_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_exp_db(id=uid, experiment_info={"key": "val"})
        mock_model.get.return_value = db_inst
        exp = Experiment(id=uid, experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_info() == {"key": "val"}

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_info_not_found(self, mock_model):
        mock_model.get.return_value = None
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_info() is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_get_info_empty(self, mock_model):
        mock_model.get.return_value = _make_exp_db(experiment_info=None)
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_info() is None

    @patch(f"{MODULE}.ExperimentModel")
    def test_set_info_success(self, mock_model):
        uid = uuid4()
        mock_model.get.return_value = _make_exp_db(id=uid)
        mock_model.update.return_value = _make_exp_db(id=uid, experiment_info={"new": "info"})
        exp = Experiment(id=uid, experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        result = exp.set_info({"new": "info"})
        assert result is not None

    @patch(f"{MODULE}.ExperimentModel")
    def test_set_info_not_found(self, mock_model):
        mock_model.get.return_value = None
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.set_info({"new": "info"}) is None


class TestExperimentAssociations:
    # --- Seasons ---
    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_get_associated_seasons_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Season", create=True):
            result = exp.get_associated_seasons()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_get_associated_seasons_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_seasons() is None

    @patch(f"{MODULE}.ExperimentSeasonsViewModel")
    def test_get_associated_seasons_exception(self, mock_view):
        mock_view.search.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_seasons() is None

    def test_create_new_season_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.season.Season") as mock_season:
            mock_season.create.return_value = MagicMock()
            result = exp.create_new_season("Spring")
            assert result is not None

    def test_create_new_season_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.season.Season") as mock_season:
            mock_season.create.return_value = None
            assert exp.create_new_season("Spring") is None

    def test_create_new_season_exception(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.season.Season") as mock_season:
            mock_season.create.side_effect = Exception("err")
            assert exp.create_new_season("Spring") is None

    # --- Populations ---
    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_associated_populations_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Population", create=True):
            result = exp.get_associated_populations()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_associated_populations_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_populations() is None

    @patch(f"{MODULE}.ExperimentPopulationsViewModel")
    def test_get_associated_populations_exception(self, mock_view):
        mock_view.search.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_populations() is None

    def test_create_new_population_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.create.return_value = MagicMock()
            result = exp.create_new_population("Pop1")
            assert result is not None

    def test_create_new_population_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.create.return_value = None
            assert exp.create_new_population("Pop1") is None

    def test_create_new_population_exception(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.create.side_effect = Exception("err")
            assert exp.create_new_population("Pop1") is None

    def test_associate_population_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_obj = MagicMock()
            mock_cult.get.return_value = mock_obj
            result = exp.associate_population("Pop1")
            assert result is mock_obj
            mock_obj.associate_experiment.assert_called_once()

    def test_associate_population_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert exp.associate_population("Pop1") is None

    def test_associate_population_exception(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.side_effect = Exception("err")
            assert exp.associate_population("Pop1") is None

    def test_unassociate_population_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_obj = MagicMock()
            mock_cult.get.return_value = mock_obj
            result = exp.unassociate_population("Pop1")
            assert result is mock_obj
            mock_obj.unassociate_experiment.assert_called_once()

    def test_unassociate_population_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert exp.unassociate_population("Pop1") is None

    def test_belongs_to_population_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_cult.get.return_value = mock_obj
            assert exp.belongs_to_population("Pop1") is True

    def test_belongs_to_population_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.return_value = None
            assert exp.belongs_to_population("Pop1") is False

    def test_belongs_to_population_exception(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.population.Population") as mock_cult:
            mock_cult.get.side_effect = Exception("err")
            assert exp.belongs_to_population("Pop1") is False

    # --- Procedures ---
    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_get_associated_procedures_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Procedure", create=True):
            result = exp.get_associated_procedures()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_get_associated_procedures_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_procedures() is None

    @patch(f"{MODULE}.ExperimentProceduresViewModel")
    def test_get_associated_procedures_exception(self, mock_view):
        mock_view.search.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_procedures() is None

    def test_create_new_procedure_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.create.return_value = MagicMock()
            result = exp.create_new_procedure("Proc1")
            assert result is not None

    def test_create_new_procedure_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.create.return_value = None
            assert exp.create_new_procedure("Proc1") is None

    def test_associate_procedure_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_obj = MagicMock()
            mock_proc.get.return_value = mock_obj
            result = exp.associate_procedure("Proc1")
            assert result is mock_obj

    def test_associate_procedure_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = None
            assert exp.associate_procedure("Proc1") is None

    def test_unassociate_procedure_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_obj = MagicMock()
            mock_proc.get.return_value = mock_obj
            result = exp.unassociate_procedure("Proc1")
            assert result is mock_obj

    def test_unassociate_procedure_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = None
            assert exp.unassociate_procedure("Proc1") is None

    def test_belongs_to_procedure_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_proc.get.return_value = mock_obj
            assert exp.belongs_to_procedure("Proc1") is True

    def test_belongs_to_procedure_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.procedure.Procedure") as mock_proc:
            mock_proc.get.return_value = None
            assert exp.belongs_to_procedure("Proc1") is False

    # --- Scripts ---
    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_get_associated_scripts_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Script", create=True):
            result = exp.get_associated_scripts()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_get_associated_scripts_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_scripts() is None

    @patch(f"{MODULE}.ExperimentScriptsViewModel")
    def test_get_associated_scripts_exception(self, mock_view):
        mock_view.search.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_scripts() is None

    def test_create_new_script_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.create.return_value = MagicMock()
            result = exp.create_new_script("Script1")
            assert result is not None

    def test_create_new_script_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.create.return_value = None
            assert exp.create_new_script("Script1") is None

    def test_associate_script_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_obj = MagicMock()
            mock_scr.get.return_value = mock_obj
            result = exp.associate_script("Script1")
            assert result is mock_obj

    def test_associate_script_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = None
            assert exp.associate_script("Script1") is None

    def test_unassociate_script_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_obj = MagicMock()
            mock_scr.get.return_value = mock_obj
            result = exp.unassociate_script("Script1")
            assert result is mock_obj

    def test_unassociate_script_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = None
            assert exp.unassociate_script("Script1") is None

    def test_belongs_to_script_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_scr.get.return_value = mock_obj
            assert exp.belongs_to_script("Script1") is True

    def test_belongs_to_script_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.script.Script") as mock_scr:
            mock_scr.get.return_value = None
            assert exp.belongs_to_script("Script1") is False

    # --- Models ---
    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_get_associated_models_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Model", create=True):
            result = exp.get_associated_models()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_get_associated_models_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_models() is None

    @patch(f"{MODULE}.ExperimentModelsViewModel")
    def test_get_associated_models_exception(self, mock_view):
        mock_view.search.side_effect = Exception("err")
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_models() is None

    def test_create_new_model_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.create.return_value = MagicMock()
            result = exp.create_new_model("Model1")
            assert result is not None

    def test_create_new_model_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.create.return_value = None
            assert exp.create_new_model("Model1") is None

    def test_associate_model_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_obj = MagicMock()
            mock_mod.get.return_value = mock_obj
            result = exp.associate_model("Model1")
            assert result is mock_obj

    def test_associate_model_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = None
            assert exp.associate_model("Model1") is None

    def test_unassociate_model_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_obj = MagicMock()
            mock_mod.get.return_value = mock_obj
            result = exp.unassociate_model("Model1")
            assert result is mock_obj

    def test_unassociate_model_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = None
            assert exp.unassociate_model("Model1") is None

    def test_belongs_to_model_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_mod.get.return_value = mock_obj
            assert exp.belongs_to_model("Model1") is True

    def test_belongs_to_model_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.model.Model") as mock_mod:
            mock_mod.get.return_value = None
            assert exp.belongs_to_model("Model1") is False

    # --- Sensors ---
    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_get_associated_sensors_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Sensor", create=True):
            result = exp.get_associated_sensors()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_get_associated_sensors_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_sensors() is None

    def test_create_new_sensor_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.create.return_value = MagicMock()
            result = exp.create_new_sensor("Sensor1")
            assert result is not None

    def test_create_new_sensor_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.create.return_value = None
            assert exp.create_new_sensor("Sensor1") is None

    def test_associate_sensor_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_obj = MagicMock()
            mock_sen.get.return_value = mock_obj
            result = exp.associate_sensor("Sensor1")
            assert result is mock_obj

    def test_associate_sensor_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = None
            assert exp.associate_sensor("Sensor1") is None

    def test_unassociate_sensor_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_obj = MagicMock()
            mock_sen.get.return_value = mock_obj
            result = exp.unassociate_sensor("Sensor1")
            assert result is mock_obj

    def test_unassociate_sensor_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = None
            assert exp.unassociate_sensor("Sensor1") is None

    def test_belongs_to_sensor_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_sen.get.return_value = mock_obj
            assert exp.belongs_to_sensor("Sensor1") is True

    def test_belongs_to_sensor_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = None
            assert exp.belongs_to_sensor("Sensor1") is False

    # --- Sensor Platforms ---
    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_get_associated_sensor_platforms_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.SensorPlatform", create=True):
            result = exp.get_associated_sensor_platforms()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_get_associated_sensor_platforms_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_sensor_platforms() is None

    def test_create_new_sensor_platform_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.create.return_value = MagicMock()
            result = exp.create_new_sensor_platform("Platform1")
            assert result is not None

    def test_create_new_sensor_platform_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.create.return_value = None
            assert exp.create_new_sensor_platform("Platform1") is None

    def test_associate_sensor_platform_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_obj = MagicMock()
            mock_sp.get.return_value = mock_obj
            result = exp.associate_sensor_platform("Platform1")
            assert result is mock_obj

    def test_associate_sensor_platform_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = None
            assert exp.associate_sensor_platform("Platform1") is None

    def test_unassociate_sensor_platform_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_obj = MagicMock()
            mock_sp.get.return_value = mock_obj
            result = exp.unassociate_sensor_platform("Platform1")
            assert result is mock_obj

    def test_unassociate_sensor_platform_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = None
            assert exp.unassociate_sensor_platform("Platform1") is None

    def test_belongs_to_sensor_platform_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_sp.get.return_value = mock_obj
            assert exp.belongs_to_sensor_platform("Platform1") is True

    def test_belongs_to_sensor_platform_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = None
            assert exp.belongs_to_sensor_platform("Platform1") is False

    # --- Sites ---
    @patch(f"{MODULE}.ExperimentSitesViewModel")
    def test_get_associated_sites_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Site", create=True):
            result = exp.get_associated_sites()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSitesViewModel")
    def test_get_associated_sites_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_sites() is None

    def test_create_new_site_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.create.return_value = MagicMock()
            result = exp.create_new_site("Site1")
            assert result is not None

    def test_create_new_site_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.create.return_value = None
            assert exp.create_new_site("Site1") is None

    def test_associate_site_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_obj = MagicMock()
            mock_site.get.return_value = mock_obj
            result = exp.associate_site("Site1")
            assert result is mock_obj

    def test_associate_site_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.get.return_value = None
            assert exp.associate_site("Site1") is None

    def test_unassociate_site_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_obj = MagicMock()
            mock_site.get.return_value = mock_obj
            result = exp.unassociate_site("Site1")
            assert result is mock_obj

    def test_unassociate_site_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.get.return_value = None
            assert exp.unassociate_site("Site1") is None

    def test_belongs_to_site_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_site.get.return_value = mock_obj
            assert exp.belongs_to_site("Site1") is True

    def test_belongs_to_site_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.site.Site") as mock_site:
            mock_site.get.return_value = None
            assert exp.belongs_to_site("Site1") is False

    # --- Datasets ---
    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_get_associated_datasets_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Dataset", create=True):
            result = exp.get_associated_datasets()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentDatasetsViewModel")
    def test_get_associated_datasets_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_datasets() is None

    def test_create_new_dataset_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_ds.create.return_value = MagicMock()
            result = exp.create_new_dataset("DS1")
            assert result is not None

    def test_create_new_dataset_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_ds.create.return_value = None
            assert exp.create_new_dataset("DS1") is None

    def test_associate_dataset_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_obj = MagicMock()
            mock_ds.get.return_value = mock_obj
            result = exp.associate_dataset("DS1")
            assert result is mock_obj

    def test_associate_dataset_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_ds.get.return_value = None
            assert exp.associate_dataset("DS1") is None

    def test_unassociate_dataset_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_obj = MagicMock()
            mock_ds.get.return_value = mock_obj
            result = exp.unassociate_dataset("DS1")
            assert result is mock_obj

    def test_unassociate_dataset_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_ds.get.return_value = None
            assert exp.unassociate_dataset("DS1") is None

    def test_belongs_to_dataset_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_ds.get.return_value = mock_obj
            assert exp.belongs_to_dataset("DS1") is True

    def test_belongs_to_dataset_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.dataset.Dataset") as mock_ds:
            mock_ds.get.return_value = None
            assert exp.belongs_to_dataset("DS1") is False

    # --- Traits ---
    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_get_associated_traits_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Trait", create=True):
            result = exp.get_associated_traits()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentTraitsViewModel")
    def test_get_associated_traits_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_traits() is None

    def test_create_new_trait_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_tr.create.return_value = MagicMock()
            result = exp.create_new_trait("Trait1")
            assert result is not None

    def test_create_new_trait_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_tr.create.return_value = None
            assert exp.create_new_trait("Trait1") is None

    def test_associate_trait_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_obj = MagicMock()
            mock_tr.get.return_value = mock_obj
            result = exp.associate_trait("Trait1")
            assert result is mock_obj

    def test_associate_trait_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_tr.get.return_value = None
            assert exp.associate_trait("Trait1") is None

    def test_unassociate_trait_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_obj = MagicMock()
            mock_tr.get.return_value = mock_obj
            result = exp.unassociate_trait("Trait1")
            assert result is mock_obj

    def test_unassociate_trait_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_tr.get.return_value = None
            assert exp.unassociate_trait("Trait1") is None

    def test_belongs_to_trait_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_tr.get.return_value = mock_obj
            assert exp.belongs_to_trait("Trait1") is True

    def test_belongs_to_trait_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.trait.Trait") as mock_tr:
            mock_tr.get.return_value = None
            assert exp.belongs_to_trait("Trait1") is False

    # --- Plots ---
    @patch(f"{MODULE}.PlotViewModel")
    def test_get_associated_plots_found(self, mock_view):
        mock_view.search.return_value = [MagicMock()]
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch(f"{MODULE}.Plot", create=True):
            result = exp.get_associated_plots()
            mock_view.search.assert_called_once()

    @patch(f"{MODULE}.PlotViewModel")
    def test_get_associated_plots_empty(self, mock_view):
        mock_view.search.return_value = []
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert exp.get_associated_plots() is None

    def test_create_new_plot_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.create.return_value = MagicMock()
            result = exp.create_new_plot(1, 1, 1)
            assert result is not None

    def test_create_new_plot_failure(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.create.return_value = None
            assert exp.create_new_plot(1, 1, 1) is None

    def test_associate_plot_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_obj = MagicMock()
            mock_plot.get.return_value = mock_obj
            result = exp.associate_plot(1, 1, 1)
            assert result is mock_obj

    def test_associate_plot_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get.return_value = None
            assert exp.associate_plot(1, 1, 1) is None

    def test_unassociate_plot_success(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_obj = MagicMock()
            mock_plot.get.return_value = mock_obj
            result = exp.unassociate_plot(1, 1, 1)
            assert result is mock_obj

    def test_unassociate_plot_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get.return_value = None
            assert exp.unassociate_plot(1, 1, 1) is None

    def test_belongs_to_plot_true(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_obj = MagicMock()
            mock_obj.belongs_to_experiment.return_value = True
            mock_plot.get.return_value = mock_obj
            assert exp.belongs_to_plot(1, 1, 1) is True

    def test_belongs_to_plot_not_found(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        with patch("gemini.api.plot.Plot") as mock_plot:
            mock_plot.get.return_value = None
            assert exp.belongs_to_plot(1, 1, 1) is False


class TestExperimentStringRepresentation:
    def test_str(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert "Test" in str(exp)

    def test_repr(self):
        exp = Experiment(id=uuid4(), experiment_name="Test", experiment_start_date=date.today(), experiment_end_date=date.today())
        assert "Test" in repr(exp)
