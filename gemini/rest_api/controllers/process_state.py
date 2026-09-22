"""
Process workspaces, pipelines and runs, stored server-side.

These used to live only in the browser's localStorage, so clearing site
data lost every run's history and nobody else could see them. The app
keeps each one as a JSON document; this controller stores, lists and
deletes those documents. It deliberately does not interpret them — the
frontend owns their shape — beyond linking each to its parent:

    workspace  ←  pipeline (doc.workspaceId)  ←  run (doc.pipelineId)

with ON DELETE CASCADE, so deleting a workspace removes its pipelines and
runs, exactly as the browser store did. Shared by every user of the
instance, like the experiments they refer to.

    GET    /api/process_state                 → {workspaces, pipelines, runs}
    PUT    /api/process_state/{kind}/{id}     body {"doc": {...}}  (upsert)
    DELETE /api/process_state/{kind}/{id}     (cascades)
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from litestar import Request, Response
from litestar.controller import Controller
from litestar.handlers import delete, get, put
from sqlalchemy import text

from gemini.db.core.base import db_engine
from gemini.rest_api.dependencies import provide_current_user
from gemini.rest_api.models import RESTAPIError

logger = logging.getLogger(__name__)

KINDS = {"workspace", "pipeline", "run"}
PARENT_FIELD = {"pipeline": "workspaceId", "run": "pipelineId"}


def _bad(error: str, desc: str, status: int = 400) -> Response:
    return Response(
        content=RESTAPIError(error=error, error_description=desc),
        status_code=status,
    )


def _uuid(value) -> Optional[str]:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


class ProcessStateController(Controller):

    @get(sync_to_thread=True)
    def list_state(self) -> dict:
        with db_engine.get_session() as session:
            rows = session.execute(
                text(
                    "SELECT kind, doc FROM gemini.process_entities "
                    "ORDER BY (doc->>'createdAt') NULLS LAST, id"
                )
            ).all()
        out: dict = {"workspaces": [], "pipelines": [], "runs": []}
        for kind, doc in rows:
            out[f"{kind}s"].append(doc)
        return out

    @put(path="/{kind:str}/{entity_id:str}", sync_to_thread=True)
    def upsert(self, request: Request, kind: str, entity_id: str, data: dict) -> Response:
        if kind not in KINDS:
            return _bad("Unknown kind", f"kind must be one of {sorted(KINDS)}")
        eid = _uuid(entity_id)
        if eid is None:
            return _bad("Bad id", "id must be a UUID")
        doc = data.get("doc") if isinstance(data, dict) else None
        if not isinstance(doc, dict):
            return _bad("Bad body", 'Body must be {"doc": {...}}')
        if _uuid(doc.get("id")) != eid:
            return _bad("Id mismatch", "doc.id must equal the id in the path")
        parent = None
        if kind in PARENT_FIELD:
            parent = _uuid(doc.get(PARENT_FIELD[kind]))
            if parent is None:
                return _bad("Missing parent", f"doc.{PARENT_FIELD[kind]} must be a UUID")
        user = provide_current_user(request)
        by = getattr(user, "email", None)
        try:
            with db_engine.get_session() as session:
                if parent is not None:
                    exists = session.execute(
                        text("SELECT 1 FROM gemini.process_entities WHERE id = :p"),
                        {"p": parent},
                    ).first()
                    if not exists:
                        return _bad(
                            "Parent not found",
                            f"{PARENT_FIELD[kind]} {parent} doesn't exist (deleted?)",
                            409,
                        )
                session.execute(
                    text(
                        """
                        INSERT INTO gemini.process_entities
                            (id, kind, parent_id, doc, updated_at, updated_by)
                        VALUES (:id, :kind, :parent, CAST(:doc AS JSONB), NOW(), :by)
                        ON CONFLICT (id) DO UPDATE
                           SET doc = EXCLUDED.doc,
                               parent_id = EXCLUDED.parent_id,
                               updated_at = NOW(),
                               updated_by = EXCLUDED.updated_by
                         WHERE gemini.process_entities.kind = EXCLUDED.kind
                        """
                    ),
                    {"id": eid, "kind": kind, "parent": parent, "doc": json.dumps(doc), "by": by},
                )
                session.commit()
        except Exception as e:
            logger.exception("process_state upsert failed")
            return _bad(str(e), "Could not save", 500)
        return Response(content={"id": eid, "kind": kind}, status_code=200)

    @delete(path="/{kind:str}/{entity_id:str}", sync_to_thread=True, status_code=200)
    def remove(self, kind: str, entity_id: str) -> dict:
        eid = _uuid(entity_id)
        if kind not in KINDS or eid is None:
            return {"deleted": 0}
        with db_engine.get_session() as session:
            n = session.execute(
                text(
                    "DELETE FROM gemini.process_entities WHERE id = :id AND kind = :kind"
                ),
                {"id": eid, "kind": kind},
            ).rowcount or 0
            session.commit()
        return {"deleted": int(n)}
