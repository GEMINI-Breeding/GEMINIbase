"""Carry out an import plan (tier 1): create each upload's entities and
dataset through the REST API — the same calls the app's uploader makes
(frontend useUploadScope / datasetForUpload) — copy its files into storage,
and register them (/api/files/register_batch, as the extraction workers do).

Re-running is safe and resumes an interrupted import: entities and datasets
are found before they're created (a dataset's name is derived from the old
upload's id), a file already in storage with the same size is not copied
again, and registration is idempotent.

The old install is only ever read (plan.py lists it; this opens its files
for reading); the caller mounts it read-only as well.
"""
from __future__ import annotations

import logging
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from gemini.importers.gemi_legacy.plan import SHORT_ID, ImportPlan, UploadPlan

logger = logging.getLogger(__name__)

# Sensor classification ids the uploader sends for Image Data
# (UploadList.tsx): type RGB=1 / Thermal=3, data type Image=4, format JPEG=8.
SENSOR_RGB, SENSOR_THERMAL, DATA_IMAGE, FORMAT_JPEG = 1, 3, 4, 8
THERMAL_NAME = re.compile(r"thermal|flir|boson|\bir\b|lwir", re.I)
REGISTER_BATCH = 500
# Upload types whose form has platform + sensor (config/dataTypes.ts).
WITH_PLATFORM = {"Image Data", "Ardupilot Logs", "Synced Metadata", "Orthomosaic", "Orthomosaic DEM"}


class LegacyImportError(RuntimeError):
    """A REST call the import needed failed."""


def dataset_name(upload: UploadPlan) -> str:
    """Like the uploader's autoDatasetName ({experiment}__{type}__{date}__
    {time}__{tail}), with the old upload's time and id so it's stable."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "", upload.data_type)
    try:
        when = datetime.fromisoformat((upload.created_at or "").replace("Z", "+00:00"))
        stamp = when.strftime("%Y%m%d__%H%M%S")
    except ValueError:
        stamp = "00000000__000000"
    return f"{upload.experiment}__{slug}__{stamp}__{upload.upload_id.replace('-', '')[:8]}"


class Api:
    """The REST calls the uploader makes, over a worker session."""

    def __init__(self, http):
        self.http = http
        self._cache: dict[tuple, dict] = {}

    def _json(self, resp) -> Any:
        if resp.status_code >= 400:
            raise LegacyImportError(f"{resp.request.method} {resp.url}: {resp.status_code} {resp.text[:300]}")
        return resp.json() if resp.content else None

    def _find(self, route: str, params: dict, name_key: str, name: str) -> Optional[dict]:
        resp = self.http.get(route, params=params)
        if resp.status_code == 404:
            return None
        rows = self._json(resp) or []
        if isinstance(rows, dict):
            rows = [rows]
        return next((r for r in rows if r.get(name_key) == name), None)

    def find_or_create(self, route: str, name_key: str, name: str,
                       experiment: Optional[str] = None, extra: Optional[dict] = None) -> dict:
        key = (route, name, experiment)
        if key in self._cache:
            return self._cache[key]
        params = {name_key: name, **({"experiment_name": experiment} if experiment else {})}
        row = self._find(route, params, name_key, name)
        if row is None:
            row = self._json(self.http.post(route, json={**params, **(extra or {})}))
        self._cache[key] = row
        return row

    def experiment(self, name: str) -> dict:
        row = self.find_or_create("/api/experiments", "experiment_name", name)
        # So it appears in this account's experiment list (best-effort, as
        # the uploader does).
        try:
            self.http.post("/api/users/me/experiments", json={"experiment_id": str(row["id"])})
        except Exception as exc:  # noqa: BLE001
            logger.warning("couldn't associate experiment %s: %s", name, exc)
        return row

    def dataset(self, name: str, experiment: str, info: dict, collection_date: Optional[str] = None) -> dict:
        key = ("/api/datasets", name, experiment)
        if key in self._cache:
            return self._cache[key]
        row = self._find("/api/datasets", {"dataset_name": name}, "dataset_name", name)
        if row is None:
            body = {"dataset_name": name, "experiment_name": experiment, "dataset_info": info}
            if collection_date:
                body["collection_date"] = collection_date
            row = self._json(self.http.post("/api/datasets", json=body))
        self._cache[key] = row
        return row

    def register(self, experiment_id: str, dataset_id: Optional[str], bucket: str, keys: list[str]) -> None:
        for i in range(0, len(keys), REGISTER_BATCH):
            self._json(self.http.post("/api/files/register_batch", json={
                "experiment_id": experiment_id, "dataset_id": dataset_id,
                "files": [{"bucket": bucket, "object_name": k} for k in keys[i:i + REGISTER_BATCH]],
            }))


def _iso_date(date: str) -> Optional[str]:
    """The old upload's date (free text, normally YYYY-MM-DD) as the
    dataset's collection date, if it is one."""
    try:
        return datetime.strptime(date.strip(), "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00")
    except (ValueError, AttributeError):
        return None


