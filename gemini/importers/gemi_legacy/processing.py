"""Import the old app's processing (tiers 2–3): reference datasets,
workspaces / pipelines / runs, and each run's results, plus an archive
copy of everything the old app wrote outside Raw/ so nothing is lost.

Where things go (see merge_plan.md Phase 5 for the new app's side):
- reference dataset → its original file under ReferenceData/{E}/{L}/{P}/
  (with a dataset + registration, as the uploader does) and the parsed
  rows via /api/reference_data/upload
- workspace / pipeline / run → /api/process_state documents with the OLD
  ids, so re-importing updates rather than duplicates. Pipelines keep the
  old config (the app migrates old keys such as odm_preset itself).
- aerial run, in Processed/{season}/{E}/{L}/{P}/{date}/{platform}/{sensor}/:
  orthomosaic versions as odm_orthophoto-gemi-{ws}-v{N}.tif (+ odm_dsm-…,
  -Pyramid.tif) so the app lists them and pairs each with its DEM; plot
  boundary versions as plot-geometry versions (which create the plots),
  with the old app's identity keys (Plot/Tier/Bed/Label …) written as the
  canonical plot/row/col/accession; per-plot traits as trait records in a
  dataset per old trait record; cropped plot images as PlotImages/…
- ground run: plot markings as plot-geometry versions under
  Processed/{season}/{E}/{L}/{P}/PlotMarkings, stitch folders as
  AgRowStitch_v{N}/, cropped plot images as PlotImages/…
- archive: the old Intermediate/ and Processed/ trees, copied as they are
  to Imported/GEMI/…, registered to their experiment.

Re-running skips what's there: versions by name, datasets by name, files
by size, documents by id.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from gemini.importers.gemi_legacy.plan import plan_upload, season_of
from gemini.importers.gemi_legacy.reader import (
    LegacyDatabase,
    LegacyRun,
    norm_rel_path,
)
from gemini.importers.gemi_legacy.run import Api, _iso_date, _stored_size, dataset_name

logger = logging.getLogger(__name__)

ARCHIVE_ROOT = "Imported/GEMI"
# The old app's alternatives for plot identity (processing/plot_record_utils.py).
PLOT_KEYS = ("plot_id", "Plot", "plot", "id", "ID")
ROW_KEYS = ("Tier", "tier", "row", "ROW", "Row")
COL_KEYS = ("Bed", "bed", "col", "COL", "column", "COLUMN", "Column")
ACCESSION_KEYS = ("Label", "label", "accession", "Accession")


# ── Conversions (pure) ─────────────────────────────────────────────────────


def _first(props: dict, keys) -> Any:
    for k in keys:
        v = props.get(k)
        if v not in (None, ""):
            return v
    return None


def as_int(v: Any) -> Optional[int]:
    """'3', '3.0', 3.0 → 3; anything else → None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


def canonical_boundaries(fc: dict) -> dict:
    """The old boundary GeoJSON with each feature's identity written under
    the keys the new app reads (plot, row, col, accession). The original
    properties are kept."""
    out = {"type": "FeatureCollection", "features": []}
    for f in fc.get("features") or []:
        props = dict(f.get("properties") or {})
        plot, row, col = (as_int(_first(props, k)) for k in (PLOT_KEYS, ROW_KEYS, COL_KEYS))
        acc = _first(props, ACCESSION_KEYS)
        for k, v in (("plot", plot), ("row", row), ("col", col)):
            if v is not None:
                props[k] = v
        if acc is not None:
            props["accession"] = str(acc)
        out["features"].append({**f, "properties": props})
    return out


def selections_from_csv(text: str) -> list[dict]:
    """plot_borders_v{N}.csv rows → the new app's plot-marking selections
    (the old rows already have the same columns)."""
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        sel = {k: (row.get(k) or "") for k in ("start_image", "end_image", "direction")}
        sel["plot_id"] = as_int(row.get("plot_id")) if as_int(row.get("plot_id")) is not None else row.get("plot_id")
        for k in ("start_lat", "start_lon", "end_lat", "end_lon"):
            try:
                sel[k] = float(row[k]) if row.get(k) not in (None, "") else None
            except ValueError:
                sel[k] = None
        out.append(sel)
    return out


