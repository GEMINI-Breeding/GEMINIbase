"""Propagate name changes to denormalized columns on record tables.

The record tables (``trait_records``, ``sensor_records``, ``dataset_records``,
``procedure_records``, ``script_records``, ``model_records``, ``genotype_records``)
carry the human-readable names of their parent entities alongside the FK ids
for fast filtering and streaming. That denormalization means a rename on any
referenced entity has to be fanned out to every affected record table —
otherwise the record-lookup paths (which search by name) silently return
empty results after a rename.

Rather than hand-rolling an ``UPDATE`` per affected record model in every
``update()`` method, ``cascade_rename`` takes the entity's id and the new
name, walks the list of record models, and issues one SQL ``UPDATE`` per
table that actually has both the matching id column and name column.
"""
from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from gemini.db.core.base import db_engine
from gemini.db.models.columnar.dataset_records import DatasetRecordModel
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
from gemini.db.models.columnar.model_records import ModelRecordModel
from gemini.db.models.columnar.procedure_records import ProcedureRecordModel
from gemini.db.models.columnar.script_records import ScriptRecordModel
from gemini.db.models.columnar.sensor_records import SensorRecordModel
from gemini.db.models.columnar.trait_records import TraitRecordModel


# Every record model that may carry a denormalized name column. The helper
# only issues an UPDATE against a model if both the id column and the name
# column are present on it, so listing extras here is harmless.
ALL_RECORD_MODELS = (
    DatasetRecordModel,
    GenotypeRecordModel,
    ModelRecordModel,
    ProcedureRecordModel,
    ScriptRecordModel,
    SensorRecordModel,
    TraitRecordModel,
)


def cascade_rename(
    entity_id: UUID | str,
    id_column: str,
    name_column: str,
    new_name: str,
    models: Optional[Iterable[type]] = None,
) -> None:
    """Write ``new_name`` into ``name_column`` on every row whose
    ``id_column`` matches ``entity_id``, across each record model that has
    the pair of columns.

    Args:
        entity_id: The renamed entity's primary key.
        id_column: The FK column on the record model (e.g. ``trait_id``).
        name_column: The denormalized name column on the record model
            (e.g. ``trait_name``).
        new_name: The new value to write.
        models: Optional override for the list of models to consider.
            Defaults to every record model in the schema.
    """
    targets = []
    for model in (models if models is not None else ALL_RECORD_MODELS):
        if hasattr(model, id_column) and hasattr(model, name_column):
            targets.append(model)
    if not targets:
        return

    with db_engine.get_session() as session:
        for model in targets:
            session.execute(
                model.__table__.update()
                .where(getattr(model, id_column) == entity_id)
                .values({name_column: new_name})
            )
