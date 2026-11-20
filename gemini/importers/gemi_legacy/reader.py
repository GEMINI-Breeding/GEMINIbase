"""Read-only access to an old GEMI install's database.

Schema facts this relies on (from the v0.0.3/v0.0.4/v0.0.5 models):
- Tables are created by SQLModel `create_all`; later columns were added
  with ad-hoc ALTER TABLEs at startup, so a database may lack some columns
  (fileupload.msgs_synced_path, plotrecord.detection_*, traitrecord.version,
  referencedataset.original_filename). Columns are read if present.
- UUID columns are 32-char hex; a few string columns hold dashed UUIDs.
- Paths are relative to the data folder, but may carry Windows
  backslashes or (for a few legacy keys) another machine's absolute path.
- JSON columns are stored as TEXT.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Optional

JSON_COLUMNS = {
    "pipeline": {"config"},
    "pipelinerun": {"steps_completed", "outputs"},
    "traitrecord": {"trait_columns"},
    "plotrecord": {"traits", "extra_properties", "detection_class_summary"},
    "referencedataset": {"column_mapping", "trait_columns"},
    "referenceplot": {"traits"},
}


def open_readonly(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite file so that nothing can be written — not even a
    journal or WAL file beside it (`immutable=1`)."""
    uri = Path(path).resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def norm_uuid(value: Any) -> Optional[str]:
    """Any stored UUID form (32-hex, dashed, bytes) → dashed lowercase."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (bytes, bytearray)) and len(value) == 16:
            return str(uuid.UUID(bytes=bytes(value)))
        return str(uuid.UUID(str(value)))
    except ValueError:
        return None


def norm_rel_path(value: Optional[str], old_root: Optional[str] = None) -> Optional[str]:
    """A stored path as a clean POSIX path relative to the data folder, or
    None if it can't be one. Windows separators are converted; an absolute
    path under the old data folder is made relative; anything that would
    leave the data folder ('..', or absolute elsewhere) is refused."""
    if not value:
        return None
    text = str(value).strip()
    is_windows = "\\" in text or (len(text) > 1 and text[1] == ":")
    parts = list((PureWindowsPath(text) if is_windows else PurePosixPath(text)).parts)
    if old_root:
        root_is_windows = "\\" in old_root or (len(old_root) > 1 and old_root[1] == ":")
        root = list((PureWindowsPath(old_root) if root_is_windows else PurePosixPath(old_root)).parts)
        if len(parts) > len(root) and [p.lower() if is_windows else p for p in parts[: len(root)]] == [
            p.lower() if root_is_windows else p for p in root
        ]:
            parts = parts[len(root):]
    if parts and (parts[0] in ("/", "\\") or parts[0].endswith(("\\", ":\\")) or ":" in parts[0]):
        return None  # absolute, and not under the old data folder
    parts = [p for p in parts if p not in (".", "")]
    if not parts or any(p == ".." for p in parts):
        return None
    return "/".join(parts)


@dataclass
class LegacyUpload:
    id: str
    data_type: str
    experiment: str
    location: str
    population: str
    date: str
    platform: Optional[str]
    sensor: Optional[str]
    storage_path: Optional[str]
    msgs_synced_path: Optional[str]
    file_count: int
    status: str
    created_at: Optional[str]


class LegacyDatabase:
    """The old app's gemi.db, opened read-only."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = open_readonly(self.path)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "LegacyDatabase":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def tables(self) -> set[str]:
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {r[0] for r in rows}

    def columns(self, table: str) -> set[str]:
        return {r[1] for r in self.conn.execute(f'PRAGMA table_info("{table}")')}

    def rows(self, table: str, wanted: Iterable[str]) -> list[dict]:
        """Every row of `table` as a dict of the wanted columns; columns the
        database lacks are None; JSON columns are parsed (None if invalid)."""
        if table not in self.tables():
            return []
        wanted = list(wanted)
        have = self.columns(table)
        present = [c for c in wanted if c in have]
        if not present:
            return []
        cols = ", ".join(f'"{c}"' for c in present)
        out = []
        for r in self.conn.execute(f'SELECT {cols} FROM "{table}"'):
            row = {c: None for c in wanted}
            for c in present:
                v = r[c]
                if c in JSON_COLUMNS.get(table, set()) and isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except ValueError:
                        v = None
                row[c] = v
            out.append(row)
        return out

    def setting(self, key: str) -> Optional[str]:
        for r in self.rows("appsetting", ["key", "value"]):
            if r["key"] == key:
                return r["value"] or None
        return None

    def old_data_root(self) -> Optional[str]:
        """The data folder's absolute path as the old app saw it (on its own
        machine); None means the default ~/GEMI-Data."""
        return self.setting("data_root")

    def uploads(self) -> list[LegacyUpload]:
        old_root = self.old_data_root()
        out = []
        for r in self.rows("fileupload", [
            "id", "data_type", "experiment", "location", "population", "date",
            "platform", "sensor", "storage_path", "msgs_synced_path",
            "file_count", "status", "created_at",
        ]):
            out.append(LegacyUpload(
                id=norm_uuid(r["id"]) or str(r["id"]),
                data_type=r["data_type"] or "",
                experiment=r["experiment"] or "",
                location=r["location"] or "",
                population=r["population"] or "",
                date=r["date"] or "",
                platform=r["platform"] or None,
                sensor=r["sensor"] or None,
                storage_path=norm_rel_path(r["storage_path"], old_root),
                msgs_synced_path=norm_rel_path(r["msgs_synced_path"], old_root),
                file_count=int(r["file_count"] or 0),
                status=r["status"] or "",
                created_at=r["created_at"],
            ))
        return out


    # ── Tiers 2–3: workspaces, pipelines, runs, results, reference data ─

    def workspaces(self) -> list[LegacyWorkspace]:
        return [
            LegacyWorkspace(norm_uuid(r["id"]) or "", r["name"] or "", r["description"], r["created_at"])
            for r in self.rows("workspace", ["id", "name", "description", "created_at"])
        ]

    def pipelines(self) -> list[LegacyPipeline]:
        return [
            LegacyPipeline(
                norm_uuid(r["id"]) or "", norm_uuid(r["workspace_id"]) or "", r["name"] or "",
                (r["type"] or "").lower(), r["config"] if isinstance(r["config"], dict) else {},
                r["created_at"],
            )
            for r in self.rows("pipeline", ["id", "workspace_id", "name", "type", "config", "created_at"])
        ]

    def runs(self) -> list[LegacyRun]:
        return [
            LegacyRun(
                norm_uuid(r["id"]) or "", norm_uuid(r["pipeline_id"]) or "",
                norm_uuid(r["file_upload_id"]), r["date"] or "", r["experiment"] or "",
                r["location"] or "", r["population"] or "", r["platform"] or "",
                r["sensor"] or "", r["status"] or "",
                r["steps_completed"] if isinstance(r["steps_completed"], dict) else {},
                r["outputs"] if isinstance(r["outputs"], dict) else {},
                r["created_at"], r["completed_at"],
            )
            for r in self.rows("pipelinerun", [
                "id", "pipeline_id", "file_upload_id", "date", "experiment", "location",
                "population", "platform", "sensor", "status", "steps_completed", "outputs",
                "created_at", "completed_at",
            ])
        ]

    def trait_records(self) -> list[LegacyTraitRecord]:
        out = []
        for r in self.rows("traitrecord", [
            "id", "run_id", "version", "trait_columns", "boundary_version", "ortho_version", "created_at",
        ]):
            out.append(LegacyTraitRecord(
                norm_uuid(r["id"]) or "", norm_uuid(r["run_id"]) or "", int(r["version"] or 1),
                r["trait_columns"] if isinstance(r["trait_columns"], list) else [],
                r["boundary_version"], r["ortho_version"], r["created_at"],
            ))
        return out

    def plot_records(self) -> list[LegacyPlotRecord]:
        out = []
        for r in self.rows("plotrecord", ["trait_record_id", "plot_id", "accession", "row", "col", "traits"]):
            out.append(LegacyPlotRecord(
                norm_uuid(r["trait_record_id"]) or "", str(r["plot_id"] or ""),
                r["accession"] or None, r["row"], r["col"],
                r["traits"] if isinstance(r["traits"], dict) else {},
            ))
        return out

    def reference_datasets(self) -> list[LegacyReferenceDataset]:
        return [
            LegacyReferenceDataset(
                norm_uuid(r["id"]) or "", r["name"] or "", r["experiment"] or "",
                r["location"] or "", r["population"] or "", r["date"] or "",
                r["column_mapping"] if isinstance(r["column_mapping"], dict) else {},
                r["trait_columns"] if isinstance(r["trait_columns"], list) else [],
                r["original_filename"], r["created_at"],
            )
            for r in self.rows("referencedataset", [
                "id", "name", "experiment", "location", "population", "date",
                "column_mapping", "trait_columns", "original_filename", "created_at",
            ])
        ]

    def reference_plots(self) -> list[LegacyReferencePlot]:
        return [
            LegacyReferencePlot(
                norm_uuid(r["dataset_id"]) or "", str(r["plot_id"] or ""), r["col"], r["row"],
                r["accession"] or None, r["traits"] if isinstance(r["traits"], dict) else {},
            )
            for r in self.rows("referenceplot", ["dataset_id", "plot_id", "col", "row", "accession", "traits"])
        ]