def ws_tag(name: str, ws_id: str) -> str:
    """A short, filename-safe tag telling one old workspace's copies apart."""
    slug = re.sub(r"[^A-Za-z0-9]+", "", name)[:12]
    return f"{slug or 'ws'}{ws_id.replace('-', '')[:4]}"


def _iso(ts: Optional[str]) -> str:
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00")).isoformat()
    except ValueError:
        return datetime(2000, 1, 1).isoformat()


# ── Planning (the dry run's counts) ───────────────────────────────────────


@dataclass
class ProcessingPlan:
    workspaces: int = 0
    pipelines: int = 0
    runs: int = 0
    ortho_versions: int = 0
    boundary_versions: int = 0
    trait_records: int = 0
    plot_markings: int = 0
    stitches: int = 0
    reference_datasets: int = 0
    archive_files: int = 0
    archive_bytes: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _archive_files(data_dir: Path) -> list[tuple[str, int]]:
    out = []
    for top in ("Intermediate", "Processed"):
        root = data_dir / top
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and not p.is_symlink():
                out.append((p.relative_to(data_dir).as_posix(), p.stat().st_size))
    return out


def plan_processing(db: LegacyDatabase, data_dir: str | Path) -> ProcessingPlan:
    data_dir = Path(data_dir)
    plan = ProcessingPlan()
    ws = {w.id for w in db.workspaces()}
    pipes = {p.id: p for p in db.pipelines() if p.workspace_id in ws}
    plan.workspaces, plan.pipelines = len(ws), len(pipes)
    runs = [r for r in db.runs() if r.pipeline_id in pipes]
    orphans = len(db.runs()) - len(runs)
    if orphans:
        plan.notes.append(f"{orphans} run(s) of deleted pipelines are only in the archive copy")
    plan.runs = len(runs)
    for r in runs:
        o = r.outputs
        plan.ortho_versions += len(_ortho_entries(o))
        plan.boundary_versions += len(o.get("plot_boundaries") or [])
        plan.plot_markings += len(o.get("plot_markings") or [])
        plan.stitches += len(o.get("stitchings") or [])
    run_ids = {r.id for r in runs}
    plan.trait_records = sum(1 for t in db.trait_records() if t.run_id in run_ids)
    plan.reference_datasets = len(db.reference_datasets())
    files = _archive_files(data_dir)
    plan.archive_files, plan.archive_bytes = len(files), sum(s for _, s in files)
    return plan


def _ortho_entries(outputs: dict) -> list[dict]:
    """Old `orthomosaics` list, or the pre-versioning flat keys as v1."""
    entries = [e for e in outputs.get("orthomosaics") or [] if isinstance(e, dict) and e.get("rgb")]
    if not entries and outputs.get("orthomosaic"):
        entries = [{"version": 1, "rgb": outputs["orthomosaic"], "dem": outputs.get("dem"), "name": None}]
    return entries


# ── Carrying it out ────────────────────────────────────────────────────────


class Copier:
    """Copy files from the old data folder into storage (skip same size)."""

    def __init__(self, data_dir: Path, storage, bucket: str, old_root: Optional[str]):
        self.data_dir, self.storage, self.bucket, self.old_root = data_dir, storage, bucket, old_root
        self.copied = 0

    def source(self, rel: Optional[str]) -> Optional[Path]:
        rel = norm_rel_path(rel, self.old_root)
        if not rel:
            return None
        p = self.data_dir / rel
        # Like plan._walk: a symlink out of the old data folder isn't followed.
        try:
            if not p.resolve().is_relative_to(self.data_dir.resolve()):
                return None
        except OSError:
            return None
        return p if p.is_file() else None

    def put_file(self, src: Path, key: str) -> None:
        if _stored_size(self.storage, self.bucket, key) == src.stat().st_size:
            return
        ctype = mimetypes.guess_type(key)[0] or "application/octet-stream"
        self.storage.fput_object(self.bucket, key, str(src), content_type=ctype)
        self.copied += 1

    def put_bytes(self, data: bytes, key: str, ctype: str) -> None:
        if _stored_size(self.storage, self.bucket, key) == len(data):
            return
        self.storage.put_object(self.bucket, key, io.BytesIO(data), len(data), content_type=ctype)
        self.copied += 1


