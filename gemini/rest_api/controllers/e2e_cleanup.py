"""Test-only cleanup endpoint for the Playwright E2E suite.

Each E2E test names every entity it creates with a per-test prefix
(see ``frontend/tests/helpers/uniquePrefix.ts``). After the test runs,
the test harness calls
``DELETE /api/e2e_cleanup?prefix=E2E-<slug>-<timestamp>`` so the rows it
created don't pile up in the dev database across runs.

This endpoint is gated behind ``GEMINI_E2E_CLEANUP_ENABLED=1`` so it
only exists in dev/CI environments. In production the env var is unset
and every call returns 404. The frontend never calls it; only the
Playwright fixture does.
"""
import logging
import os

from litestar import Response
from litestar.controller import Controller
from litestar.handlers import delete
from sqlalchemy import select

from gemini.api.experiment import Experiment
from gemini.api.genotyping_study import GenotypingStudy
from gemini.db.core.base import db_engine
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.experiments import ExperimentModel
from gemini.db.models.genotyping_studies import GenotypingStudyModel
from gemini.db.models.lines import LineModel
from gemini.rest_api.models import RESTAPIError

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.environ.get("GEMINI_E2E_CLEANUP_ENABLED") == "1"


class E2ECleanupController(Controller):
    """Sweep entities whose names start with a given prefix."""

    @delete(sync_to_thread=True, status_code=200)
    def cleanup_by_prefix(self, prefix: str) -> dict:
        if not _enabled():
            # Pretend the route doesn't exist so a stray prod hit looks
            # like a routing typo, not a deliberate access-control denial.
            return Response(
                content=RESTAPIError(
                    error="Not Found", error_description=""
                ),
                status_code=404,
            )
        if not prefix or len(prefix) < 4:
            return Response(
                content=RESTAPIError(
                    error="Invalid prefix",
                    error_description="prefix must be at least 4 chars",
                ),
                status_code=400,
            )

        deleted = {
            "experiments": 0,
            "genotyping_studies": 0,
            "accessions": 0,
            "lines": 0,
        }

        # Collect ids first (separate session) so the per-row deletes
        # below can each run in their own transaction without holding
        # the listing transaction open.
        with db_engine.get_session() as session:
            exp_ids = list(session.execute(
                select(ExperimentModel.id).where(
                    ExperimentModel.experiment_name.like(f"{prefix}%")
                )
            ).scalars().all())
            study_ids = list(session.execute(
                select(GenotypingStudyModel.id).where(
                    GenotypingStudyModel.study_name.like(f"{prefix}%")
                )
            ).scalars().all())

        # Experiment cascade handles its associated studies/accessions/
        # plots/etc. automatically (Phase 9d'.5 wired study deletion via
        # GenotypingStudy.delete() into the cascade), so we drive that
        # path first.
        for eid in exp_ids:
            try:
                exp = Experiment.get_by_id(id=eid)
                if exp is None:
                    continue
                if exp.delete():
                    deleted["experiments"] += 1
            except Exception as exc:
                logger.warning(
                    "E2E cleanup: experiment %s delete failed: %s", eid, exc
                )

        # Studies that weren't tied to a deleted experiment (the
        # genotyping-studies-crud spec creates standalone studies).
        for sid in study_ids:
            try:
                study = GenotypingStudy.get_by_id(id=sid)
                if study is None:
                    continue  # already cascaded above
                if study.delete():
                    deleted["genotyping_studies"] += 1
            except Exception as exc:
                logger.warning(
                    "E2E cleanup: study %s delete failed: %s", sid, exc
                )

        # Accessions / lines created by a spec but not reachable from
        # any experiment cascade (e.g. the ones created during the
        # genomic wizard's sample-resolve step before the experiment
        # association is recorded).
        with db_engine.get_session() as session:
            acc_count = session.execute(
                AccessionModel.__table__.delete().where(
                    AccessionModel.accession_name.like(f"{prefix}%")
                )
            ).rowcount or 0
            line_count = session.execute(
                LineModel.__table__.delete().where(
                    LineModel.line_name.like(f"{prefix}%")
                )
            ).rowcount or 0
            deleted["accessions"] = int(acc_count)
            deleted["lines"] = int(line_count)

        return {"prefix": prefix, "deleted": deleted}
