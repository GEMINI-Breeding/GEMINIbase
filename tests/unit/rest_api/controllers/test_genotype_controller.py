"""Unit tests for the GenotypeController."""

import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import GenotypeOutput, GenotypeRecordOutput, ExperimentOutput

API_PATH = "gemini.rest_api.controllers.genotype.Genotype"
RECORD_API_PATH = "gemini.rest_api.controllers.genotype.GenotypeRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "genotype-uuid",
        "genotype_name": "Cowpea_MAGIC_GBS",
        "genotype_info": {"platform": "GBS"},
    }


@pytest.fixture
def mock_record_output():
    return {
        "id": "record-uuid",
        "genotype_id": "genotype-uuid",
        "genotype_name": "Cowpea_MAGIC_GBS",
        "variant_id": "variant-uuid",
        "variant_name": "2_24641",
        "chromosome": 1,
        "position": 0.0,
        "population_id": "pop-uuid",
        "population_name": "IT89KD-288",
        "population_accession": "IT89KD-288",
        "call_value": "TT",
        "record_info": {},
    }


class TestGetAllGenotypes:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [GenotypeOutput(**mock_output)]
        response = test_client.get("/api/genotypes/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_empty(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/genotypes/all")
        assert response.status_code == 404


class TestGetGenotypes:
    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [GenotypeOutput(**mock_output)]
        response = test_client.get("/api/genotypes/?genotype_name=Cowpea_MAGIC_GBS")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_empty(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/genotypes/?genotype_name=nonexistent")
        assert response.status_code == 404


class TestGetGenotypeById:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = GenotypeOutput(**mock_output)
        response = test_client.get("/api/genotypes/id/genotype-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/genotypes/id/nonexistent")
        assert response.status_code == 404


class TestCreateGenotype:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = GenotypeOutput(**mock_output)
        response = test_client.post("/api/genotypes/", json={
            "genotype_name": "Cowpea_MAGIC_GBS"
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_failure(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/genotypes/", json={
            "genotype_name": "test"
        })
        assert response.status_code == 500


class TestUpdateGenotype:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = GenotypeOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/genotypes/id/genotype-uuid", json={
            "genotype_name": "Updated"
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/genotypes/id/nonexistent", json={
            "genotype_name": "Updated"
        })
        assert response.status_code == 404


class TestDeleteGenotype:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/genotypes/id/genotype-uuid")
        assert response.status_code == 200 or response.status_code == 204

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/genotypes/id/nonexistent")
        assert response.status_code == 404


class TestGetAssociatedExperiments:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [
            ExperimentOutput(
                id="exp-uuid",
                experiment_name="Exp1",
                experiment_info={},
                experiment_start_date="2024-01-01",
                experiment_end_date="2024-12-31",
            )
        ]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/genotypes/id/genotype-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/genotypes/id/nonexistent/experiments")
        assert response.status_code == 404


class TestUploadGenotypeRecords:
    @patch(RECORD_API_PATH)
    @patch(API_PATH)
    def test_success(self, mock_geno_cls, mock_record_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.id = "genotype-uuid"
        mock_obj.genotype_name = "test"
        mock_geno_cls.get_by_id.return_value = mock_obj
        mock_record_cls.insert.return_value = (True, ["id1", "id2"])
        response = test_client.post("/api/genotypes/id/genotype-uuid/records", json={
            "records": [
                {"variant_name": "2_24641", "population_name": "IT89KD-288", "call_value": "TT"},
                {"variant_name": "2_30714", "population_name": "IT89KD-288", "call_value": "CC"},
            ]
        })
        assert response.status_code == 201


class TestExportGenotype:
    @patch(API_PATH)
    def test_hapmap_export(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.export.return_value = "rs#\talleles\tchrom\tpos\n"
        mock_obj.genotype_name = "test"
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/genotypes/id/genotype-uuid/export?format=hapmap")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/genotypes/id/nonexistent/export?format=hapmap")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_empty_export(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.export.return_value = ""
        mock_obj.genotype_name = "test"
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/genotypes/id/genotype-uuid/export?format=hapmap")
        assert response.status_code == 404
