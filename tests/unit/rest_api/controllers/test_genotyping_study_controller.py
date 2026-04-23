"""Unit tests for the GenotypingStudyController, focused on the new
matrix-ingest endpoint used by the genomic import wizard.
"""

from unittest.mock import patch, MagicMock

import pytest

from gemini.rest_api.models import GenotypingStudyOutput

CONTROLLER_MODULE = "gemini.rest_api.controllers.genotyping_study"
STUDY_PATH = f"{CONTROLLER_MODULE}.GenotypingStudy"


@pytest.fixture
def mock_study():
    return GenotypingStudyOutput(
        id="study-uuid",
        study_name="test-study",
        study_info={},
    )


def _session_cm(acc_rows, variant_rows):
    """Build a fake db_engine.get_session() context manager whose session
    returns acc_rows on its first execute() call and variant_rows on the
    second. Mirrors the real endpoint's query order."""
    session = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=session)
    cm.__exit__ = MagicMock(return_value=None)

    state = {"calls": 0}

    def execute_side_effect(_stmt, *_a, **_kw):
        result = MagicMock()
        if state["calls"] == 0:
            result.all.return_value = acc_rows
        else:
            result.all.return_value = variant_rows
        state["calls"] += 1
        return result

    session.execute.side_effect = execute_side_effect
    return cm


class TestIngestMatrix:
    @patch(f"{CONTROLLER_MODULE}._copy_insert_genotype_records")
    @patch(f"{CONTROLLER_MODULE}.VariantModel.insert_bulk")
    @patch(f"{CONTROLLER_MODULE}.db_engine")
    @patch(STUDY_PATH)
    def test_happy_path(
        self,
        mock_study_cls,
        mock_db_engine,
        mock_variant_insert,
        mock_copy_insert,
        test_client,
        mock_study,
    ):
        mock_study_cls.get_by_id.return_value = mock_study
        mock_variant_insert.return_value = ["v1", "v2"]
        mock_copy_insert.return_value = 4

        acc_rows = [
            MagicMock(id="acc-a-id", accession_name="SAMPLE_A"),
            MagicMock(id="acc-b-id", accession_name="SAMPLE_B"),
        ]
        variant_rows = [
            MagicMock(id="v1", variant_name="snp1"),
            MagicMock(id="v2", variant_name="snp2"),
        ]
        mock_db_engine.get_session.return_value = _session_cm(acc_rows, variant_rows)

        payload = {
            "sample_headers": ["SAMPLE_A", "SAMPLE_B"],
            "variant_rows": [
                {
                    "variant_name": "snp1",
                    "chromosome": 1,
                    "position": 10.0,
                    "alleles": "A/C",
                    "calls": ["AA", "AC"],
                },
                {
                    "variant_name": "snp2",
                    "chromosome": 1,
                    "position": 20.0,
                    "alleles": "G/T",
                    "calls": ["GG", "TT"],
                },
            ],
        }
        response = test_client.post(
            "/api/genotyping_studies/id/study-uuid/ingest-matrix",
            json=payload,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["variants_inserted"] == 2
        assert body["records_inserted"] == 4
        assert body["errors"] == []

        # Four (2 variants × 2 samples) records should have been offered to the
        # bulk inserter. Verify payload shape: study/variant/accession IDs set.
        records = mock_copy_insert.call_args.args[0]
        assert len(records) == 4
        first = records[0]
        assert first["study_id"] == "study-uuid"
        assert first["study_name"] == "test-study"
        assert first["variant_name"] == "snp1"
        assert first["accession_name"] == "SAMPLE_A"
        assert first["call_value"] == "AA"

    @patch(STUDY_PATH)
    def test_missing_study(self, mock_study_cls, test_client):
        mock_study_cls.get_by_id.return_value = None
        response = test_client.post(
            "/api/genotyping_studies/id/nope/ingest-matrix",
            json={"sample_headers": ["A"], "variant_rows": []},
        )
        assert response.status_code == 404

    @patch(STUDY_PATH)
    def test_empty_batch(self, mock_study_cls, test_client, mock_study):
        mock_study_cls.get_by_id.return_value = mock_study
        response = test_client.post(
            "/api/genotyping_studies/id/study-uuid/ingest-matrix",
            json={"sample_headers": [], "variant_rows": []},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["variants_inserted"] == 0
        assert body["records_inserted"] == 0
        assert "Empty batch" in body["errors"][0]

    @patch(f"{CONTROLLER_MODULE}._copy_insert_genotype_records")
    @patch(f"{CONTROLLER_MODULE}.VariantModel.insert_bulk")
    @patch(f"{CONTROLLER_MODULE}.db_engine")
    @patch(STUDY_PATH)
    def test_unknown_accession_reported(
        self,
        mock_study_cls,
        mock_db_engine,
        mock_variant_insert,
        mock_copy_insert,
        test_client,
        mock_study,
    ):
        mock_study_cls.get_by_id.return_value = mock_study
        mock_variant_insert.return_value = ["v1"]
        mock_copy_insert.return_value = 0

        mock_db_engine.get_session.return_value = _session_cm(
            acc_rows=[],
            variant_rows=[MagicMock(id="v1", variant_name="snp1")],
        )

        response = test_client.post(
            "/api/genotyping_studies/id/study-uuid/ingest-matrix",
            json={
                "sample_headers": ["MISSING_A", "MISSING_B"],
                "variant_rows": [
                    {
                        "variant_name": "snp1",
                        "chromosome": 1,
                        "position": 10.0,
                        "alleles": "A/C",
                        "calls": ["AA", "AC"],
                    }
                ],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["records_inserted"] == 0
        assert any("Unknown accession: MISSING_A" in e for e in body["errors"])
        assert any("Unknown accession: MISSING_B" in e for e in body["errors"])
        # No records to insert → helper should not have been called.
        assert not mock_copy_insert.called
