"""Tests for the Procedure controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    ProcedureOutput, ExperimentOutput, ProcedureRunOutput,
    DatasetOutput, ProcedureRecordOutput
)


API_PATH = "gemini.rest_api.controllers.procedure.Procedure"
RECORD_PATH = "gemini.rest_api.controllers.procedure.ProcedureRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "proc-uuid",
        "procedure_name": "Procedure A",
        "procedure_info": {},
    }


class TestGetAllProcedures:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [ProcedureOutput(**mock_output)]
        response = test_client.get("/api/procedures/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/procedures/all")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/all")
        assert response.status_code == 500


class TestGetProcedures:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [ProcedureOutput(**mock_output)]
        response = test_client.get("/api/procedures", params={"procedure_name": "Procedure A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/procedures", params={"procedure_name": "Missing"})
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures", params={"procedure_name": "Proc"})
        assert response.status_code == 500


class TestGetProcedureById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = ProcedureOutput(**mock_output)
        response = test_client.get("/api/procedures/id/proc-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/procedures/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/id/proc-uuid")
        assert response.status_code == 500


class TestCreateProcedure:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = ProcedureOutput(**mock_output)
        response = test_client.post("/api/procedures", json={
            "procedure_name": "Procedure A",
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/procedures", json={
            "procedure_name": "Procedure A",
        })
        assert response.status_code == 500


class TestUpdateProcedure:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = ProcedureOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/procedures/id/proc-uuid", json={
            "procedure_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/procedures/id/missing", json={
            "procedure_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteProcedure:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/procedures/id/proc-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/procedures/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/procedures/id/proc-uuid")
        assert response.status_code == 500


class TestProcedureAssociations:

    @patch(API_PATH)
    def test_get_runs(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_runs.return_value = [ProcedureRunOutput(
            id="r1", procedure_name="Proc A", procedure_run_info={}
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/runs")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_datasets(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = [DatasetOutput(
            id="d1", dataset_name="DS", collection_date=None,
            dataset_info={}, dataset_type_id=0
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/datasets")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_association_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/procedures/id/missing/runs")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_runs_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_runs.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/runs")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_runs_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/id/proc-uuid/runs")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_experiments_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/procedures/id/missing/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/experiments")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_experiments_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/id/proc-uuid/experiments")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_datasets_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/procedures/id/missing/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/procedures/id/proc-uuid/datasets")
        assert response.status_code == 200
        assert response.json() == []

    @patch(API_PATH)
    def test_get_datasets_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/id/proc-uuid/datasets")
        assert response.status_code == 500


class TestProcedureRecords:

    @patch(RECORD_PATH)
    def test_get_record_by_id_success(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = ProcedureRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", procedure_id="p1",
            procedure_name="Proc A", procedure_data={}, dataset_id="d1",
            dataset_name="DS", collection_date=None,
            experiment_id=None, experiment_name=None,
            season_id=None, season_name=None,
            site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        response = test_client.get("/api/procedures/records/id/r1")
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_get_record_by_id_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.get("/api/procedures/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_get_record_by_id_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/procedures/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = True
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/procedures/records/id/r1")
        assert response.status_code in (200, 204)

    @patch(RECORD_PATH)
    def test_delete_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.delete("/api/procedures/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_delete_record_fails(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = False
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/procedures/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/procedures/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_update_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.update.return_value = ProcedureRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", procedure_id="p1",
            procedure_name="Proc A", procedure_data={"updated": True}, dataset_id="d1",
            dataset_name="DS", collection_date=None,
            experiment_id=None, experiment_name=None,
            season_id=None, season_name=None,
            site_id=None, site_name=None,
            record_file=None, record_info=None
        )
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.patch("/api/procedures/records/id/r1", json={
            "procedure_data": {"updated": True},
        })
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_update_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.patch("/api/procedures/records/id/missing", json={
            "procedure_data": {},
        })
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_update_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/procedures/records/id/r1", json={
            "procedure_data": {},
        })
        assert response.status_code == 500
