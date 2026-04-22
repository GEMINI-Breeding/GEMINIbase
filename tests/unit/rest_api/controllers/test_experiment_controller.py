"""Tests for the Experiment controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    ExperimentOutput, SeasonOutput, SiteOutput, PopulationOutput,
    SensorPlatformOutput, TraitOutput, SensorOutput, ScriptOutput,
    ProcedureOutput, ModelOutput, DatasetOutput
)


EXP_API_PATH = "gemini.rest_api.controllers.experiment.Experiment"


@pytest.fixture
def mock_exp_output():
    return {
        "id": "exp-uuid",
        "experiment_name": "Experiment A",
        "experiment_info": {},
        "experiment_start_date": None,
        "experiment_end_date": None,
    }


class TestGetAllExperiments:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client, mock_exp_output):
        mock_cls.get_all.return_value = [ExperimentOutput(**mock_exp_output)]
        response = test_client.get("/api/experiments/all")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/experiments/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/all")
        assert response.status_code == 500


class TestGetExperiments:

    @patch(EXP_API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_exp_output):
        mock_cls.search.return_value = [ExperimentOutput(**mock_exp_output)]
        response = test_client.get("/api/experiments", params={"experiment_name": "Exp A"})
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/experiments", params={"experiment_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments", params={"experiment_name": "Exp A"})
        assert response.status_code == 500


class TestGetExperimentById:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client, mock_exp_output):
        mock_cls.get_by_id.return_value = ExperimentOutput(**mock_exp_output)
        response = test_client.get("/api/experiments/id/exp-uuid")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid")
        assert response.status_code == 500


class TestCreateExperiment:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client, mock_exp_output):
        mock_cls.create.return_value = ExperimentOutput(**mock_exp_output)
        response = test_client.post("/api/experiments", json={
            "experiment_name": "Experiment A",
        })
        assert response.status_code == 201

    @patch(EXP_API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/experiments", json={
            "experiment_name": "Experiment A",
        })
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.create.side_effect = Exception("DB error")
        response = test_client.post("/api/experiments", json={
            "experiment_name": "Experiment A",
        })
        assert response.status_code == 500


class TestUpdateExperiment:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client, mock_exp_output):
        mock_exp = MagicMock()
        mock_exp.update.return_value = ExperimentOutput(**mock_exp_output)
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.patch("/api/experiments/id/exp-uuid", json={
            "experiment_name": "Updated",
        })
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/experiments/id/missing", json={
            "experiment_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteExperiment:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.delete("/api/experiments/id/exp-uuid")
        assert response.status_code in (200, 204)

    @patch(EXP_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/experiments/id/missing")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/experiments/id/exp-uuid")
        assert response.status_code == 500


class TestExperimentAssociations:

    @patch(EXP_API_PATH)
    def test_get_seasons_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_seasons.return_value = [SeasonOutput(
            id="s1", season_name="Season 1", season_info={},
            season_start_date=None, season_end_date=None, experiment_id="exp-uuid"
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/seasons")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_seasons_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/seasons")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_sites_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sites.return_value = [SiteOutput(
            id="s1", site_name="Site A", site_city="Davis",
            site_state="CA", site_country="US", site_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sites")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_populations_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_populations.return_value = [PopulationOutput(
            id="c1", population_name="Pop A", population_type="diversity_panel",
            species="Zea mays", population_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/populations")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_sensor_platforms_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sensor_platforms.return_value = [SensorPlatformOutput(
            id="sp1", sensor_platform_name="Platform A", sensor_platform_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sensor_platforms")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_traits_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_traits.return_value = [TraitOutput(
            id="t1", trait_name="Trait A", trait_units="cm",
            trait_level_id=1, trait_metrics={}, trait_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/traits")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_sensors_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sensors.return_value = [SensorOutput(
            id="s1", sensor_name="Sensor A", sensor_type_id=1,
            sensor_data_type_id=1, sensor_data_format_id=1, sensor_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sensors")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_scripts_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_scripts.return_value = [ScriptOutput(
            id="sc1", script_name="Script A", script_url=None,
            script_extension=".py", script_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/scripts")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_procedures_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_procedures.return_value = [ProcedureOutput(
            id="p1", procedure_name="Proc A", procedure_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/procedures")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_models_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_models.return_value = [ModelOutput(
            id="m1", model_name="Model A", model_url=None, model_info={}
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/models")
        assert response.status_code == 200

    @patch(EXP_API_PATH)
    def test_get_datasets_success(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_datasets.return_value = [DatasetOutput(
            id="d1", dataset_name="DS A", collection_date=None,
            dataset_info={}, dataset_type_id=0
        )]
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/datasets")
        assert response.status_code == 200

    # --- Not-found and no-data tests for association endpoints ---

    @patch(EXP_API_PATH)
    def test_get_seasons_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_seasons.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/seasons")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_seasons_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/seasons")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_sites_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/sites")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_sites_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sites.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sites")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_sites_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/sites")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_populations_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/populations")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_populations_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_populations.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/populations")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_populations_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/populations")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_sensor_platforms_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/sensor_platforms")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_sensor_platforms_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sensor_platforms.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sensor_platforms")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_sensor_platforms_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/sensor_platforms")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_traits_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/traits")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_traits_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_traits.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/traits")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_traits_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/traits")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_sensors_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/sensors")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_sensors_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_sensors.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/sensors")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_sensors_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/sensors")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_scripts_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/scripts")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_scripts_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_scripts.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/scripts")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_scripts_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/scripts")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_procedures_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/procedures")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_procedures_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_procedures.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/procedures")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_procedures_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/procedures")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_models_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/models")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_models_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_models.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/models")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_models_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/models")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_get_datasets_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/datasets")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_get_datasets_no_data(self, mock_cls, test_client):
        mock_exp = MagicMock()
        mock_exp.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/datasets")
        assert response.status_code == 200
        assert response.json() == []

    @patch(EXP_API_PATH)
    def test_get_datasets_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/datasets")
        assert response.status_code == 500


class TestGetExperimentHierarchy:

    @patch(EXP_API_PATH)
    def test_success(self, mock_cls, test_client, mock_exp_output):
        mock_exp = MagicMock()
        mock_exp.__iter__ = MagicMock(return_value=iter(mock_exp_output.items()))
        mock_exp.id = mock_exp_output["id"]
        mock_exp.experiment_name = mock_exp_output["experiment_name"]
        mock_exp.experiment_info = mock_exp_output["experiment_info"]
        mock_exp.experiment_start_date = mock_exp_output["experiment_start_date"]
        mock_exp.experiment_end_date = mock_exp_output["experiment_end_date"]
        mock_exp.get_associated_seasons.return_value = []
        mock_exp.get_associated_sites.return_value = []
        mock_exp.get_associated_populations.return_value = []
        mock_exp.get_associated_sensor_platforms.return_value = []
        mock_exp.get_associated_sensors.return_value = []
        mock_exp.get_associated_datasets.return_value = []
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/hierarchy")
        assert response.status_code == 200
        data = response.json()
        assert "experiment" in data
        assert "seasons" in data
        assert "sites" in data
        assert "populations" in data
        assert "sensor_platforms" in data
        assert "sensors" in data
        assert "datasets" in data
        assert isinstance(data["seasons"], list)

    @patch(EXP_API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/experiments/id/missing/hierarchy")
        assert response.status_code == 404

    @patch(EXP_API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/experiments/id/exp-uuid/hierarchy")
        assert response.status_code == 500

    @patch(EXP_API_PATH)
    def test_null_associations_default_to_empty_lists(self, mock_cls, test_client, mock_exp_output):
        mock_exp = MagicMock()
        mock_exp.id = mock_exp_output["id"]
        mock_exp.experiment_name = mock_exp_output["experiment_name"]
        mock_exp.experiment_info = mock_exp_output["experiment_info"]
        mock_exp.experiment_start_date = mock_exp_output["experiment_start_date"]
        mock_exp.experiment_end_date = mock_exp_output["experiment_end_date"]
        mock_exp.get_associated_seasons.return_value = None
        mock_exp.get_associated_sites.return_value = None
        mock_exp.get_associated_populations.return_value = None
        mock_exp.get_associated_sensor_platforms.return_value = None
        mock_exp.get_associated_sensors.return_value = None
        mock_exp.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_exp
        response = test_client.get("/api/experiments/id/exp-uuid/hierarchy")
        assert response.status_code == 200
        data = response.json()
        assert data["seasons"] == []
        assert data["sites"] == []
        assert data["populations"] == []