# ── Workspaces, pipelines, runs, results (tiers 2–3) ───────────────────────


@dataclass
class LegacyWorkspace:
    id: str
    name: str
    description: Optional[str]
    created_at: Optional[str]


@dataclass
class LegacyPipeline:
    id: str
    workspace_id: str
    name: str
    type: str  # "aerial" | "ground"
    config: dict
    created_at: Optional[str]


@dataclass
class LegacyRun:
    id: str
    pipeline_id: str
    file_upload_id: Optional[str]
    date: str
    experiment: str
    location: str
    population: str
    platform: str
    sensor: str
    status: str
    steps_completed: dict
    outputs: dict
    created_at: Optional[str]
    completed_at: Optional[str]


@dataclass
class LegacyTraitRecord:
    id: str
    run_id: str
    version: int
    trait_columns: list
    boundary_version: Optional[int]
    ortho_version: Optional[int]
    created_at: Optional[str]


@dataclass
class LegacyPlotRecord:
    trait_record_id: str
    plot_id: str
    accession: Optional[str]
    row: Optional[str]
    col: Optional[str]
    traits: dict


@dataclass
class LegacyReferenceDataset:
    id: str
    name: str
    experiment: str
    location: str
    population: str
    date: str
    column_mapping: dict
    trait_columns: list
    original_filename: Optional[str]
    created_at: Optional[str]


@dataclass
class LegacyReferencePlot:
    dataset_id: str
    plot_id: str
    col: Optional[str]
    row: Optional[str]
    accession: Optional[str]
    traits: dict
