"""Tests for the Trait controller."""
import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import (
    TraitOutput, ExperimentOutput, DatasetOutput, TraitRecordOutput
)


API_PATH = "gemini.rest_api.controllers.trait.Trait"
RECORD_PATH = "gemini.rest_api.controllers.trait.TraitRecord"


@pytest.fixture
def mock_output():
    return {
        "id": "trait-uuid",
        "trait_name": "Trait A",
        "trait_units": "cm",
        "trait_level_id": 1,
        "trait_metrics": {},
        "trait_info": {},
    }


class TestGetAllTraits:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [TraitOutput(**mock_output)]
        response = test_client.get("/api/traits/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/traits/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/traits/all")
        assert response.status_code == 500


class TestGetTraits:

    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [TraitOutput(**mock_output)]
        response = test_client.get("/api/traits", params={"trait_name": "Trait A"})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_not_found(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/traits", params={"trait_name": "Missing"})
        assert response.status_code == 404

    @patch(API_PATH)
    def test_search_error(self, mock_cls, test_client):
        mock_cls.search.side_effect = Exception("DB error")
        response = test_client.get("/api/traits", params={"trait_name": "Trait A"})
        assert response.status_code == 500


class TestGetTraitById:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = TraitOutput(**mock_output)
        response = test_client.get("/api/traits/id/trait-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/traits/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/traits/id/trait-uuid")
        assert response.status_code == 500


class TestCreateTrait:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = TraitOutput(**mock_output)
        response = test_client.post("/api/traits", json={
            "trait_name": "Trait A",
            "trait_level_id": 0,
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_create_returns_none(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/traits", json={
            "trait_name": "Trait A",
            "trait_level_id": 0,
        })
        assert response.status_code == 500


class TestUpdateTrait:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = TraitOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/traits/id/trait-uuid", json={
            "trait_name": "Updated",
        })
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/traits/id/missing", json={
            "trait_name": "Updated",
        })
        assert response.status_code == 404


class TestDeleteTrait:

    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/traits/id/trait-uuid")
        assert response.status_code in (200, 204)

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/traits/id/missing")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_delete_fails(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = False
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/traits/id/trait-uuid")
        assert response.status_code == 500


class TestTraitAssociations:

    @patch(API_PATH)
    def test_get_experiments(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = [ExperimentOutput(
            id="e1", experiment_name="Exp A", experiment_info={},
            experiment_start_date=None, experiment_end_date=None
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/traits/id/trait-uuid/experiments")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_get_datasets(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = [DatasetOutput(
            id="d1", dataset_name="DS", collection_date=None,
            dataset_info={}, dataset_type_id=0
        )]
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/traits/id/trait-uuid/datasets")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_association_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/traits/id/missing/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_experiments.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/traits/id/trait-uuid/experiments")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_experiments_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/traits/id/trait-uuid/experiments")
        assert response.status_code == 500

    @patch(API_PATH)
    def test_get_datasets_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/traits/id/missing/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_no_data(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.get_associated_datasets.return_value = None
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.get("/api/traits/id/trait-uuid/datasets")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_get_datasets_error(self, mock_cls, test_client):
        mock_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/traits/id/trait-uuid/datasets")
        assert response.status_code == 500


class TestTraitRecords:

    @patch(RECORD_PATH)
    def test_get_record_by_id_success(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = TraitRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", trait_id="t1",
            trait_name="Trait A", trait_value=1.0, collection_date=None,
            dataset_id=None, dataset_name=None, experiment_id=None,
            experiment_name=None, season_id=None, season_name=None,
            site_id=None, site_name=None, plot_id=None, plot_number=None,
            plot_row_number=None, plot_column_number=None, record_info=None
        )
        response = test_client.get("/api/traits/records/id/r1")
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_get_record_by_id_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.get("/api/traits/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_get_record_by_id_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.get("/api/traits/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = True
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/traits/records/id/r1")
        assert response.status_code in (200, 204)

    @patch(RECORD_PATH)
    def test_delete_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.delete("/api/traits/records/id/missing")
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_delete_record_fails(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.delete.return_value = False
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.delete("/api/traits/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_delete_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.delete("/api/traits/records/id/r1")
        assert response.status_code == 500

    @patch(RECORD_PATH)
    def test_update_record_success(self, mock_record_cls, test_client):
        mock_record = MagicMock()
        mock_record.update.return_value = TraitRecordOutput(
            id="r1", timestamp="2024-01-01T00:00:00", trait_id="t1",
            trait_name="Trait A", trait_value=2.0, collection_date=None,
            dataset_id=None, dataset_name=None, experiment_id=None,
            experiment_name=None, season_id=None, season_name=None,
            site_id=None, site_name=None, plot_id=None, plot_number=None,
            plot_row_number=None, plot_column_number=None, record_info=None
        )
        mock_record_cls.get_by_id.return_value = mock_record
        response = test_client.patch("/api/traits/records/id/r1", json={
            "trait_value": 2.0,
        })
        assert response.status_code == 200

    @patch(RECORD_PATH)
    def test_update_record_not_found(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.return_value = None
        response = test_client.patch("/api/traits/records/id/missing", json={
            "trait_value": 2.0,
        })
        assert response.status_code == 404

    @patch(RECORD_PATH)
    def test_update_record_error(self, mock_record_cls, test_client):
        mock_record_cls.get_by_id.side_effect = Exception("DB error")
        response = test_client.patch("/api/traits/records/id/r1", json={
            "trait_value": 2.0,
        })
        assert response.status_code == 500
