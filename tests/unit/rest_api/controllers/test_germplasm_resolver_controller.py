"""Unit tests for the GermplasmResolverController."""

from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

from gemini.api.germplasm_resolver import ResolveResult

RESOLVE_PATH = "gemini.rest_api.controllers.germplasm_resolver.resolve_germplasm"
ACCESSION_PATH = "gemini.rest_api.controllers.germplasm_resolver.Accession"
LINE_PATH = "gemini.rest_api.controllers.germplasm_resolver.Line"
MODEL_PATH = "gemini.rest_api.controllers.germplasm_resolver.AccessionAliasModel"


class TestResolveEndpoint:
    @patch(RESOLVE_PATH)
    def test_success(self, mock_resolve, test_client):
        mock_resolve.return_value = [
            ResolveResult(
                input_name="MAGIC110",
                match_kind="accession_exact",
                accession_id="acc-uuid",
                canonical_name="MAGIC110",
            ),
            ResolveResult(input_name="ghost", match_kind="unresolved"),
        ]
        response = test_client.post(
            "/api/germplasm/resolve",
            json={"names": ["MAGIC110", "ghost"]},
        )
        assert response.status_code == 201
        body = response.json()
        assert len(body["results"]) == 2
        assert body["results"][0]["match_kind"] == "accession_exact"
        assert body["results"][0]["canonical_name"] == "MAGIC110"
        assert body["results"][1]["match_kind"] == "unresolved"

    @patch(RESOLVE_PATH)
    def test_exception_returns_500(self, mock_resolve, test_client):
        mock_resolve.side_effect = RuntimeError("db down")
        response = test_client.post(
            "/api/germplasm/resolve",
            json={"names": ["x"]},
        )
        assert response.status_code == 500


class TestBulkAliasesValidation:
    def test_invalid_scope_rejected(self, test_client):
        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={"scope": "weird", "entries": []},
        )
        assert response.status_code == 400

    def test_scope_global_with_experiment_id_rejected(self, test_client):
        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={"scope": "global", "experiment_id": str(uuid4()), "entries": []},
        )
        assert response.status_code == 400

    def test_scope_experiment_without_experiment_id_rejected(self, test_client):
        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={"scope": "experiment", "entries": []},
        )
        assert response.status_code == 400


class TestBulkAliasesBehavior:
    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_creates_new_alias_for_accession(self, mock_acc, mock_line, mock_model, test_client):
        mock_acc.get.return_value = MagicMock(id="acc-uuid")
        mock_model.get_by_parameters.return_value = None
        mock_model.create.return_value = MagicMock(id="alias-uuid")

        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{"alias": "foo", "accession_name": "PI-1"}],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["created"] == 1
        assert body["updated"] == 0
        assert body["errors"] == []

    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_both_target_fields_is_error(self, mock_acc, mock_line, mock_model, test_client):
        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{"alias": "foo", "accession_name": "A", "line_name": "L"}],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert body["errors"][0]["alias"] == "foo"

    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_missing_accession_is_error(self, mock_acc, mock_line, mock_model, test_client):
        mock_acc.get.return_value = None

        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{"alias": "foo", "accession_name": "does-not-exist"}],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert "not found" in body["errors"][0]["reason"].lower()

    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_conflict_on_different_target_rejected(
        self, mock_acc, mock_line, mock_model, test_client
    ):
        mock_acc.get.return_value = MagicMock(id="new-acc")
        existing = MagicMock()
        existing.accession_id = "OTHER-acc"
        existing.line_id = None
        mock_model.get_by_parameters.return_value = existing

        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{"alias": "1", "accession_name": "MAGIC110"}],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert "different target" in body["errors"][0]["reason"].lower()

    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_same_target_no_op(self, mock_acc, mock_line, mock_model, test_client):
        mock_acc.get.return_value = MagicMock(id="acc-x")
        existing = MagicMock()
        existing.accession_id = "acc-x"
        existing.line_id = None
        existing.source = "existing"
        mock_model.get_by_parameters.return_value = existing

        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{"alias": "1", "accession_name": "MAGIC110"}],
            },
        )
        body = response.json()
        assert body["created"] == 0
        assert body["updated"] == 0
        assert body["errors"] == []

    @patch(MODEL_PATH)
    @patch(LINE_PATH)
    @patch(ACCESSION_PATH)
    def test_same_target_updates_source(self, mock_acc, mock_line, mock_model, test_client):
        mock_acc.get.return_value = MagicMock(id="acc-x")
        existing = MagicMock()
        existing.accession_id = "acc-x"
        existing.line_id = None
        existing.source = "old"
        mock_model.get_by_parameters.return_value = existing

        response = test_client.post(
            "/api/germplasm/aliases/bulk",
            json={
                "scope": "global",
                "entries": [{
                    "alias": "1",
                    "accession_name": "MAGIC110",
                    "source": "import:summer2022.xlsx#MAGIC",
                }],
            },
        )
        body = response.json()
        assert body["updated"] == 1
        mock_model.update.assert_called_once()
