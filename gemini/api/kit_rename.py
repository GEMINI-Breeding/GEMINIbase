"""Renaming a platform or a sensor of data already in the app.

Platform and sensor are path segments of every file of an upload and of
everything made from it:

    Raw/{year}/{experiment}/{site}/{population}/{date}/{platform}/{sensor}/…
    Processed/{year}/{experiment}/{site}/{population}/{date}/{platform}/{sensor}/…

and the app files new uploads by a fixed list of platforms (Drone, Rover,
Handheld) and sensors (RGB, Thermal, …). Data uploaded under another name
("P4", "Amiga") would never meet new uploads of the same flight; renaming it
moves it to the name new uploads use. Everything that names those paths moves
with it: the files, their records, the upload datasets, the Process tab's runs
and the plot boundaries saved for the folder, the jobs' records.

This module is the pure part (which paths, and how they change); the admin
endpoint (controllers/kit_rename.py) applies it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

ROOTS = ("Raw", "Processed")
SEGMENT = {"platform": 6, "sensor": 7}      # index in the path, after the root


@dataclass(frozen=True)
class Rename:
    experiment: str
    field: str                 # "platform" | "sensor"
    old: str
    new: str
    site: Optional[str] = None

    def __post_init__(self) -> None:
        if self.field not in SEGMENT:
            raise ValueError("field must be platform or sensor")
        for v in (self.old, self.new, self.experiment):
            if not v or "/" in v or v in (".", ".."):
                raise ValueError(f"bad name {v!r}")
        if self.old == self.new:
            raise ValueError("old and new are the same")


def new_path(path: str, r: Rename) -> Optional[str]:
    """The path after the rename, or None when it is not one of the renamed data's.
    Works with or without a leading bucket ("gemini/Raw/…") and on folder prefixes."""
    lead = ""
    body = path
    m = re.match(r"^([^/]+/)(?=(?:Raw|Processed)/)", path)
    if m:
        lead, body = m.group(1), path[len(m.group(1)):]
    parts = body.split("/")
    i = SEGMENT[r.field]
    if len(parts) <= i or parts[0] not in ROOTS:
        return None
    if parts[2] != r.experiment or (r.site is not None and parts[3] != r.site):
        return None
    if parts[i] != r.old:
        return None
    parts[i] = r.new
    return lead + "/".join(parts)


_PATHLIKE = re.compile(r"(?:^|(?<=[\s\"'(=]))(?:[^\s\"'/]+/)?(?:Raw|Processed)/[^\s\"']+")


def rewrite_text(text: str, r: Rename) -> str:
    """Every path in a string (a bare path, or paths inside a message) renamed."""
    if "/" not in text:
        return text
    whole = new_path(text, r)                # a string that is a path (names may hold spaces)
    if whole is not None:
        return whole

    def one(m: re.Match) -> str:
        return new_path(m.group(0), r) or m.group(0)

    return _PATHLIKE.sub(one, text)


def rewrite_json(value: Any, r: Rename, in_scope: bool = False) -> tuple[Any, int]:
    """A JSON document (a Process-tab run, a job's parameters, a boundary snapshot) with its
    paths renamed, and, in a scope of the renamed data ({experiment, site, platform/sensor}),
    the field itself. Returns (new value, number of changes)."""
    changes = 0
    if isinstance(value, str):
        out = rewrite_text(value, r)
        return out, int(out != value)
    if isinstance(value, list):
        res = []
        for v in value:
            nv, n = rewrite_json(v, r, in_scope)
            res.append(nv)
            changes += n
        return res, changes
    if isinstance(value, dict):
        scoped = in_scope or _is_scope(value, r)
        # A run (its name) whose upload scope, one level down, is the renamed data's.
        holds = scoped or any(isinstance(v, dict) and _is_scope(v, r) for v in value.values())
        res = {}
        for k, v in value.items():
            if scoped and k in _FIELD_KEYS[r.field] and v == r.old:
                res[k] = r.new
                changes += 1
                continue
            if holds and k == "name" and isinstance(v, str):
                # A run's name: "2022-07-05 · P4/RGB".
                renamed = v.replace(f"{r.old}/", f"{r.new}/") if r.field == "platform" \
                    else re.sub(rf"/{re.escape(r.old)}\b", f"/{r.new}", v)
                res[k] = renamed
                changes += int(renamed != v)
                continue
            nv, n = rewrite_json(v, r, scoped and not isinstance(v, dict))
            res[k] = nv
            changes += n
        return res, changes
    return value, 0


_FIELD_KEYS = {"platform": ("platform", "sensorPlatform", "sensor_platform"), "sensor": ("sensor",)}


def _is_scope(d: dict, r: Rename) -> bool:
    """A dict describing the renamed data's scope: its experiment (and site), and the old name."""
    exp = d.get("experiment") or d.get("experiment_name")
    site = d.get("location") or d.get("site") or d.get("site_name")
    named = any(d.get(k) == r.old for k in _FIELD_KEYS[r.field])
    return named and exp == r.experiment and (r.site is None or site in (None, r.site))
