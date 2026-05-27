"""Integration tests for ``DELETE /api/e2e_cleanup``.

Drives the real Litestar app + real Postgres test DB. No mocks: the
cleanup endpoint exercises the same ``Experiment.delete()`` cascade
that production runs, and these tests pin the failure-surfacing
behavior added 2026-05-18 so the Playwright fixture's ``!res.ok``
branch fails-loud when any underlying delete fails instead of silently
leaking rows.

Requires: ``docker compose -f tests/docker-compose.test.yaml up -d``
"""
import os
import uuid

import pytest
from sqlalchemy import text


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(setup_real_db):
    """Litestar TestClient backed by the real test DB."""
    from litestar.testing import TestClient
    from gemini.rest_api.app import app
    with TestClient(app=app) as c:
        yield c


@pytest.fixture
def cleanup_enabled():
    """The endpoint is gated behind GEMINI_E2E_CLEANUP_ENABLED=1; flip
    it on for tests that exercise the happy path. Tests that verify
    the gate itself toggle it off explicitly."""
    prev = os.environ.get("GEMINI_E2E_CLEANUP_ENABLED")
    os.environ["GEMINI_E2E_CLEANUP_ENABLED"] = "1"
    yield
    if prev is None:
        os.environ.pop("GEMINI_E2E_CLEANUP_ENABLED", None)
    else:
        os.environ["GEMINI_E2E_CLEANUP_ENABLED"] = prev


class TestEndpointGate:

    def test_disabled_returns_404(self, client):
        """Without GEMINI_E2E_CLEANUP_ENABLED, the endpoint pretends
        it doesn't exist — so a stray prod hit looks like a routing
        typo, not a gated access denial."""
        os.environ.pop("GEMINI_E2E_CLEANUP_ENABLED", None)
        resp = client.delete("/api/e2e_cleanup", params={"prefix": "anything"})
        assert resp.status_code == 404

    def test_prefix_too_short_returns_400(self, client, cleanup_enabled):
        """A 1-3 char prefix is rejected before the DB is touched."""
        resp = client.delete("/api/e2e_cleanup", params={"prefix": "ab"})
        assert resp.status_code == 400


class TestHappyPath:

    def test_no_match_returns_200_with_empty_failed(self, client, cleanup_enabled):
        """No matching rows → 200 with zero counts and an empty
        ``failed`` array. The Playwright fixture treats 2xx as
        success; the array being empty (not absent) is what the
        contract guarantees."""
        resp = client.delete(
            "/api/e2e_cleanup", params={"prefix": "E2E-nothing-matches"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"] == {
            "experiments": 0, "genotyping_studies": 0,
            "accessions": 0, "lines": 0,
        }
        assert body["failed"] == []

    def test_real_experiment_cascade_returns_200(
        self, client, setup_real_db, cleanup_enabled,
    ):
        """End-to-end: seed an experiment matching the prefix, hit
        the endpoint, verify both the response and the database
        state. Real cascade through ``Experiment.delete()``."""
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.core.base import db_engine

        ExperimentModel.get_or_create(experiment_name="E2E-cleanup-real-1")
        ExperimentModel.get_or_create(experiment_name="E2E-cleanup-real-2")

        resp = client.delete(
            "/api/e2e_cleanup", params={"prefix": "E2E-cleanup-real-"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"]["experiments"] == 2
        assert body["failed"] == []

        with db_engine.get_session() as session:
            remaining = session.execute(text(
                "SELECT count(*) FROM gemini.experiments "
                "WHERE experiment_name LIKE 'E2E-cleanup-real-%'"
            )).scalar()
        assert remaining == 0


class TestFailureSurfacing:
    """The regression-pinning class: pre-fix, the endpoint silently
    reported ``experiments: 0`` and HTTP 200 whenever
    ``Experiment.delete()`` returned False from inside its own
    try/except (the symptom from the 2026-05-18 dev-DB sweep). Now
    the endpoint accumulates failures and returns 500 with a
    ``failed`` array listing each entity that didn't get deleted."""

    def test_delete_returning_false_surfaces_as_500(
        self, client, setup_real_db, cleanup_enabled,
    ):
        """Force ``Experiment.delete()`` to return False for a real
        seeded experiment by monkey-patching JUST that one method on
        the API surface. The rest of the stack (route resolution,
        DB session, the per-entity loop, the response shape) is
        real. Pre-fix this returned 200 with ``experiments: 0`` and
        no failure record; post-fix it returns 500 with a populated
        ``failed`` array."""
        from gemini.api import experiment as exp_module
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.get_or_create(experiment_name="E2E-fail-target-1")

        original_delete = exp_module.Experiment.delete

        def returns_false(self):
            return False

        exp_module.Experiment.delete = returns_false
        try:
            resp = client.delete(
                "/api/e2e_cleanup", params={"prefix": "E2E-fail-target-"},
            )
        finally:
            exp_module.Experiment.delete = original_delete

        assert resp.status_code == 500, (
            f"Expected 500 (failure-surfaced), got "
            f"{resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["deleted"]["experiments"] == 0
        assert len(body["failed"]) == 1
        entry = body["failed"][0]
        assert entry["kind"] == "experiment"
        # The id field must match the seeded experiment's UUID, so
        # the operator can localize the failure even without rest-api
        # logs.
        assert uuid.UUID(entry["id"])
        assert "returned False" in entry["reason"]

    def test_delete_raising_surfaces_as_500(
        self, client, setup_real_db, cleanup_enabled,
    ):
        """Same shape when ``Experiment.delete()`` raises instead of
        returning False — the per-entity try/except inside the
        controller catches it but the response still 500s with the
        exception message in ``failed[].reason``."""
        from gemini.api import experiment as exp_module
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.get_or_create(experiment_name="E2E-raises-target-1")

        original_delete = exp_module.Experiment.delete

        def raises(self):
            raise RuntimeError("boom from real test")

        exp_module.Experiment.delete = raises
        try:
            resp = client.delete(
                "/api/e2e_cleanup", params={"prefix": "E2E-raises-target-"},
            )
        finally:
            exp_module.Experiment.delete = original_delete

        assert resp.status_code == 500
        body = resp.json()
        assert len(body["failed"]) == 1
        entry = body["failed"][0]
        assert entry["kind"] == "experiment"
        assert entry["reason"] == "boom from real test"