def _stored_size(storage, bucket: str, key: str) -> Optional[int]:
    try:
        return storage.stat_object(bucket, key).size
    except Exception:  # noqa: BLE001 — not there (or unreadable): copy it
        return None


def import_upload(upload: UploadPlan, data_dir: Path, api: Api,
                  storage, bucket: str, on_file: Callable[[int], None]) -> dict:
    """One old upload → its entities, dataset and files. Returns counts."""
    exp = api.experiment(upload.experiment)
    exp_id = str(exp["id"])
    E = upload.experiment
    if upload.season:
        api.find_or_create("/api/seasons", "season_name", upload.season, E)
    if upload.site:
        api.find_or_create("/api/sites", "site_name", upload.site, E)
    if upload.population:
        api.find_or_create("/api/populations", "population_name", upload.population, E)
    thermal = False
    if upload.data_type in WITH_PLATFORM and upload.platform:
        api.find_or_create("/api/sensor_platforms", "sensor_platform_name", upload.platform, E)
        if upload.sensor:
            extra = {"sensor_platform_name": upload.platform}
            if upload.data_type == "Image Data":
                thermal = bool(THERMAL_NAME.search(upload.sensor))
                extra.update(sensor_type_id=SENSOR_THERMAL if thermal else SENSOR_RGB,
                             sensor_data_type_id=DATA_IMAGE, sensor_data_format_id=FORMAT_JPEG)
            api.find_or_create("/api/sensors", "sensor_name", upload.sensor, E, extra)

    ds = api.dataset(dataset_name(upload), E, {
        "files_prefix": f"{bucket}/{upload.source_dir}",
        "bucket": bucket,
        "data_type_label": upload.data_type,
        "imported_from": "GEMI (previous desktop app)",
        "legacy_upload_id": upload.upload_id,
    }, collection_date=_iso_date(upload.date))
    ds_id = str(ds["id"])
    short_id = ds_id.replace("-", "")[:8]

    copied = skipped = 0
    keys = []
    for f in upload.files:
        key = f.target.replace(SHORT_ID, short_id)
        keys.append(key)
        if _stored_size(storage, bucket, key) == f.size:
            skipped += 1
        else:
            # The type a browser upload records (image/jpeg, text/csv, …).
            ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
            storage.fput_object(bucket, key, str(data_dir / f.source), content_type=ctype)
            copied += 1
        on_file(f.size)
    api.register(exp_id, ds_id, bucket, keys)
    return {"experiment_id": exp_id, "dataset_id": ds_id, "copied": copied,
            "already_there": skipped, "thermal": thermal}


def run_import(plan: ImportPlan, data_dir: str | Path,
               http, storage, bucket: str,
               progress: Callable[[float, str], None] = lambda p, m: None,
               cancelled: Callable[[], bool] = lambda: False) -> dict:
    """Import every plannable upload. An upload that fails is reported and
    the rest continue; re-running picks up where it stopped."""
    data_dir = Path(data_dir)
    api = Api(http)
    todo = plan.to_import
    total = max(sum(u.bytes for u in todo), 1)
    done = {"bytes": 0}
    results, failed = [], []

    def on_file(size: int) -> None:
        done["bytes"] += size
        progress(100 * done["bytes"] / total, f"Copied {done['bytes'] / 1e9:.1f} of {total / 1e9:.1f} GB")

    for n, upload in enumerate(todo):
        if cancelled():
            break
        progress(100 * done["bytes"] / total, f"Upload {n + 1} of {len(todo)}: {upload.source_dir}")
        try:
            r = import_upload(upload, data_dir, api, storage, bucket, on_file)
            results.append({"upload_id": upload.upload_id, "path": upload.source_dir, **r})
        except Exception as exc:  # noqa: BLE001 — report it, carry on with the rest
            logger.exception("import of %s failed", upload.source_dir)
            failed.append({"upload_id": upload.upload_id, "path": upload.source_dir, "error": str(exc)})
    return {
        "imported": results,
        "failed": failed,
        "skipped": plan.summary()["skipped"],
        "cancelled": cancelled(),
        "thermal_uploads": [r["path"] for r in results if r.get("thermal")],
    }
