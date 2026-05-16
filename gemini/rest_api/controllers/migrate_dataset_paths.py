"""One-shot admin endpoint that migrates legacy MinIO keys to the
post-Option-A per-dataset layout.

The Option-A change inserts a dataset's 8-char short-id between
``{sensor}/`` and ``Images/`` in upload prefixes:

  legacy: Raw/{year}/{exp}/{loc}/{pop}/{date}/{plat}/{sensor}/Images/{file}
  new:    Raw/{year}/{exp}/{loc}/{pop}/{date}/{plat}/{sensor}/{shortId}/Images/{file}

For uploads that landed before the change, the experiment_files row
points at the legacy key. Walk every row, skip those already in the
new shape, copy the legacy MinIO object to the new key, update the
``object_name`` column, and remove the old object.

Idempotent: re-running is safe — already-migrated rows are detected
and skipped.

Gated behind ``GEMINI_ADMIN_MIGRATIONS_ENABLED=1`` so it 404s in any
environment that hasn't deliberately opted in. Run-once-then-disable:
operators should unset the env var after the migration completes.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from litestar import Response
from litestar.controller import Controller
from litestar.handlers import post
from sqlalchemy import select, update

from gemini.api.base import minio_storage_config, minio_storage_provider
from gemini.api._dataset_path_migration import (
    new_key_for as _new_key_for,
    short_id_from_uuid as _short_id_from_uuid,
)
from gemini.db.core.base import db_engine
from gemini.db.models.datasets import DatasetModel
from gemini.db.models.experiment_files import ExperimentFileModel
from gemini.rest_api.models import RESTAPIError

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.environ.get("GEMINI_ADMIN_MIGRATIONS_ENABLED") == "1"


class MigrateDatasetPathsController(Controller):
    """POST /api/migrate_dataset_paths — run-once migration."""

    @post(sync_to_thread=True, status_code=200)
    def run_migration(self) -> dict[str, Any] | Response:
        if not _enabled():
            return Response(
                content=RESTAPIError(
                    error="Not Found", error_description=""
                ),
                status_code=404,
            )

        logger.warning(
            "Dataset-path migration invoked. Disable "
            "GEMINI_ADMIN_MIGRATIONS_ENABLED after this completes."
        )

        bucket = minio_storage_config.bucket_name
        client = minio_storage_provider.client
        from minio.commonconfig import CopySource

        migrated = 0
        skipped = 0
        errors: list[dict[str, str]] = []

        # Pull every experiment_files row that has a dataset (rows
        # without one can't get a short-id and so can't be migrated;
        # they stay at their legacy keys until the experiment cascade
        # sweeps them).
        with db_engine.get_session() as session:
            rows = list(
                session.execute(
                    select(
                        ExperimentFileModel.id,
                        ExperimentFileModel.bucket,
                        ExperimentFileModel.object_name,
                        ExperimentFileModel.dataset_id,
                    ).where(ExperimentFileModel.dataset_id.is_not(None))
                ).all()
            )

        for row in rows:
            file_id, file_bucket, object_name, dataset_id = row
            short_id = _short_id_from_uuid(dataset_id)
            if not short_id:
                skipped += 1
                continue
            new_key = _new_key_for(object_name, short_id)
            if new_key is None:
                # Already migrated, or out-of-scope path (wizard
                # supplemental, processed output, etc.).
                skipped += 1
                continue
            try:
                client.copy_object(
                    file_bucket or bucket,
                    new_key,
                    CopySource(file_bucket or bucket, object_name),
                )
                client.remove_object(file_bucket or bucket, object_name)
                with db_engine.get_session() as session:
                    session.execute(
                        update(ExperimentFileModel)
                        .where(ExperimentFileModel.id == file_id)
                        .values(object_name=new_key)
                    )
                    session.commit()
                migrated += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "file_id": str(file_id),
                        "from": object_name,
                        "to": new_key,
                        "error": str(exc),
                    }
                )
                logger.warning(
                    "Migration failed for %s -> %s: %s",
                    object_name,
                    new_key,
                    exc,
                )

        # Also walk Dataset.dataset_info.files_prefix so the
        # informational pointer stays in sync. Best-effort: failures
        # here don't block the file-row migration above.
        with db_engine.get_session() as session:
            ds_rows = list(
                session.execute(
                    select(DatasetModel.id, DatasetModel.dataset_info)
                ).all()
            )
            for ds_id, info in ds_rows:
                if not isinstance(info, dict):
                    continue
                fp = info.get("files_prefix")
                if not isinstance(fp, str) or "/Images/" not in fp:
                    continue
                short_id = _short_id_from_uuid(ds_id)
                if not short_id:
                    continue
                new_fp = _new_key_for(fp.rstrip("/") + "/Images/_", short_id)
                # _new_key_for expected a trailing filename — strip it
                # back off, then re-add the trailing slash.
                if new_fp is None:
                    continue
                new_fp = new_fp.rsplit("/", 1)[0] + "/"
                try:
                    session.execute(
                        update(DatasetModel)
                        .where(DatasetModel.id == ds_id)
                        .values(
                            dataset_info={
                                **info,
                                "files_prefix": new_fp,
                            }
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to update dataset %s files_prefix: %s",
                        ds_id,
                        exc,
                    )
            session.commit()

        return {
            "migrated": migrated,
            "skipped": skipped,
            "errors": errors,
        }
