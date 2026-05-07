import os
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import computed_field
from pydantic import model_validator
from typing import Any, Optional, Union, ClassVar
from uuid import UUID

import logging
from gemini.storage.providers.minio_storage import MinioStorageProvider
from gemini.storage.config.storage_config import MinioStorageConfig
from gemini.manager import GEMINIManager, GEMINIComponentType

from functools import cached_property
from abc import ABC, abstractmethod

manager = GEMINIManager()
minio_storage_settings = manager.get_component_settings(GEMINIComponentType.STORAGE)
minio_storage_config = MinioStorageConfig(
    endpoint=f"{minio_storage_settings['GEMINI_STORAGE_HOSTNAME']}:{minio_storage_settings['GEMINI_STORAGE_PORT']}",
    access_key=minio_storage_settings['GEMINI_STORAGE_ACCESS_KEY'],
    secret_key=minio_storage_settings['GEMINI_STORAGE_SECRET_KEY'],
    bucket_name=minio_storage_settings['GEMINI_STORAGE_BUCKET_NAME'],
    secure=False
)
minio_storage_provider = MinioStorageProvider(minio_storage_config)

logger = logging.getLogger(__name__)

class APIBase(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
        extra="allow"
    )

    @classmethod
    @abstractmethod
    def exists(cls, **kwargs) -> bool:
        pass

    @classmethod
    @abstractmethod
    def create(cls, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def get_by_id(cls, id: Union[UUID, int, str]):
        pass

    @classmethod
    @abstractmethod
    def get_all(cls):
        pass

    @classmethod
    @abstractmethod
    def get(cls, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def search(cls, **search_parameters):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def refresh(self):
        pass

def sweep_minio_prefixes(prefixes: list[str]) -> list[str]:
    """Idempotently delete every object under each given MinIO prefix.

    Called from entity ``delete()`` methods AFTER the DB transaction
    commits, so removing a Dataset/Experiment/Sensor/… also cleans up
    the files it owns. Failures here are best-effort: the DB delete is
    the source of truth, a stale prefix is recoverable, but a partial
    DB delete is not. We log failures at ERROR with the prefix so an
    operator can re-run the sweep by hand, and return the list of
    failed prefixes so the caller can surface a single summary line
    (the experiment no longer exists at that point, so this is the
    only place the orphan is recorded).
    """
    import time
    failed: list[str] = []
    for prefix in prefixes:
        if not prefix:
            continue
        t0 = time.monotonic()
        try:
            removed = minio_storage_provider.delete_prefix(prefix)
            elapsed = time.monotonic() - t0
            # Always log duration so a stuck prefix is visible even when
            # the call eventually returns 0 — the delay, not the count,
            # is the signal we care about here.
            logger.info(
                f"Swept {removed} MinIO object(s) under prefix {prefix!r} in {elapsed:.2f}s."
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            failed.append(prefix)
            logger.error(
                f"ORPHANED MinIO prefix {prefix!r} — sweep failed after "
                f"{elapsed:.2f}s: {e}. Clean up manually with "
                f"`mc rm -r --force <alias>/<bucket>/{prefix}` or re-run "
                f"the sweep once the storage issue is resolved."
            )
    return failed


def sweep_orphan_datasets(
    candidate_dataset_ids: list,
    owner: str = "",
) -> int:
    """Drop ``gemini.datasets`` rows from a candidate set that have no
    remaining inbound association.

    The ``populate_*_record_ids`` BEFORE-INSERT triggers
    (``6_init_functions.sql``) silently insert a ``gemini.datasets`` row
    + a matching ``*_datasets`` association row whenever a record is
    inserted with a previously-unseen ``dataset_name``. When the parent
    (Trait/Sensor/Procedure/Script/Model) is later deleted, the
    ``*_datasets`` join CASCADEs but the ``gemini.datasets`` row
    survives — that's the orphan we sweep here.

    Pattern matches the variant/accession orphan-sweep in
    ``GenotypingStudy.delete()`` at ``genotyping_study.py:230-285``:
    capture candidate ids BEFORE the parent's cascade fires (caller's
    responsibility), then call this helper AFTER the cascade has
    committed. Scoped to the candidate set so a concurrent unrelated
    orphaning isn't collateral'd.

    Returns the count of dataset rows actually deleted.
    """
    if not candidate_dataset_ids:
        return 0
    from sqlalchemy import text
    from gemini.db.core.base import db_engine
    from gemini.db.models.datasets import DatasetModel

    # Resolve candidates to *actual orphans* in one query: ids that
    # exist in `gemini.datasets` AND have no row in any of the six
    # `*_datasets` association tables. Avoids the false-positive class
    # "id never existed in gemini.datasets" which a complement-style
    # check (still-referenced vs. all candidates) would mark as orphan.
    #
    # CAST(:cand AS uuid[]) keeps psycopg2 from complaining about
    # "uuid = text" when the bound param is a Python list of uuid/str.
    candidate_strs = [str(c) for c in candidate_dataset_ids]
    with db_engine.get_session() as session:
        orphan_ids = list(session.execute(
            text(
                """
                SELECT d.id FROM gemini.datasets d
                WHERE d.id = ANY(CAST(:cand AS uuid[]))
                  AND NOT EXISTS (SELECT 1 FROM gemini.experiment_datasets x WHERE x.dataset_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM gemini.trait_datasets x      WHERE x.dataset_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM gemini.sensor_datasets x     WHERE x.dataset_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM gemini.procedure_datasets x  WHERE x.dataset_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM gemini.script_datasets x     WHERE x.dataset_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM gemini.model_datasets x      WHERE x.dataset_id = d.id)
                """
            ),
            {"cand": candidate_strs},
        ).scalars().all())
        if orphan_ids:
            session.execute(
                DatasetModel.__table__.delete().where(
                    DatasetModel.id.in_(orphan_ids)
                )
            )
            session.commit()
            logger.info(
                "Deleted %d orphan dataset(s) after deleting %s.",
                len(orphan_ids), owner or "<unknown>",
            )
        return len(orphan_ids)


class FileHandlerMixin(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    minio_storage_provider: ClassVar[MinioStorageProvider] = minio_storage_provider

    @classmethod
    @abstractmethod
    def process_record(cls, record: 'APIBase') -> 'APIBase':
        pass
    
    @classmethod
    @abstractmethod
    def create_file_uri(cls, record_file_key: str) -> str:
        pass

