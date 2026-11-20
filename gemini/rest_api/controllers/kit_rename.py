"""Rename a platform or a sensor of data already in the app (administrators).

    POST /api/kit_rename          {experiment, field, old, new, site?, dry_run?}  → {task_id}
    GET  /api/kit_rename/{task}   → where it stands, and what it found or did

Moves the data uploaded under another name ("P4", "Amiga") to the name new
uploads use ("Drone", "Rover"), so both meet in the same folders and runs
(gemini.api.kit_rename). In order, so a failure never leaves a record pointing
at nothing:

  1. every file under the old name is copied to its new path (in storage);
  2. in one transaction: the file records, the upload datasets, the plot
     boundaries saved per folder, the Process tab's runs and the jobs' records;
     the new name's platform/sensor is created for the experiment;
  3. the old copies are deleted.

A dry run (the default) only counts. Running it again finishes a move that
stopped part way: files already at their new path (same size) are not copied
again.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from litestar import Response
from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers import get, post
from sqlalchemy import text

from gemini.api.base import minio_storage_config, minio_storage_provider
from gemini.api.kit_rename import ROOTS, Rename, new_path, rewrite_json
from gemini.api.user import User
from gemini.db.core.base import db_engine
from gemini.rest_api.dependencies import require_superuser
from gemini.rest_api.models import RESTAPIError

logger = logging.getLogger(__name__)

_TASKS: dict[str, dict] = {}
_LOCK = threading.Lock()
_COPY_LIMIT = 5 * 1024 ** 3        # one copy request up to 5 GiB; larger files are streamed
COPY_THREADS = 4                   # below the storage client's connection pool


def _set(task: dict, **kw: Any) -> None:
    with _LOCK:
        task.update(kw)
        task["updated"] = time.time()


def _objects(r: Rename) -> list[tuple[str, str, int]]:
    """(old key, new key, size) of every file under the old name."""
    client, bucket = minio_storage_provider.client, minio_storage_config.bucket_name
    out = []
    for root in ROOTS:
        years = [o.object_name for o in client.list_objects(bucket, prefix=f"{root}/", recursive=False) if o.is_dir]
        for year in years:
            prefix = f"{year}{r.experiment}/" + (f"{r.site}/" if r.site else "")
            for o in client.list_objects(bucket, prefix=prefix, recursive=True):
                if o.is_dir:
                    continue
                n = new_path(o.object_name, r)
                if n:
                    out.append((o.object_name, n, int(o.size or 0)))
    return out


def _copy(src: str, dst: str, size: int) -> str:
    from minio.commonconfig import CopySource

    client, bucket = minio_storage_provider.client, minio_storage_config.bucket_name
    try:
        st = client.stat_object(bucket, dst)
    except Exception:
        st = None                                 # not there yet
    if st is not None:
        if int(st.size or 0) == size:
            return "there"                        # copied by an earlier run
        raise RuntimeError(f"{dst} exists already with another size: not overwritten")
    if size > _COPY_LIMIT:
        # Over one copy request's limit: streamed through in parts (this storage refuses a
        # composed copy of a single large file), never held whole in memory.
        resp = client.get_object(bucket, src)
        try:
            client.put_object(bucket, dst, resp, length=size, part_size=64 * 1024 * 1024)
        finally:
            resp.close()
            resp.release_conn()
    else:
        client.copy_object(bucket, dst, CopySource(bucket, src))
    return "copied"


def _documents(session, r: Rename, apply: bool) -> dict:
    """Records naming the old paths or name; rewritten when ``apply``. Counts per kind."""
    counts = {"datasets": 0, "plot_boundary_versions": 0, "process_runs_and_more": 0, "jobs": 0}
    like = f"%{r.experiment}%"

    rows = session.execute(text(
        "SELECT d.id, d.dataset_info FROM gemini.datasets d "
        "JOIN gemini.experiment_datasets ed ON ed.dataset_id = d.id "
        "JOIN gemini.experiments e ON e.id = ed.experiment_id WHERE e.experiment_name = :exp"),
        {"exp": r.experiment}).all()
    for did, info in rows:
        info = info or {}
        # A dataset's info says where it belongs (site, platform…) but not the experiment.
        new, n = rewrite_json({**info, "experiment": r.experiment}, r)
        new.pop("experiment", None)
        if n:
            counts["datasets"] += 1
            if apply:
                session.execute(text("UPDATE gemini.datasets SET dataset_info = CAST(:i AS JSONB) WHERE id = :id"),
                                {"i": json.dumps(new), "id": did})

    rows = session.execute(text(
        "SELECT id, directory, state_snapshot FROM gemini.plot_geometry_versions WHERE directory LIKE :like"),
        {"like": like}).all()
    for vid, directory, snap in rows:
        nd = new_path(directory, r)
        ns, n = rewrite_json(snap or {}, r)
        if nd or n:
            counts["plot_boundary_versions"] += 1
            if apply:
                session.execute(text("UPDATE gemini.plot_geometry_versions SET directory = :d, "
                                     "state_snapshot = CAST(:s AS JSONB) WHERE id = :id"),
                                {"d": nd or directory, "s": json.dumps(ns), "id": vid})

    rows = session.execute(text("SELECT id, doc FROM gemini.process_entities WHERE doc::text LIKE :like"),
                           {"like": like}).all()
    for eid, doc in rows:
        nd, n = rewrite_json(doc or {}, r)
        if n:
            counts["process_runs_and_more"] += 1
            if apply:
                session.execute(text("UPDATE gemini.process_entities SET doc = CAST(:d AS JSONB) WHERE id = :id"),
                                {"d": json.dumps(nd), "id": eid})

    rows = session.execute(text("SELECT id, parameters, result FROM gemini.jobs "
                                "WHERE parameters::text LIKE :like OR result::text LIKE :like"),
                           {"like": like}).all()
    for jid, params, result in rows:
        np_, n1 = rewrite_json(params or {}, r)
        nr, n2 = rewrite_json(result or {}, r)
        if n1 or n2:
            counts["jobs"] += 1
            if apply:
                session.execute(text("UPDATE gemini.jobs SET parameters = CAST(:p AS JSONB), "
                                     "result = CAST(:r AS JSONB) WHERE id = :id"),
                                {"p": json.dumps(np_), "r": json.dumps(nr), "id": jid})
    return counts


def _ensure_new_name(r: Rename) -> None:
    """The new platform (or sensor) exists for the experiment, as an upload would make it."""
    if r.field == "platform":
        from gemini.api.sensor_platform import SensorPlatform

        SensorPlatform.create(sensor_platform_name=r.new, experiment_name=r.experiment)
    else:
        from gemini.api.sensor import Sensor

        Sensor.create(sensor_name=r.new, experiment_name=r.experiment)


def _run(task: dict, r: Rename, dry: bool) -> None:
    try:
        _set(task, stage="listing files")
        moves = _objects(r)
        bucket = minio_storage_config.bucket_name
        with db_engine.get_session() as session:
            file_rows = 0
            for i in range(0, len(moves), 1000):
                keys = [m[0] for m in moves[i:i + 1000]]
                file_rows += session.execute(text(
                    "SELECT count(*) FROM gemini.experiment_files WHERE bucket = :b AND object_name = ANY(:k)"),
                    {"b": bucket, "k": keys}).scalar() or 0
            counts = _documents(session, r, apply=False)
        _set(task, files=len(moves), bytes=sum(m[2] for m in moves), file_records=file_rows, records=counts,
             examples=[f"{a} → {b}" for a, b, _ in moves[:3]])
        if dry:
            _set(task, stage="done", state="done (dry run: nothing changed)")
            return

        _set(task, stage="copying files", copied=0)
        done = 0
        # Few at a time: a copy request is signed when made, and one queued behind others for a
        # free connection to storage (several GB each) can be refused as too old.
        with ThreadPoolExecutor(COPY_THREADS) as pool:
            for _ in pool.map(lambda m: _copy(*m), moves):
                done += 1
                if done % 500 == 0:
                    _set(task, copied=done)
        _set(task, copied=done, stage="updating records")
        with db_engine.get_session() as session:
            for a, b, _ in moves:
                session.execute(text("UPDATE gemini.experiment_files SET object_name = :n "
                                     "WHERE bucket = :bk AND object_name = :o"), {"n": b, "o": a, "bk": bucket})
            _documents(session, r, apply=True)
            session.commit()
        _ensure_new_name(r)
        _set(task, stage="removing the old copies")
        client = minio_storage_provider.client
        with ThreadPoolExecutor(16) as pool:
            list(pool.map(lambda m: client.remove_object(bucket, m[0]), moves))
        _set(task, stage="done", state="done")
    except Exception as e:                      # noqa: BLE001 — reported on the task
        logger.exception("kit rename failed")
        _set(task, stage="failed", state="failed", error=str(e)[:500])


class KitRenameController(Controller):
    dependencies = {"superuser": Provide(require_superuser, sync_to_thread=True)}

    @post(sync_to_thread=True, status_code=200)
    def start(self, superuser: User, data: dict) -> Response:
        try:
            r = Rename(experiment=str(data.get("experiment") or "").strip(),
                       field=str(data.get("field") or "").strip(),
                       old=str(data.get("old") or "").strip(), new=str(data.get("new") or "").strip(),
                       site=(str(data["site"]).strip() or None) if data.get("site") else None)
        except ValueError as e:
            return Response(content=RESTAPIError(error="Bad rename", error_description=str(e)), status_code=400)
        dry = data.get("dry_run", True) is not False
        tid = uuid.uuid4().hex[:12]
        task = {"task_id": tid, "rename": r.__dict__, "dry_run": dry, "state": "running", "stage": "starting",
                "started": time.time(), "by": str(superuser.email)}
        with _LOCK:
            _TASKS[tid] = task
        logger.info("kit rename %s: %s %s → %s in %s%s", tid, r.field, r.old, r.new, r.experiment,
                    " (dry run)" if dry else "")
        threading.Thread(target=_run, args=(task, r, dry), daemon=True).start()
        return Response(content={"task_id": tid}, status_code=200)

    @get(path="/{task_id:str}", sync_to_thread=False)
    def state(self, superuser: User, task_id: str) -> Response:
        task: Optional[dict] = _TASKS.get(task_id)
        if task is None:
            return Response(content=RESTAPIError(error="Not found", error_description="no such rename"),
                            status_code=404)
        with _LOCK:
            return Response(content=dict(task), status_code=200)
