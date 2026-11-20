"""Import from the previous GEMI desktop app (v0.0.x).

GET  /api/legacy_import/plan   — the dry run: is an old install mounted, and
                                 what would be imported (counts, bytes,
                                 experiments, seasons, what can't be and why)
POST /api/legacy_import/start  — queue the IMPORT_LEGACY job (geo worker)

Superuser only: the import creates experiments and datasets for the whole
install. The old install is mounted read-only (see
gemini/importers/gemi_legacy); nothing here can change it.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from litestar import Response
from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers import get, post

from gemini.api.dataset import Dataset
from gemini.api.job import Job
from gemini.api.user import User
from gemini.importers.gemi_legacy.plan import plan_import
from gemini.importers.gemi_legacy.processing import plan_processing
from gemini.importers.gemi_legacy.reader import LegacyDatabase
from gemini.importers.gemi_legacy.run import dataset_name
from gemini.importers.gemi_legacy.source import legacy_data_dir, legacy_database
from gemini.rest_api.dependencies import provide_superuser
from gemini.rest_api.models import RESTAPIError

logger = logging.getLogger(__name__)


def current_plan() -> dict[str, Any]:
    """The dry run. `already_imported`: uploads whose dataset exists (its
    name is derived from the old upload's id), i.e. a previous import (or
    an interrupted one, which re-running completes)."""
    db_path = legacy_database()
    if db_path is None:
        return {"available": False}
    with LegacyDatabase(db_path) as db:
        plan = plan_import(db, legacy_data_dir())
        processing = plan_processing(db, legacy_data_dir())
    done = [u.upload_id for u in plan.to_import if Dataset.exists(dataset_name=dataset_name(u))]
    return {"available": True, **plan.summary(), "already_imported": len(done),
            "processing": processing.summary()}


class LegacyImportController(Controller):
    dependencies = {
        "superuser": Provide(provide_superuser, sync_to_thread=True),
    }

    @get(path="/plan", sync_to_thread=True)
    def get_plan(self, superuser: Optional[User]) -> dict[str, Any] | Response:
        try:
            return current_plan()
        except Exception as exc:  # noqa: BLE001 — a damaged old database
            logger.exception("legacy import plan failed")
            return Response(
                content=RESTAPIError(
                    error="Can't read the previous GEMI install",
                    error_description=str(exc),
                ),
                status_code=500,
            )

    @post(path="/start", sync_to_thread=True, status_code=200)
    def start(self, superuser: Optional[User]) -> dict[str, Any] | Response:
        if legacy_database() is None:
            return Response(
                content=RESTAPIError(
                    error="No previous GEMI install",
                    error_description="No previous GEMI install is available to import.",
                ),
                status_code=404,
            )
        job = Job.create(job_type="IMPORT_LEGACY", parameters={})
        if job is None:
            return Response(
                content=RESTAPIError(error="Couldn't queue the import", error_description=""),
                status_code=500,
            )
        return {"job_id": str(job.id)}
