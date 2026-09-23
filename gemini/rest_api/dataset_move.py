"""
Edit an upload's metadata (main's "edit metadata" for a file upload).

Here an upload's season, site, population, date, platform and sensor *are*
its storage path:

    Raw/{season}/{experiment}/{site}/{population}/{date}/{platform}/{sensor}/{dataset}/…

so fixing one means moving the upload's folder. The experiment is not
editable here (that's a different operation). Rules:

- Everything under the upload's folder moves — its own files and what
  workers wrote beside them (extracted frames, synced tracks) — and each
  file's experiment_files row follows it.
- Nothing is overwritten: if any target already exists the move is refused.
- Copy, repoint the row, then delete the source, one object at a time; a
  failure stops the move and reports what moved. Re-running continues,
  since moved files already sit at their new keys.
- Processed/ outputs built from the old scope (orthos, stitches, boundaries,
  traits) stay where they are; the result lists that they exist.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)

FIELDS = ("season", "site", "population", "date", "platform", "sensor")


class MoveError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def source_folder(object_names: List[str], to: Dict[str, str]) -> str:
    """The upload's folder, Raw/…/{sensor}/{dataset}/, from its files.

    Normally all files share one folder. After a move that stopped part way,
    some are already in the target folder: the other one is the source, and
    moving again finishes the job.
    """
    folders = set()
    for name in object_names:
        parts = name.split("/")
        if len(parts) < 10 or parts[0] != "Raw" or not re.fullmatch(r"[0-9a-f]{8}", parts[8]):
            raise MoveError(
                f"{name} isn't in a per-upload folder (Raw/…/{{sensor}}/{{dataset}}/); "
                "uploads from before per-upload folders can't be moved.")
        folders.add("/".join(parts[:9]) + "/")
    if not folders:
        raise MoveError("This upload has no files.", 404)
    if len(folders) == 1:
        return folders.pop()
    if len(folders) == 2:
        a, b = sorted(folders)
        if target_folder(a, to) == b:
            return a
        if target_folder(b, to) == a:
            return b
    raise MoveError(f"The upload's files are in {len(folders)} folders: {sorted(folders)}")


def scope_of(folder: str) -> Dict[str, str]:
    parts = folder.strip("/").split("/")
    return {
        "season": parts[1], "experiment": parts[2], "site": parts[3],
        "population": parts[4], "date": parts[5], "platform": parts[6],
        "sensor": parts[7], "dataset": parts[8],
    }


def target_folder(folder: str, to: Dict[str, str]) -> str:
    s = scope_of(folder)
    for f in FIELDS:
        v = (to.get(f) or "").strip()
        if not v:
            raise MoveError(f"{f} can't be empty")
        if "/" in v:
            raise MoveError(f"{f} can't contain '/'")
        s[f] = v
    return "Raw/{season}/{experiment}/{site}/{population}/{date}/{platform}/{sensor}/{dataset}/".format(**s)


@dataclass
class MoveResult:
    source: str
    target: str
    moved: int = 0
    processed_outputs_left: List[str] = field(default_factory=list)


def move_upload(
    *,
    folder: str,
    to: Dict[str, str],
    list_objects: Callable[[str], List[str]],
    exists: Callable[[str], bool],
    copy: Callable[[str, str], None],
    remove: Callable[[str], None],
    repoint: Callable[[str, str], None],
) -> MoveResult:
    """Move every object under `folder` to the folder for scope `to`."""
    target = target_folder(folder, to)
    result = MoveResult(source=folder, target=target)
    if target == folder:
        return result
    objects = list_objects(folder)
    if not objects:
        raise MoveError("The upload's folder is empty.", 404)
    clashes = [target + o[len(folder):] for o in objects if exists(target + o[len(folder):])]
    if clashes:
        raise MoveError(
            f"{len(clashes)} file(s) already exist at the new location "
            f"(e.g. {clashes[0]}); nothing was moved.", 409)
    for obj in objects:
        new = target + obj[len(folder):]
        try:
            copy(obj, new)
            repoint(obj, new)
            remove(obj)
        except Exception as exc:
            raise MoveError(
                f"Stopped after moving {result.moved} of {len(objects)} files: {obj}: {exc}. "
                "Run the move again to finish it.", 500) from exc
        result.moved += 1
    old = scope_of(folder)
    processed = "Processed/{season}/{experiment}/{site}/{population}/{date}/{platform}/{sensor}/".format(**old)
    result.processed_outputs_left = list_objects(processed)[:20]
    return result


def ensure_entities(experiment: str, to: Dict[str, str]) -> None:
    """Season, site and population exist and belong to the experiment
    (as the upload form ensures before an upload). Best effort."""
    from gemini.api.population import Population
    from gemini.api.season import Season
    from gemini.api.site import Site

    for make in (
        lambda: Season.get(season_name=to["season"], experiment_name=experiment)
        or Season.create(season_name=to["season"], experiment_name=experiment),
        lambda: Site.create(site_name=to["site"], experiment_name=experiment),
        lambda: Population.create(population_name=to["population"], experiment_name=experiment),
    ):
        try:
            make()
        except Exception as exc:
            logger.warning("Couldn't ensure an entity for the move: %s", exc)