class Importer:
    def __init__(self, db: LegacyDatabase, data_dir: Path, http, storage, bucket: str,
                 progress: Callable[[str], None]):
        self.db, self.data_dir, self.bucket = db, data_dir, bucket
        self.api = Api(http)
        self.http = http
        self.copier = Copier(data_dir, storage, bucket, db.old_data_root())
        self.progress = progress
        self.result: dict[str, Any] = {
            "workspaces": 0, "pipelines": 0, "runs": 0, "ortho_versions": 0,
            "boundary_versions": 0, "trait_datasets": 0, "plot_markings": 0, "stitches": 0,
            "reference_datasets": 0, "archive_files": 0, "failed": [], "notes": [],
        }
        self.uploads = {u.id: u for u in db.uploads()}
        # Loaded once (not per run): big databases have many plot records.
        self._trait_records: dict[str, list] = {}
        for t in db.trait_records():
            self._trait_records.setdefault(t.run_id, []).append(t)
        self._plot_records: dict[str, list] = {}
        for pr in db.plot_records():
            self._plot_records.setdefault(pr.trait_record_id, []).append(pr)

    # -- helpers --------------------------------------------------------
    def _json(self, resp):
        return self.api._json(resp)

    def _fail(self, what: str, exc: Exception) -> None:
        logger.exception("legacy import: %s failed", what)
        self.result["failed"].append({"path": what, "error": str(exc)})

    def _scope_of(self, run: LegacyRun) -> dict:
        up = self.uploads.get(run.file_upload_id or "")
        season = season_of(up) if up else (run.date.split("-")[0] if run.date else "")
        return {"season": season, "experiment": run.experiment, "site": run.location,
                "population": run.population, "date": run.date, "platform": run.platform,
                "sensor": run.sensor}

    def _processed(self, s: dict) -> str:
        return (f"Processed/{s['season']}/{s['experiment']}/{s['site']}/{s['population']}/"
                f"{s['date']}/{s['platform']}/{s['sensor']}/")

    def _accessions(self, names: set[str], experiment: str, population: str) -> None:
        for name in sorted(n for n in names if n):
            try:
                self.api.find_or_create("/api/accessions", "accession_name", name,
                                        extra={"population_name": population} if population else None)
            except Exception as exc:  # noqa: BLE001 — plots still import, just unlinked
                logger.warning("accession %s: %s", name, exc)

    def _versions(self, directory: str) -> dict[str, int]:
        rows = self._json(self.http.post("/api/plot_geometry/versions/list", json={"directory": directory})) or []
        return {r.get("name"): r.get("version") for r in rows}

    def _save_version(self, directory: str, name: str, snapshot: dict) -> int:
        existing = self._versions(directory)
        if name in existing:
            return existing[name]
        r = self._json(self.http.post("/api/plot_geometry/versions/save",
                                      json={"directory": directory, "name": name, "state_snapshot": snapshot}))
        return int(r["version"])

    # -- reference data ---------------------------------------------------
    def reference_datasets(self) -> None:
        plots_by_ds: dict[str, list] = {}
        for p in self.db.reference_plots():
            plots_by_ds.setdefault(p.dataset_id, []).append(p)
        # Keyed by the old dataset's id, not its name: names aren't unique
        # (two old "Yield" datasets, or one the user made here, must not
        # stand in for each other).
        done = {
            (d.get("dataset_info") or {}).get("legacy_reference_id")
            for d in (self._json(self.http.get("/api/reference_data")) or [])
        }
        for ds in self.db.reference_datasets():
            try:
                if ds.id in done:
                    continue
                self.progress(f"Reference data: {ds.name}")
                original = None
                src = self.copier.source(f"reference_data/{ds.id}/{ds.original_filename}") if ds.original_filename else None
                if src and ds.experiment:
                    exp = self.api.experiment(ds.experiment)
                    original = (f"ReferenceData/{ds.experiment or 'Experiment'}/{ds.location or 'Location'}/"
                                f"{ds.population or 'Population'}/{ds.original_filename}")
                    self.copier.put_file(src, original)
                    rds = self.api.dataset(
                        f"{ds.experiment}__ReferenceData__{_stamp(ds.created_at)}__{ds.id.replace('-', '')[:8]}",
                        ds.experiment, {"files_prefix": f"{self.bucket}/{original}", "bucket": self.bucket,
                                        "data_type_label": "Reference Data",
                                        "imported_from": "GEMI (previous desktop app)"})
                    self.api.register(str(exp["id"]), str(rds["id"]), self.bucket, [original])
                # The parsed rows, as a clean CSV with an identity mapping.
                traits = list(ds.trait_columns)
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["plot_id", "row", "col", "accession", *traits])
                for p in plots_by_ds.get(ds.id, []):
                    w.writerow([p.plot_id, p.row or "", p.col or "", p.accession or "",
                                *[p.traits.get(t, "") for t in traits]])
                mapping = {"plot_id": "plot_id", "row": "row", "col": "col", "accession": "accession",
                           **{t: t for t in traits}}
                params = {"name": ds.name, "column_mapping_json": json.dumps(mapping),
                          "legacy_reference_id": ds.id}
                for k, v in (("experiment", ds.experiment), ("location", ds.location),
                             ("population", ds.population), ("date", _iso_date(ds.date or "") and ds.date),
                             ("original_object", original)):
                    if v:
                        params[k] = v
                self._json(self.http.post("/api/reference_data/upload", params=params,
                                          files={"file": (f"{ds.name}.csv", buf.getvalue().encode(), "text/csv")}))
                self.result["reference_datasets"] += 1
            except Exception as exc:  # noqa: BLE001
                self._fail(f"reference dataset {ds.name}", exc)

    # -- workspaces / pipelines ---------------------------------------------
    def _put_doc(self, kind: str, doc: dict) -> None:
        self._json(self.http.put(f"/api/process_state/{kind}/{doc['id']}", json={"doc": doc}))

    def workspaces_and_pipelines(self) -> dict[str, Any]:
        ws = {w.id: w for w in self.db.workspaces()}
        for w in ws.values():
            self._put_doc("workspace", {"id": w.id, "name": w.name, "description": w.description or "",
                                        "createdAt": _iso(w.created_at)})
            self.result["workspaces"] += 1
        pipes = {}
        for p in self.db.pipelines():
            if p.workspace_id not in ws:
                continue
            self._put_doc("pipeline", {"id": p.id, "workspaceId": p.workspace_id, "name": p.name,
                                       "type": p.type if p.type in ("aerial", "ground") else "aerial",
                                       "params": p.config, "createdAt": _iso(p.created_at)})
            pipes[p.id] = p
            self.result["pipelines"] += 1
        return {"workspaces": ws, "pipelines": pipes}

    # -- runs -----------------------------------------------------------------
    def run(self, run: LegacyRun, pipe, ws) -> None:
        s = self._scope_of(run)
        E = s["experiment"]
        exp = self.api.experiment(E)
        ids = {
            "experimentId": str(exp["id"]),
            "seasonId": str(self.api.find_or_create("/api/seasons", "season_name", s["season"], E)["id"]),
            "siteId": str(self.api.find_or_create("/api/sites", "site_name", s["site"], E)["id"]),
            "populationId": str(self.api.find_or_create("/api/populations", "population_name",
                                                         s["population"], E)["id"]),
        }
        short_ids = []
        up = self.uploads.get(run.file_upload_id or "")
        if up:
            up_name = dataset_name(plan_upload(up, self.data_dir))
            ds = self.api._find("/api/datasets", {"dataset_name": up_name, "experiment_name": up.experiment},
                                "dataset_name", up_name)
            if ds:
                short_ids.append(str(ds["id"]).replace("-", "")[:8])
        directory = self._processed(s)
        tag = ws_tag(ws.name, ws.id)
        steps: dict[str, dict] = {}
        if pipe.type == "ground":
            self._ground(run, s, directory, steps, short_ids)
        else:
            self._aerial(run, s, directory, tag, steps)
        status = {"completed": "completed", "failed": "failed"}.get(run.status, "draft")
        name = f"{run.date} {run.platform}/{run.sensor}"
        self._put_doc("run", {
            "id": run.id, "pipelineId": pipe.id, "workspaceId": ws.id, "name": name,
            "scope": ids,
            "uploadScope": {"year": s["season"], "experiment": E, "location": s["site"],
                            "population": s["population"], "date": s["date"], "platform": s["platform"],
                            "sensor": s["sensor"], "experimentId": ids["experimentId"],
                            **({"datasetShortIds": short_ids} if short_ids else {})},
            "status": status, "steps": steps,
            "createdAt": _iso(run.created_at), "updatedAt": _iso(run.completed_at or run.created_at),
        })
        self.result["runs"] += 1

    def _part(self, what: str, fn: Callable[[], Any]) -> Any:
        """Run one part of a run's import; a failure is recorded (it shows
        under "Couldn't import", and re-importing retries it) without
        abandoning the rest of the run."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            self._fail(what, exc)
            return None

    def _aerial(self, run: LegacyRun, s: dict, directory: str, tag: str, steps: dict) -> None:
        o = run.outputs
        now = _iso(run.completed_at or run.created_at)
        label = f"{run.date} {run.platform}/{run.sensor}"

        # Orthomosaic versions.
        versions = []
        for e in sorted(_ortho_entries(o), key=lambda e: e.get("version") or 0):
            v = self._part(f"{label}: orthomosaic v{e.get('version') or 1}",
                           lambda e=e: self._ortho_version(e, directory, tag))
            if v:
                versions.append(v)
                self.result["ortho_versions"] += 1
        if versions:
            steps["data_sync"] = {"status": "skipped", "jobIds": []}
            steps["orthomosaic"] = {"status": "completed", "jobIds": [], "completedAt": now,
                                    "outputs": {"versions": versions}}

        # Plot boundary versions (+ plots).
        features_by_version: dict[int, dict] = {}
        accessions: set[str] = set()
        for b in sorted(o.get("plot_boundaries") or [], key=lambda b: b.get("version") or 0):
            src = self.copier.source(b.get("geojson_path"))
            if not src:
                self._fail(f"{label}: boundary v{b.get('version')}",
                           FileNotFoundError(f"{b.get('geojson_path')} is not in the data folder"))
                continue
            fc = self._part(f"{label}: boundary v{b.get('version')}",
                            lambda src=src: canonical_boundaries(json.loads(src.read_text())))
            if fc is None:
                continue
            features_by_version[b.get("version") or 0] = fc
            accessions |= {str(f["properties"]["accession"]) for f in fc["features"]
                           if f["properties"].get("accession")}
            no_plot = sum(1 for f in fc["features"] if f["properties"].get("plot") is None)
            if no_plot:
                self.result["notes"].append(
                    f"{label}: {no_plot} plot(s) in boundary \"{b.get('name') or b.get('version')}\" have no "
                    "whole-number plot id, so no plot was created for them (the shapes are kept in the version)"
                )
        self._accessions(accessions, s["experiment"], s["population"])
        new_versions: dict[int, tuple[int, str]] = {}
        for b in sorted(o.get("plot_boundaries") or [], key=lambda b: b.get("version") or 0):
            v = b.get("version") or 0
            if v not in features_by_version:
                continue
            name = b.get("name") or f"v{v} (GEMI)"
            new_v = self._part(f"{label}: boundary \"{name}\"", lambda v=v, name=name: self._save_version(
                directory, name, {"boundaries": features_by_version[v], "created_from": "import"}))
            if new_v is not None:
                new_versions[v] = (new_v, name)
                self.result["boundary_versions"] += 1
        active_old = o.get("active_plot_boundary_version") or (max(new_versions) if new_versions else None)
        if active_old in new_versions:
            nv, nname = new_versions[active_old]
            activated = self._part(f"{label}: activating boundary \"{nname}\"", lambda: self._json(
                self.http.post("/api/plot_geometry/versions/activate",
                               json={"directory": directory, "version": nv})) or {})
            if activated is not None:
                steps["plot_boundary_prep"] = {"status": "completed", "jobIds": [], "completedAt": now,
                                               "outputs": {"activeVersion": nv, "activeVersionName": nname}}

        # Traits: one dataset per old trait record.
        acc_by_plot = {}
        for fc in features_by_version.values():
            for f in fc["features"]:
                p = f["properties"]
                if p.get("plot") is not None and p.get("accession"):
                    acc_by_plot[str(p["plot"])] = str(p["accession"])
        for tr in self._trait_records.get(run.id, []):
            rows = self._plot_records.get(tr.id, [])
            if not rows:
                continue
            done = self._part(f"{label}: plot traits v{tr.version}", lambda tr=tr, rows=rows: self._traits(tr, rows, s))
            if done is None:
                continue  # failed: recorded, and retried by the next import
            if done:
                self.result["trait_datasets"] += 1
            steps["trait_extraction"] = {"status": "completed", "jobIds": [], "completedAt": now}

        # Cropped plot images.
        self._part(f"{label}: plot images", lambda: self._plot_images(o.get("cropped_images"), directory, acc_by_plot))

    def _ortho_version(self, e: dict, directory: str, tag: str) -> Optional[dict]:
        n = e.get("version") or 1
        base = f"odm_orthophoto-gemi-{tag}-v{n}"
        rgb = self.copier.source(e.get("rgb"))
        if not rgb:
            raise FileNotFoundError(f"{e.get('rgb')} is not in the data folder")
        self.copier.put_file(rgb, f"{directory}{base}.tif")
        dem = self.copier.source(e.get("dem"))
        if dem:
            self.copier.put_file(dem, f"{directory}odm_dsm-gemi-{tag}-v{n}.tif")
        pyr = self.copier.source(e.get("pyramid"))
        if pyr:
            self.copier.put_file(pyr, f"{directory}{base}-Pyramid.tif")
        return {"filename": f"{base}.tif", "path": f"{self.bucket}/{directory}{base}.tif",
                "label": e.get("name") or f"v{n} (GEMI)", "source": "RUN_ODM",
                "createdAt": _iso(e.get("created_at"))}

    def _traits(self, tr, rows, s: dict) -> bool:
        """One old trait record → a dataset of trait records. The dataset
        is marked import_complete only after every record is in; a dataset
        found without the mark is an interrupted import, so it's deleted
        (which sweeps its partial records) and imported again. Returns
        False if it was already complete."""
        E = s["experiment"]
        name = (f"Traits from GEMI · {E} · {s['season']}/{s['site']}/{s['population']} · "
                f"{s['date']} {s['platform']}/{s['sensor']} · v{tr.version}")
        found = self.api._find("/api/datasets", {"dataset_name": name, "experiment_name": E}, "dataset_name", name)
        if found and (found.get("dataset_info") or {}).get("import_complete"):
            return False
        if found:
            self._json(self.http.delete(f"/api/datasets/id/{found['id']}"))
            self.api._cache.pop(("/api/datasets", name, E), None)
        info = {"source": "GEMI import", "legacy_trait_record_id": tr.id}
        ds = self.api.dataset(name, E, info, collection_date=_iso_date(s["date"]))
        trait_names = tr.trait_columns or sorted({k for r in rows for k in r.traits})
        stamp = f"{s['date']}T00:00:00" if _iso_date(s["date"]) else None
        unlinked = 0
        for t in trait_names:
            trait = self.api.find_or_create("/api/traits", "trait_name", t, E,
                                            {"trait_units": "", "trait_level_id": 2})
            recs = []
            for r in rows:
                v = r.traits.get(t)
                if v is None:
                    continue  # no value for this trait on this plot
                plot = as_int(r.plot_id)
                rec = {"trait_value": v,
                       "record_info": {"source": "GEMI import", "legacy_trait_record_id": tr.id,
                                       "legacy_plot_id": r.plot_id,
                                       **({"legacy_accession": r.accession} if r.accession else {})},
                       **({"timestamp": stamp} if stamp else {})}
                # Every record carries the plot keys (None when unlinked): a
                # bulk insert needs the same keys in every row.
                # (Row/col only go with a plot number: the API refuses them
                # alone. Unlinked values keep them in record_info.)
                linked = plot is not None
                rec.update(plot_number=plot, plot_row_number=as_int(r.row) if linked else None,
                           plot_column_number=as_int(r.col) if linked else None)
                if plot is None:
                    # Plot numbers are integers here; "101A" can't be one.
                    # Keep the value, unlinked, with the old plot id and
                    # row/col in record_info — never drop it.
                    rec["record_info"].update(legacy_row=r.row, legacy_col=r.col)
                    unlinked += 1
                recs.append(rec)
            for i in range(0, len(recs), 500):
                self._json(self.http.post(f"/api/traits/id/{trait['id']}/records/bulk", json={
                    "records": recs[i:i + 500], "experiment_name": E, "season_name": s["season"],
                    "site_name": s["site"], "population_name": s["population"], "dataset_name": name,
                    **({"collection_date": stamp} if stamp else {}),
                }))
        self._json(self.http.patch(f"/api/datasets/id/{ds['id']}",
                                   json={"dataset_info": {**info, "import_complete": True}}))
        if unlinked:
            self.result["notes"].append(
                f"{unlinked} trait value(s) in \"{name}\" kept without a plot link: their old plot "
                "ids aren't whole numbers (the old id, row and column are kept with each value)"
            )
        return True

    def _plot_images(self, cropped_dir: Optional[str], directory: str, acc_by_plot: dict) -> None:
        rel = norm_rel_path(cropped_dir, self.copier.old_root)
        if not rel or not (self.data_dir / rel).is_dir():
            return
        for p in sorted((self.data_dir / rel).glob("plot_*.png")):
            plot = p.stem[len("plot_"):]
            acc = re.sub(r"[ /]", "_", acc_by_plot.get(plot, "unknown"))
            self.copier.put_file(p, f"{directory}PlotImages/plot_{plot}_accession_{acc}.png")

    def _ground(self, run: LegacyRun, s: dict, directory: str, steps: dict, short_ids: list) -> None:
        o = run.outputs
        now = _iso(run.completed_at or run.created_at)
        label = f"{run.date} {run.platform}/{run.sensor}"
        marks_dir = f"Processed/{s['season']}/{s['experiment']}/{s['site']}/{s['population']}/PlotMarkings"
        track_root = (f"Raw/{s['season']}/{s['experiment']}/{s['site']}/{s['population']}/{s['date']}/"
                      f"{s['platform']}/{s['sensor']}/{short_ids[0]}" if short_ids else None)

        def marking(m: dict) -> tuple[int, int]:
            src = self.copier.source(m.get("csv_path"))
            if not src:
                raise FileNotFoundError(f"{m.get('csv_path')} is not in the data folder")
            sels = selections_from_csv(src.read_text())
            snap = {"selections": sels, "track": {
                "imagesPrefix": f"{self.bucket}/{track_root}/RGB/Images/top/" if track_root else "",
                "msgsSyncedPath": f"{self.bucket}/{track_root}/RGB/Metadata/msgs_synced.csv" if track_root else None,
            }}
            return self._save_version(marks_dir, m.get("name") or f"v{m.get('version')} (GEMI)", snap), len(sels)

        saved = {}
        for m in sorted(o.get("plot_markings") or [], key=lambda m: m.get("version") or 0):
            r = self._part(f"{label}: plot marking v{m.get('version')}", lambda m=m: marking(m))
            if r:
                saved[m.get("version")] = r
                self.result["plot_markings"] += 1
        active = o.get("active_plot_marking_version")
        if active in saved:
            v, count = saved[active]
            if self._part(f"{label}: activating plot marking", lambda: self._json(self.http.post(
                    "/api/plot_geometry/versions/activate", json={"directory": marks_dir, "version": v})) or {}
                    ) is not None:
                steps["plot_marking"] = {"status": "completed", "jobIds": [], "completedAt": now,
                                         "outputs": {"directory": marks_dir, "version": v, "plots": count}}

        # Stitch versions: next free AgRowStitch_v{N}. The marker saying
        # which old stitch it came from is written FIRST, so an interrupted
        # copy is finished in the same folder by the next import instead of
        # leaving a partial duplicate.
        def stitch(st: dict) -> None:
            rel = norm_rel_path(st.get("dir"), self.copier.old_root)
            if not rel or not (self.data_dir / rel).is_dir():
                raise FileNotFoundError(f"{st.get('dir')} is not in the data folder")
            marker = {"imported_from": "GEMI", "legacy_run_id": run.id, "legacy_version": st.get("version")}
            target = self._stitch_dir(directory, marker)
            self.copier.put_bytes(json.dumps(marker).encode(), f"{target}imported_from_gemi.json",
                                  "application/json")
            root = (self.data_dir / rel).resolve()
            for p in sorted((self.data_dir / rel).rglob("*")):
                if p.is_file() and p.resolve().is_relative_to(root):
                    self.copier.put_file(p, f"{target}{p.relative_to(self.data_dir / rel).as_posix()}")

        for st in sorted(o.get("stitchings") or [], key=lambda x: x.get("version") or 0):
            if self._part(f"{label}: stitch v{st.get('version')}", lambda st=st: stitch(st) or True):
                self.result["stitches"] += 1
                steps["stitching"] = {"status": "completed", "jobIds": [], "completedAt": now}
        self._part(f"{label}: plot images", lambda: self._plot_images(o.get("cropped_images"), directory, {}))

    def _stitch_dir(self, directory: str, marker: dict) -> str:
        storage = self.copier.storage
        taken = set()
        for obj in storage.list_objects(self.bucket, prefix=f"{directory}AgRowStitch_v", recursive=True):
            m = re.match(rf"{re.escape(directory)}AgRowStitch_v(\d+)/", obj.object_name)
            if not m:
                continue
            taken.add(int(m.group(1)))
            if obj.object_name.endswith("/imported_from_gemi.json"):
                try:
                    r = storage.get_object(self.bucket, obj.object_name)
                    try:
                        if json.loads(r.read()) == marker:
                            return f"{directory}AgRowStitch_v{m.group(1)}/"
                    finally:
                        r.close()
                        r.release_conn()
                except Exception:  # noqa: BLE001
                    pass
        return f"{directory}AgRowStitch_v{max(taken, default=0) + 1}/"

    # -- archive ------------------------------------------------------------
    def archive(self) -> None:
        """Everything the old app wrote outside Raw/, as it was, so nothing
        is lost (results the new app can't show yet, logs, older copies)."""
        by_exp: dict[str, list[str]] = {}
        experiments = {u.experiment for u in self.uploads.values()} | {r.experiment for r in self.db.runs()}
        for rel, _size in _archive_files(self.data_dir):
            key = f"{ARCHIVE_ROOT}/{rel}"
            self.copier.put_file(self.data_dir / rel, key)
            self.result["archive_files"] += 1
            parts = rel.split("/")
            # {Intermediate|Processed}/{workspace}/{year}/{experiment}/…
            exp = parts[3] if len(parts) > 4 and parts[3] in experiments else None
            if exp:
                by_exp.setdefault(exp, []).append(key)
        for exp, keys in by_exp.items():
            try:
                e = self.api.experiment(exp)
                self.api.register(str(e["id"]), None, self.bucket, keys)
            except Exception as exc:  # noqa: BLE001
                self._fail(f"archive registration for {exp}", exc)

    def all(self, cancelled: Callable[[], bool]) -> dict:
        self.reference_datasets()
        try:
            found = self.workspaces_and_pipelines()
        except Exception as exc:  # noqa: BLE001
            self._fail("workspaces and pipelines", exc)
            found = {"workspaces": {}, "pipelines": {}}
        for run in self.db.runs():
            if cancelled():
                break
            pipe = found["pipelines"].get(run.pipeline_id)
            if not pipe:
                continue  # its pipeline was deleted; the archive keeps its files
            self.progress(f"Run {run.date} {run.platform}/{run.sensor}")
            try:
                self.run(run, pipe, found["workspaces"][pipe.workspace_id])
            except Exception as exc:  # noqa: BLE001
                self._fail(f"run {run.date} {run.platform}/{run.sensor}", exc)
        if not cancelled():
            self.progress("Archiving the previous app's other files")
            self.archive()
        return self.result


def _stamp(ts: Optional[str]) -> str:
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00")).strftime("%Y%m%d__%H%M%S")
    except ValueError:
        return "00000000__000000"
