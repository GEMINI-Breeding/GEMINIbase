"""Plan the import of an old install's uploads (tier 1): what each becomes
in GEMINIbase and where every file lands. Pure: reads the old database and
lists the old data folder, writes nothing. The plan is what the dry run
shows the user, and what the import then carries out.

Mapping (old Raw layout → new):
- Old uploads live at `Raw/{year}/{E}/{L}/{P}/...`; the new layout's first
  slot is the season, so **season = that year** and the rest of the path is
  kept as is — where the old app kept a file is where it goes.
- Image-type uploads (Image Data, Farm-ng) get the per-dataset `{short_id}/`
  before `Images/`, exactly as the new uploader does (UploadList.tsx
  buildTargetRootDir). The short id comes from the dataset the import
  creates, so targets hold a `{short_id}` placeholder until then.
- A DEM moves from `Orthomosaic/` to `Orthomosaic-DEM/` (the new uploader's
  folder for DEMs).
- Farm-ng: the old app deleted the .bin after extracting it into
  `Images/RGB/{camera}/` and `Images/RGB/Metadata/`; the new extraction
  writes `{short_id}/RGB/Images/{camera}/` and `{short_id}/RGB/Metadata/`.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from gemini.importers.gemi_legacy.reader import LegacyDatabase, LegacyUpload

SHORT_ID = "{short_id}"

# Old data type → how its files map. "images": gets the dataset segment.
KNOWN_TYPES = {
    "Image Data": "images",
    "Farm-ng Binary File": "amiga",
    "Ardupilot Logs": "plain",
    "Synced Metadata": "plain",
    "Orthomosaic": "ortho",
    "Orthomosaic DEM": "ortho",
    "Weather Data": "plain",
    "Field Design": "plain",
}


@dataclass
class PlannedFile:
    source: str   # relative to the old data folder
    target: str   # object key in the bucket (may hold {short_id})
    size: int


@dataclass
class UploadPlan:
    upload_id: str
    data_type: str
    season: str
    experiment: str
    site: str
    population: str
    date: str
    platform: Optional[str]
    sensor: Optional[str]
    source_dir: Optional[str]
    created_at: Optional[str] = None
    files: list[PlannedFile] = field(default_factory=list)
    skip_reason: Optional[str] = None

    @property
    def bytes(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def needs_dataset(self) -> bool:
        return any(SHORT_ID in f.target for f in self.files)


@dataclass
class ImportPlan:
    uploads: list[UploadPlan]

    @property
    def to_import(self) -> list[UploadPlan]:
        return [u for u in self.uploads if not u.skip_reason]

    @property
    def skipped(self) -> list[UploadPlan]:
        return [u for u in self.uploads if u.skip_reason]

    def summary(self) -> dict:
        todo = self.to_import
        return {
            "uploads": len(todo),
            "files": sum(len(u.files) for u in todo),
            "bytes": sum(u.bytes for u in todo),
            "experiments": sorted({u.experiment for u in todo}),
            "seasons": sorted({u.season for u in todo}),
            "skipped": [
                {"upload_id": u.upload_id, "data_type": u.data_type,
                 "path": u.source_dir, "reason": u.skip_reason}
                for u in self.skipped
            ],
        }


def season_of(upload: LegacyUpload) -> str:
    """The old path's year slot (what the old app actually used), else the
    date's year, else the date as is."""
    parts = (upload.storage_path or "").split("/")
    if len(parts) > 1 and parts[0] == "Raw" and parts[1]:
        return parts[1]
    return upload.date.split("-")[0] if upload.date else ""


def _walk(root: Path) -> list[tuple[str, int]]:
    """(relative POSIX path, size) of every regular file under root.
    Symlinks are followed only if they stay inside root."""
    out = []
    root_real = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            p = Path(dirpath) / name
            try:
                real = p.resolve()
                if not real.is_relative_to(root_real) or not real.is_file():
                    continue
                out.append((p.relative_to(root).as_posix(), real.stat().st_size))
            except OSError:
                continue
    return out


def _target(kind: str, storage_path: str, rel: str) -> str:
    """Object key for one file of an upload (see module docstring)."""
    base = storage_path.rstrip("/")
    if kind == "images" and base.endswith("/Images"):
        return f"{base[: -len('/Images')]}/{SHORT_ID}/Images/{rel}"
    if kind == "amiga" and base.endswith("/Images"):
        root = f"{base[: -len('/Images')]}/{SHORT_ID}"
        m = re.match(r"^RGB/(?!Metadata/)([^/]+)/(.+)$", rel)
        if m:
            return f"{root}/RGB/Images/{m.group(1)}/{m.group(2)}"
        return f"{root}/{rel}"
    if kind == "ortho" and base.endswith("/Orthomosaic") and re.search(r"-DEM(-v\d+)?\.tiff?$", rel, re.I):
        return f"{base[: -len('/Orthomosaic')]}/Orthomosaic-DEM/{rel}"
    return f"{base}/{rel}"


def plan_upload(upload: LegacyUpload, data_dir: Path) -> UploadPlan:
    plan = UploadPlan(
        upload_id=upload.id, data_type=upload.data_type, season=season_of(upload),
        experiment=upload.experiment, site=upload.location,
        population=upload.population, date=upload.date,
        platform=upload.platform, sensor=upload.sensor,
        source_dir=upload.storage_path, created_at=upload.created_at,
    )
    kind = KNOWN_TYPES.get(upload.data_type)
    if kind is None:
        plan.skip_reason = f"unknown data type {upload.data_type!r}"
    elif upload.status == "missing":
        plan.skip_reason = "the old app had already marked its folder missing"
    elif not upload.storage_path:
        plan.skip_reason = "no usable folder path in the old database"
    elif not upload.experiment:
        plan.skip_reason = "no experiment recorded"
    else:
        src = data_dir / upload.storage_path
        if not src.is_dir():
            plan.skip_reason = "its folder is not in the data folder"
        else:
            plan.files = [
                PlannedFile(f"{upload.storage_path}/{rel}", _target(kind, upload.storage_path, rel), size)
                for rel, size in _walk(src)
            ]
            if not plan.files:
                plan.skip_reason = "its folder is empty"
    return plan


def plan_import(db: LegacyDatabase, data_dir: str | Path) -> ImportPlan:
    data_dir = Path(data_dir)
    return ImportPlan([plan_upload(u, data_dir) for u in db.uploads()])
