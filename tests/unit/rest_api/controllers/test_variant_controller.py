"""Unit tests for the VariantController."""

import pytest
from unittest.mock import patch, MagicMock
from gemini.rest_api.models import VariantOutput

API_PATH = "gemini.rest_api.controllers.variant.Variant"


@pytest.fixture
def mock_output():
    return {
        "id": "variant-uuid",
        "variant_name": "2_24641",
        "chromosome": 1,
        "position": 0.0,
        "alleles": "T/C",
        "design_sequence": "AGAC[T/C]GACT",
        "variant_info": {},
    }


class TestGetAllVariants:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_all.return_value = [VariantOutput(**mock_output)]
        response = test_client.get("/api/variants/all")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_empty(self, mock_cls, test_client):
        mock_cls.get_all.return_value = None
        response = test_client.get("/api/variants/all")
        assert response.status_code == 404

    @patch(API_PATH)
    def test_exception(self, mock_cls, test_client):
        mock_cls.get_all.side_effect = Exception("DB error")
        response = test_client.get("/api/variants/all")
        assert response.status_code == 500


class TestGetVariants:
    @patch(API_PATH)
    def test_search_success(self, mock_cls, test_client, mock_output):
        mock_cls.search.return_value = [VariantOutput(**mock_output)]
        response = test_client.get("/api/variants/?chromosome=1")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_search_empty(self, mock_cls, test_client):
        mock_cls.search.return_value = None
        response = test_client.get("/api/variants/?chromosome=99")
        assert response.status_code == 404


class TestGetVariantById:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.get_by_id.return_value = VariantOutput(**mock_output)
        response = test_client.get("/api/variants/id/variant-uuid")
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.get("/api/variants/id/nonexistent")
        assert response.status_code == 404


class TestCreateVariant:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_cls.create.return_value = VariantOutput(**mock_output)
        response = test_client.post("/api/variants/", json={
            "variant_name": "2_24641", "chromosome": 1, "position": 0.0, "alleles": "T/C"
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_failure(self, mock_cls, test_client):
        mock_cls.create.return_value = None
        response = test_client.post("/api/variants/", json={
            "variant_name": "2_24641", "chromosome": 1, "position": 0.0, "alleles": "T/C"
        })
        assert response.status_code == 500


class TestCreateVariantsBulk:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_cls.create_bulk.return_value = (True, ["id1", "id2"])
        response = test_client.post("/api/variants/bulk", json={
            "variants": [{"variant_name": "a"}, {"variant_name": "b"}]
        })
        assert response.status_code == 201

    @patch(API_PATH)
    def test_failure(self, mock_cls, test_client):
        mock_cls.create_bulk.return_value = (False, [])
        response = test_client.post("/api/variants/bulk", json={"variants": []})
        assert response.status_code == 500


class TestUpdateVariant:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client, mock_output):
        mock_obj = MagicMock()
        mock_obj.update.return_value = VariantOutput(**mock_output)
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.patch("/api/variants/id/variant-uuid", json={"chromosome": 2})
        assert response.status_code == 200

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.patch("/api/variants/id/nonexistent", json={"chromosome": 2})
        assert response.status_code == 404


class TestDeleteVariant:
    @patch(API_PATH)
    def test_success(self, mock_cls, test_client):
        mock_obj = MagicMock()
        mock_obj.delete.return_value = True
        mock_cls.get_by_id.return_value = mock_obj
        response = test_client.delete("/api/variants/id/variant-uuid")
        assert response.status_code == 200 or response.status_code == 204

    @patch(API_PATH)
    def test_not_found(self, mock_cls, test_client):
        mock_cls.get_by_id.return_value = None
        response = test_client.delete("/api/variants/id/nonexistent")
        assert response.status_code == 404
