"""
ODM processing worker.

Handles orthomosaic generation via NodeODM:
- RUN_ODM: Download drone images from MinIO, submit to NodeODM,
  poll for progress, upload resulting orthophoto back to MinIO.

Requires: NodeODM sidecar service (opendronemap/nodeodm).
"""

import logging
import os
import tempfile
import time
from typing import Set

import requests

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType
from gemini.workers.odm.nodeodm_client import (
    NodeODMClient,
    NodeODMError,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_FAILED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)

logger = logging.getLogger(__name__)

# MinIO connection
STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

# NodeODM polling interval
POLL_INTERVAL = int(os.environ.get("GEMINI_ODM_POLL_INTERVAL", "5"))

# Max consecutive poll failures before failing the job (5s * 60 = 5 min)
MAX_POLL_FAILURES = int(os.environ.get("GEMINI_ODM_MAX_POLL_FAILURES", "60"))

# Image file extensions to include
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Sidecar files NodeODM auto-detects when present alongside the images.
# The frontend's GCP picker writes both to the same MinIO prefix.
GCP_SIDECAR_FILENAMES = ("gcp_list.txt", "geo.txt")

# Optional sidecar written by the frontend's Image Review step. One image
# basename per line, with `#` comments. Listed images are dropped from
# both the staged image set and the geo.txt rows we forward to NodeODM.
IMAGE_FILTER_FILENAME = "image_filter.txt"

# Default ODM options. Match main's `run_orthomosaic` defaults
# (backend/app/processing/aerial.py): --dsm at 3 cm/px for both ortho
# and DEM, --skip-report to dodge the NumPy 2.x / GDAL incompatibility
# in ODM's report stage. Quality presets layer on top of this; "Custom"
# / None / unknown quality strings yield these unchanged.
#
# The historical 0.25 cm/px default on this branch produced ~20k×20k
# px ortho canvases that OOM-killed texrecon on a stock Docker Desktop
# install. 3 cm/px keeps us inside the memory envelope main targets
# and matches the visual quality users have been getting from main.
DEFAULT_OPTIONS = [
    {"name": "orthophoto-resolution", "value": 3},
    {"name": "dem-resolution", "value": 3},
    {"name": "dsm", "value": True},
    {"name": "skip-report", "value": True},
]


# Reconstruction-quality presets exposed by the OrthomosaicTool dropdown.
# Each preset is a flat list of NodeODM `{name, value}` overrides that get
# merged into DEFAULT_OPTIONS at submit time.
# Preset table is a 1:1 port of main's `ODM_PRESETS`
# (backend/app/processing/aerial.py + ProcessingPipeline.tsx). Same names,
# same cm/px, same pc/feature qualities. We keep the migrated stack
# producing the same orthos main produced — diverging silently is what
# got us into trouble (every prior preset divergence on this branch
# either OOM'd at texrecon or ran at a different resolution than the
# user expected). Custom is handled separately by the worker (the
# textbox path), not as a preset row.
QUALITY_PRESETS: dict[str, list[dict]] = {
    "Draft": [
        {"name": "feature-quality", "value": "low"},
        {"name": "pc-quality", "value": "lowest"},
        {"name": "orthophoto-resolution", "value": 5},
        {"name": "dem-resolution", "value": 5},
    ],
    "Standard": [
        {"name": "feature-quality", "value": "high"},
        {"name": "pc-quality", "value": "medium"},
        {"name": "orthophoto-resolution", "value": 3},
        {"name": "dem-resolution", "value": 3},
    ],
    "High Quality": [
        {"name": "feature-quality", "value": "ultra"},
        {"name": "pc-quality", "value": "high"},
        {"name": "orthophoto-resolution", "value": 2},
        {"name": "dem-resolution", "value": 2},
    ],
    "Ultra": [
        {"name": "feature-quality", "value": "ultra"},
        {"name": "pc-quality", "value": "ultra"},
        {"name": "orthophoto-resolution", "value": 1},
        {"name": "dem-resolution", "value": 1},
    ],
}


# Piecewise mapping from NodeODM's `progress` field (0-100, computed as the
# linear sum of ODM stage weights) to the worker's 20-85 UI band. The
# breakpoints are chosen so the slow stages — opensfm (ODM 5-25) and openmvs
# (ODM 25-50) — span more of the visible range than their natural ODM weights
# imply. Without this remap the bar sits at ~23% for the entire opensfm phase
# (commonly 30-50% of total wall-clock on real flights).
#
# ODM 0-5    (dataset)              → UI 20-23
# ODM 5-25   (opensfm)              → UI 23-48     (was 23-36)
# ODM 25-50  (openmvs)              → UI 48-65     (was 36-52)
# ODM 50-100 (filterpoints+mesh+
#             texturing+geo+dem+
#             ortho+report)         → UI 65-85     (was 52-85)
_ODM_REMAP_BREAKPOINTS = (
    (0, 20),
    (5, 23),
    (25, 48),
    (50, 65),
    (100, 85),
)


def _remap_odm_progress(odm_progress: float) -> float:
    """Piecewise-linear remap of NodeODM's progress field to the UI band.

    See _ODM_REMAP_BREAKPOINTS for the mapping rationale.
    """
    p = max(0.0, min(100.0, float(odm_progress)))
    pts = _ODM_REMAP_BREAKPOINTS
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= p <= x1:
            if x1 == x0:
                return y0
            return y0 + (p - x0) * (y1 - y0) / (x1 - x0)
    return pts[-1][1]


# Time constant (seconds) for the asymptotic plateau-creep. After ~tau seconds
# stuck at the same NodeODM progress value, the smoothed bar is halfway to the
# segment ceiling; after 2*tau, ~67%; after 4*tau, ~80%. Five minutes is tuned
# for the opensfm/openmvs plateaus seen in real flights — small enough that
# the bar visibly moves within the first minute, large enough that we never
# crowd the ceiling before the next ODM tick arrives.
SMOOTH_TAU_SECONDS = float(os.environ.get("GEMINI_ODM_SMOOTH_TAU", "300"))


def _segment_ceiling(odm_progress: float) -> float:
    """Mapped ceiling of the piecewise segment containing odm_progress."""
    p = max(0.0, min(100.0, float(odm_progress)))
    pts = _ODM_REMAP_BREAKPOINTS
    for i in range(len(pts) - 1):
        x0, _ = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= p < x1:
            return float(y1)
    return float(pts[-1][1])


def _smooth_progress(
    odm_progress: float,
    plateau_elapsed: float,
    last_reported: float,
    tau: float = SMOOTH_TAU_SECONDS,
) -> float:
    """Asymptotic plateau-creep on top of `_remap_odm_progress`.

    NodeODM's `progress` field is chunky — it can sit at the same value for
    many minutes while opensfm or openmvs grinds through internal sub-stages
    that NodeODM doesn't surface. Without smoothing, the UI bar appears
    frozen even though the worker is polling and the job is making progress
    (one real flight reported only 5 distinct ODM progress values across
    14 minutes of opensfm). We approach — but never reach — the next
    breakpoint asymptotically, then re-base when ODM finally ticks.
    Monotonic: never regresses on re-base.
    """
    base = _remap_odm_progress(odm_progress)
    ceiling = _segment_ceiling(odm_progress)
    # Reserve 1 UI point of headroom so we never collide with the next
    # breakpoint — leaves visible motion for the real ODM tick.
    headroom = max(0.0, ceiling - 1.0 - base)
    creep = (
        headroom * plateau_elapsed / (plateau_elapsed + tau)
        if plateau_elapsed > 0
        else 0.0
    )
    return max(last_reported, base + creep)


def _apply_quality_preset(quality: str | None) -> list[dict]:
    """Return DEFAULT_OPTIONS with the matching quality-preset overrides
    merged in (preset values win on key collisions). Unknown / empty
    quality strings (`Custom`, `None`, anything not in QUALITY_PRESETS)
    just yield DEFAULT_OPTIONS unchanged.

    Returns a fresh list so callers can mutate without polluting module
    state. Pure function — covered by pytest in
    tests/workers/odm/test_quality_presets.py.
    """
    base = list(DEFAULT_OPTIONS)
    if not quality or quality not in QUALITY_PRESETS:
        return base
    overrides = QUALITY_PRESETS[quality]
    by_name = {opt["name"]: opt for opt in base}
    for opt in overrides:
        by_name[opt["name"]] = opt
    return list(by_name.values())


def _get_minio_client():
    """Create a MinIO client for file access."""
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _build_scope_prefix(params: dict) -> str:
    """Build the scope-root prefix `Raw/{year}/.../{sensor}/` (no
    `dataset_short_id`, no `Images/`).

    This is where scope-wide artifacts live: `image_filter.txt`,
    `gcp_list.txt`, `geo.txt`, `gcp_locations.csv`,
    `gcp_image_groups.json`. The Image Review and GCP Picker tools
    write them at this root so they survive multi-dataset selection
    in the Run wizard (one ODM job can pool images from multiple
    per-dataset prefixes — the GCP/filter set is shared across them).
    """
    parts = [
        "Raw",
        params.get("year", ""),
        params.get("experiment", ""),
        params.get("location", ""),
        params.get("population", ""),
        params.get("date", ""),
        params.get("platform", ""),
        params.get("sensor", ""),
    ]
    return "/".join(p for p in parts if p) + "/"


def _build_image_prefix(params: dict) -> str:
    """Build the MinIO prefix for raw images from job parameters.

    Mirrors the frontend upload-form convention from
    `gemini-app/frontend/src/config/dataTypes.ts`: drone images land under
    `Raw/{year}/{experiment}/{location}/{population}/{date}/{platform}/
    {sensor}/[dataset_short_id/]Images/`. The optional `dataset_short_id`
    segment isolates per-upload prefixes so two uploads at the same scope
    don't commingle on disk; when absent the prefix collapses to the
    legacy `{sensor}/Images/` shape (used by pre-migration uploads and as
    the recursive root for multi-dataset listings — see
    `_resolve_image_prefixes`).
    """
    parts = [
        "Raw",
        params.get("year", ""),
        params.get("experiment", ""),
        params.get("location", ""),
        params.get("population", ""),
        params.get("date", ""),
        params.get("platform", ""),
        params.get("sensor", ""),
        params.get("dataset_short_id", ""),
    ]
    return "/".join(p for p in parts if p) + "/Images/"


def _resolve_image_prefixes(params: dict) -> list[str]:
    """Decide which MinIO prefixes feed RUN_ODM for this job.

    Three input shapes are accepted:

    1. `dataset_short_ids: list[str]` — multi-dataset selection from the
       Run wizard. One prefix per chosen dataset:
       `Raw/.../{sensor}/{shortId}/Images/`.
    2. `dataset_short_id: str` — single-dataset job. One prefix.
    3. Neither — legacy / "all datasets at this scope" semantics. One
       prefix at `Raw/.../{sensor}/` (recursive listing in
       `_download_images` picks up both legacy `{sensor}/Images/...`
       and new `{sensor}/{shortId}/Images/...` files).
    """
    short_ids = params.get("dataset_short_ids")
    if isinstance(short_ids, list) and short_ids:
        scope_prefix = _build_scope_prefix(params)
        return [f"{scope_prefix}{sid}/Images/" for sid in short_ids if sid]
    if params.get("dataset_short_id"):
        return [_build_image_prefix(params)]
    # Legacy / all-datasets fallback: recursive listing under the scope
    # root catches both layouts.
    return [_build_scope_prefix(params)]


def _build_output_prefix(params: dict) -> str:
    """Build the MinIO prefix for processed output from job parameters.

    `dataset_short_id` is intentionally NOT inserted here: outputs
    (orthophoto, COG, log, etc.) are scope-wide products of one or more
    datasets. The Run wizard's multi-dataset selection feeds them into
    one ODM job whose output lives at the scope root.
    """
    parts = [
        "Processed",
        params.get("year", ""),
        params.get("experiment", ""),
        params.get("location", ""),
        params.get("population", ""),
        params.get("date", ""),
        params.get("platform", ""),
        params.get("sensor", ""),
    ]
    return "/".join(p for p in parts if p) + "/"


def _parse_custom_options(custom_options) -> list[dict]:
    """
    Parse custom ODM options from the frontend.

    Accepts either a string of CLI-style args (e.g. "--dem-resolution 0.25 --orthophoto-resolution 0.25")
    or a list of {"name": ..., "value": ...} dicts.
    """
    if isinstance(custom_options, list):
        if all(isinstance(o, dict) for o in custom_options):
            return custom_options
        return []

    if not isinstance(custom_options, str) or not custom_options.strip():
        return DEFAULT_OPTIONS

    options = []
    parts = custom_options.strip().split()
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            name = part.lstrip("-")
            # Check if next part is a value or another flag
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                value = parts[i + 1]
                # Try to parse as number or boolean
                if value.lower() in ("true", "yes"):
                    value = True
                elif value.lower() in ("false", "no"):
                    value = False
                else:
                    try:
                        value = float(value) if "." in value else int(value)
                    except ValueError:
                        pass
                options.append({"name": name, "value": value})
                i += 2
            else:
                # Boolean flag
                options.append({"name": name, "value": True})
                i += 1
        else:
            i += 1

    return options if options else DEFAULT_OPTIONS


def _diagnose_odm_failure(log_lines: list[str]) -> str:
    """Scan the ODM task log for common failure signatures and return a
    short, actionable description.

    NodeODM only ever surfaces "Cannot process dataset" via its
    `errorMessage` field — the actual root cause is buried in the task
    output. The patterns here cover the failure modes we've actually
    seen in the field; returning an empty string is fine when nothing
    matches and falls back to the generic message at the call site.
    """
    if not log_lines:
        return ""
    # Search the tail first — failures are almost always near the end.
    tail = "\n".join(log_lines[-200:])

    # OOM-killer SIGKILL on a sub-process. Most common ODM failure on
    # large flights: OpenMVS depth-fusion or PoissonRecon spikes RAM
    # past Docker's container limit, the kernel kills the subprocess,
    # ODM observes the dead exit code, marks the sub-scene unrecoverable,
    # and ends with "Could not compute dense point cloud".
    if "Killed" in tail and (
        "depth-maps" in tail
        or "Could not compute dense point cloud" in tail
        or "could not be reconstructed" in tail
    ):
        return (
            "out-of-memory during depth-map fusion. The OpenMVS step needs "
            "~15-25 GiB RAM for hundreds of high-res images; the Docker "
            "engine is likely capped lower than that. Raise Docker Desktop's "
            "memory limit (Settings → Resources → Memory) to at least 16 GiB, "
            "or retry with `--feature-quality medium` / fewer images / a "
            "smaller `--depthmap-resolution`."
        )

    # OOM at the texturing stage. Distinct signature from depth-map OOM:
    # texrecon prints "Running..." then the kernel SIGKILL appends "Killed"
    # on the same line, and ODM explicitly surfaces "Whoops! You ran out
    # of memory!" in its error block. Texturing memory is dominated by
    # the per-image working set, which the SfM/MVS quality knobs don't
    # touch — the practical lever is the ortho canvas size
    # (orthophoto-resolution) and the Docker memory cap.
    if "Whoops! You ran out of memory" in tail or (
        "Killed" in tail and "mvstex" in tail
    ):
        return (
            "out-of-memory during texturing (mvs_texturing). Retry with the "
            "Draft quality preset (5 cm/px ortho canvas), or raise Docker "
            "Desktop's Memory limit (Settings → Resources → Memory) to "
            "16 GiB+ if you need a higher tier."
        )

    # Out-of-disk on the NodeODM working volume.
    if "No space left on device" in tail or "ENOSPC" in tail:
        return (
            "NodeODM ran out of disk space. Free space on the Docker volume "
            "(`gemini-app_nodeodm_data`) or prune old tasks via the NodeODM "
            "admin UI."
        )

    # SfM bailed because images don't overlap enough or GPS metadata is bad.
    if "Not enough images" in tail or "Not enough features" in tail:
        return (
            "not enough overlapping features between images. ODM needs ~80% "
            "forward overlap; verify the flight plan or remove blurry frames."
        )
    if "could not be matched" in tail or "0 cameras matched" in tail:
        return (
            "ODM couldn't match any image pairs. Common causes: missing/wrong "
            "EXIF GPS, all images of the same point, or extreme lighting "
            "differences between frames."
        )

    # OpenMVS produced an empty dense cloud and then segfaulted. Two distinct
    # root causes converge on the same downstream symptoms, so disambiguate
    # by the OpenMVS self-reported memory line.
    #
    # Cause A (memory exhaustion): on Docker Desktop with a low memory/swap
    # cap, DensifyPointCloud reports something like
    #   "RAM: 7.65GB Physical Memory 1024.00MB Virtual Memory"
    # then either OOM-kills or — without enough swap to even fail cleanly —
    # produces 0 depthmaps and the next stage segfaults (exit 139) on the
    # empty input. No "Killed" appears in the log because the kernel didn't
    # SIGKILL anything; the process self-aborted on bad memory access.
    #
    # Cause B (preset too aggressive): on a Draft-class preset (pc-quality=
    # lowest) the densifier's view-selection step legitimately picks 0 of
    # N images and DensifyPointCloud segfaults on empty input. Plenty of
    # RAM available; just nothing to fuse.
    empty_cloud = (
        "Selecting images for dense reconstruction completed: 0 images" in tail
        or "no valid point-cloud for the ROI estimation" in tail
        or "Densifying point-cloud completed: 0 points" in tail
    )
    if empty_cloud:
        # Heuristic for cause A: a small virtual-memory figure on the
        # OpenMVS banner. Docker Desktop's default swap is 1 GiB; anything
        # at or below that with a segfault almost always means the engine
        # ran out of headroom mid-densification.
        low_vmem = False
        for line in log_lines[-200:]:
            if "Virtual Memory" not in line or "RAM:" not in line:
                continue
            # Line shape: "... RAM: 7.65GB Physical Memory 1024.00MB Virtual Memory"
            try:
                vmem_token = line.split("Physical Memory", 1)[1].strip().split()[0]
                value = float(vmem_token.rstrip("GBMmKkBb"))
                unit = vmem_token[-2:].upper()
                vmem_gib = value if unit.startswith("G") else value / 1024.0
                if vmem_gib <= 2.0:
                    low_vmem = True
                    break
            except (IndexError, ValueError):
                continue
        if low_vmem:
            return (
                "OpenMVS ran out of memory during dense reconstruction and "
                "segfaulted on the empty result. The Docker engine is likely "
                "capped too low (the log shows ~1 GiB virtual memory). Raise "
                "Docker Desktop's Memory to at least 16 GiB and Swap to ~4 "
                "GiB (Settings → Resources), then retry. As a workaround "
                "without changing Docker settings, retry at a lower "
                "Reconstruction quality."
            )
        return (
            "OpenMVS rejected every image during dense reconstruction — "
            "the quality preset is likely too aggressive for this dataset. "
            "Retry with a higher Reconstruction quality (e.g. Standard or "
            "High Quality instead of Draft), or pass `--depthmap-resolution "
            "640` and `--pc-quality low` via custom options."
        )

    # SfM placed cameras outside any plausible ROI and ODM saw a flipped Z
    # axis — usually an EXIF orientation / camera-model issue rather than a
    # quality-preset problem. Both warnings together strongly imply bad
    # metadata; the densification step then has no valid scene to fuse.
    if (
        "Negative GSD estimated" in tail
        and "scene will be considered unbounded" in tail
    ):
        return (
            "ODM couldn't establish a valid scene from the input EXIF "
            "(negative GSD + unbounded scene). Verify image orientation and "
            "GPS metadata, or strip and re-tag EXIF before re-uploading."
        )

    # GPU/CUDA path failed — uncommon but possible.
    if "CUDA" in tail and ("error" in tail.lower() or "failed" in tail.lower()):
        return "CUDA/GPU path crashed. Retry with CPU-only options."

    return ""


class OdmWorker(BaseWorker):
    """Worker for orthomosaic generation via NodeODM."""

    def __init__(self, worker_id: str = None):
        super().__init__(worker_id)
        self._nodeodm = NodeODMClient()

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.RUN_ODM}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        return self._run_odm(job_id, parameters)

    def _get_experiment_id(self, job_id: str) -> str | None:
        """Look up the parent job's `experiment_id` so chained child
        jobs (e.g. CREATE_COG) can inherit it. Required for the
        experiment-cascade delete to find and reap them — a job row
        with `experiment_id IS NULL` is invisible to the cascade.
        """
        try:
            resp = self._http.get(f"/api/jobs/{job_id}", timeout=5)
            if resp.status_code == 200:
                return resp.json().get("experiment_id")
        except Exception as e:
            logger.warning(f"Failed to look up experiment_id for {job_id}: {e}")
        return None

    def _run_odm(self, job_id: str, parameters: dict) -> dict:
        """
        Full ODM orthomosaic generation pipeline.

        1. Download images from MinIO
        2. Submit to NodeODM
        3. Poll for progress
        4. Download result
        5. Upload to MinIO
        6. Save log
        7. Cleanup
        """
        client = _get_minio_client()
        image_prefixes = _resolve_image_prefixes(parameters)
        scope_prefix = _build_scope_prefix(parameters)
        output_prefix = _build_output_prefix(parameters)

        # Parse ODM options. Precedence:
        #   1. Explicit `custom_options` string/list always wins — the user
        #      typed CLI flags into the textbox; honor them as-is.
        #   2. Otherwise apply the `reconstruction_quality` preset
        #      (Draft/Standard/High Quality/Ultra) merged into DEFAULT_OPTIONS.
        #   3. Fall back to DEFAULT_OPTIONS for `Custom` / unknown values
        #      (DEFAULT_OPTIONS is intentionally identical to Standard).
        custom = parameters.get("custom_options")
        quality = parameters.get("reconstruction_quality", "Standard")
        if isinstance(custom, str) and custom.strip():
            options = _parse_custom_options(custom)
            logger.info(f"Using user-supplied custom options: {options}")
        elif isinstance(custom, list) and custom:
            options = _parse_custom_options(custom)
            logger.info(f"Using user-supplied custom options: {options}")
        elif quality in QUALITY_PRESETS:
            options = _apply_quality_preset(quality)
            logger.info(f"Using quality preset {quality!r}: {options}")
        else:
            options = list(DEFAULT_OPTIONS)
            logger.info(f"Using default options (quality={quality!r}): {options}")

        with tempfile.TemporaryDirectory() as tmpdir:
            images_dir = os.path.join(tmpdir, "images")
            os.makedirs(images_dir)

            # Create initial log file so the frontend doesn't 404 while polling
            self._write_log_to_minio(
                ["Processing started..."], output_prefix, client
            )

            # Pull the optional Image Review exclusion list before the image
            # download so we never stage excluded frames locally. The filter
            # lives at the scope root (sibling of every dataset subdir) so a
            # single list applies across multi-dataset selections.
            excluded = self._load_image_filter(client, scope_prefix)
            if excluded:
                logger.info(
                    f"Excluding {len(excluded)} image(s) from job {job_id} per "
                    f"{IMAGE_FILTER_FILENAME}"
                )

            # Phase 1: Download images from MinIO (0-15%)
            self.report_progress(job_id, 2, {"stage": "downloading_images"})
            image_paths: list[str] = []
            for prefix in image_prefixes:
                image_paths.extend(
                    self._download_images(
                        client, prefix, images_dir, job_id, excluded=excluded
                    )
                )
            if not image_paths:
                raise RuntimeError(
                    "No images found in MinIO at "
                    f"{STORAGE_BUCKET}/{image_prefixes[0]}"
                    + (f" (+{len(image_prefixes) - 1} more)"
                       if len(image_prefixes) > 1 else "")
                )
            logger.info(
                f"Downloaded {len(image_paths)} images for job {job_id} "
                f"from {len(image_prefixes)} prefix(es)"
            )

            # Pull GCP sidecar files (gcp_list.txt, geo.txt) from the scope
            # root (sibling of every dataset subdir) so NodeODM can use
            # them. Absent files are skipped. When the user clicked
            # "Skip" in the GCP picker the frontend sends `skip_gcps:
            # true`; honor that even if the files are still sitting in
            # MinIO from a prior session — the UI state is the source
            # of truth, not the sidecars on disk.
            skip_gcps = bool(parameters.get("skip_gcps"))
            gcp_paths = (
                []
                if skip_gcps
                else self._download_gcp_files(client, scope_prefix, images_dir)
            )
            if skip_gcps:
                logger.info(
                    f"skip_gcps=true; not forwarding GCP sidecars to NodeODM "
                    f"for job {job_id}"
                )
            if gcp_paths:
                # Strip excluded images from geo.txt so NodeODM doesn't
                # complain about GPS rows for files we never staged.
                for p in gcp_paths:
                    if os.path.basename(p) == "geo.txt":
                        removed = self._filter_geo_txt(p, excluded)
                        if removed:
                            logger.info(
                                f"Removed {removed} excluded image row(s) from geo.txt"
                            )
                logger.info(
                    f"Forwarding GCP sidecars to NodeODM: "
                    f"{[os.path.basename(p) for p in gcp_paths]}"
                )

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Phase 2: Submit to NodeODM (15-20%)
            self.report_progress(job_id, 16, {
                "stage": "submitting_to_odm",
                "image_count": len(image_paths),
            })
            try:
                task_id = self._nodeodm.create_task(
                    image_paths, options, extra_files=gcp_paths
                )
            except Exception as e:
                raise RuntimeError(f"Failed to submit task to NodeODM: {e}") from e
            logger.info(f"NodeODM task created: {task_id}")

            self.report_progress(job_id, 20, {
                "stage": "odm_processing",
                "nodeodm_task_id": task_id,
            })

            # Phase 3: Poll for progress (20-85%)
            try:
                self._poll_nodeodm(job_id, task_id, tmpdir, output_prefix, client)
            except _CancelledError:
                self._cancel_and_remove_nodeodm_task(task_id)
                return {"status": "cancelled"}

            if self.is_cancelled(job_id):
                self._cancel_and_remove_nodeodm_task(task_id)
                return {"status": "cancelled"}

            # Phase 4: Download orthophoto result (85-90%)
            # NodeODM's /download/orthophoto.tif convenience URL is unreliable
            # (returns "Invalid asset" even when the ortho exists). Download
            # all.zip and extract the orthophoto from it instead.
            self.report_progress(job_id, 86, {"stage": "downloading_result"})
            ortho_path = os.path.join(tmpdir, "odm_orthophoto.tif")
            zip_path = os.path.join(tmpdir, "all.zip")
            try:
                self._nodeodm.download_result(task_id, "all.zip", zip_path)
            except Exception as e:
                raise RuntimeError(f"Failed to download results from NodeODM: {e}") from e

            # Extract orthophoto from zip
            import zipfile
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    ortho_entry = None
                    for name in zf.namelist():
                        if name.endswith("odm_orthophoto.tif"):
                            ortho_entry = name
                            break
                    if ortho_entry is None:
                        raise RuntimeError(
                            "NodeODM did not produce an orthophoto. "
                            "The images may not have enough overlap or features."
                        )
                    with zf.open(ortho_entry) as src, open(ortho_path, "wb") as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
            except zipfile.BadZipFile:
                raise RuntimeError("NodeODM returned invalid zip file")

            ortho_size = os.path.getsize(ortho_path)
            if ortho_size < 1024:
                raise RuntimeError(
                    f"NodeODM produced an invalid orthophoto ({ortho_size} bytes). "
                    "The images may not have enough overlap or features for reconstruction."
                )
            logger.info(f"Extracted orthophoto: {ortho_size:,} bytes")

            # Phase 5: Upload orthophoto to MinIO (90-95%)
            # Filename includes the job_id so re-runs don't overwrite prior
            # versions — buildOrthoVersions on the frontend (and the geo
            # worker's SPLIT_ORTHOMOSAIC discovery) recognize any
            # `odm_orthophoto*.tif` as a version of this ortho.
            self.report_progress(job_id, 91, {"stage": "uploading_result"})
            ortho_object_path = f"{output_prefix}odm_orthophoto-{job_id}.tif"
            client.fput_object(
                STORAGE_BUCKET,
                ortho_object_path,
                ortho_path,
                content_type="image/tiff",
            )
            logger.info(f"Uploaded orthophoto to {ortho_object_path}")

            # Phase 6: Save final log to MinIO (95-98%)
            self.report_progress(job_id, 96, {"stage": "saving_log"})
            self._save_log(task_id, output_prefix, client)

            # Phase 7: Submit CREATE_COG job for tile serving (96-98%)
            self.report_progress(job_id, 97, {"stage": "submitting_cog_job"})
            cog_job_id = self._submit_cog_job(
                ortho_object_path,
                experiment_id=self._get_experiment_id(job_id),
            )
            if cog_job_id:
                logger.info(f"Submitted CREATE_COG job {cog_job_id} for {ortho_object_path}")

            # Phase 8: Cleanup NodeODM task (98-100%)
            self.report_progress(job_id, 99, {"stage": "cleanup"})
            self._remove_nodeodm_task(task_id)

            result = {
                "orthophoto_path": ortho_object_path,
                "image_count": len(image_paths),
            }
            if cog_job_id:
                result["cog_job_id"] = cog_job_id
            return result

    def _download_images(
        self,
        client,
        prefix: str,
        dest_dir: str,
        job_id: str,
        excluded: Set[str] | None = None,
    ) -> list[str]:
        """Download all image files from MinIO prefix to a local directory.

        Recursive listing: when the caller passes the scope-root prefix
        (multi-dataset / legacy "all datasets at this scope" mode), this
        walks every `…/{shortId}/Images/...` subdirectory plus any
        legacy `…/Images/...` files. Restricts to keys under an
        `Images/` segment so siblings (`gcp_list.txt`, `RawThermal/...`,
        `Orthomosaic/...`) don't get pulled in.

        `excluded` is an optional set of basenames the user marked for
        exclusion via the Image Review step (image_filter.txt). Listed
        images are silently skipped here and removed from geo.txt by
        the caller before NodeODM sees either.
        """
        excluded = excluded or set()
        objects = list(
            client.list_objects(STORAGE_BUCKET, prefix=prefix, recursive=True)
        )
        image_objects = [
            obj
            for obj in objects
            if os.path.splitext(obj.object_name)[1].lower() in IMAGE_EXTENSIONS
            and "/Images/" in obj.object_name
            and os.path.basename(obj.object_name) not in excluded
        ]

        paths = []
        total = len(image_objects)
        for i, obj in enumerate(image_objects):
            if self.is_cancelled(job_id):
                return paths

            filename = os.path.basename(obj.object_name)
            local_path = os.path.join(dest_dir, filename)
            if os.path.exists(local_path):
                # Cross-dataset basename collision (two uploads with the
                # same `IMG_001.jpg`). NodeODM and the user-supplied
                # geo.txt are both keyed on basename — silent overwrite
                # would mean unpredictable GPS pairing. Fail loud.
                raise RuntimeError(
                    f"Duplicate image basename {filename!r} across datasets "
                    f"(collision at {obj.object_name}). Rename one of the "
                    "colliding files or run ODM against a single dataset."
                )
            client.fget_object(STORAGE_BUCKET, obj.object_name, local_path)
            paths.append(local_path)

            # Map download progress to 2-15% range. Round before sending so
            # the frontend doesn't render "3.2729970326409497%".
            progress = round(2 + (13 * (i + 1) / total))
            if (i + 1) % max(1, total // 10) == 0 or i == total - 1:
                self.report_progress(job_id, progress, {
                    "stage": "downloading_images",
                    "downloaded": i + 1,
                    "total": total,
                })

        return paths

    def _download_gcp_files(
        self, client, prefix: str, dest_dir: str
    ) -> list[str]:
        """
        Download the GCP picker's sidecars (gcp_list.txt, geo.txt) from MinIO
        if they exist at the scope root (sibling of every dataset subdir).
        Pre-migration uploads stored these alongside the images
        (`…/{sensor}/Images/`); post-migration they live one level up
        (`…/{sensor}/`) so a single set applies across multi-dataset
        selections. NodeODM auto-detects both filenames when they are
        present in the input set.
        """
        paths: list[str] = []
        for filename in GCP_SIDECAR_FILENAMES:
            object_name = f"{prefix.rstrip('/')}/{filename}"
            local_path = os.path.join(dest_dir, filename)
            try:
                client.fget_object(STORAGE_BUCKET, object_name, local_path)
            except Exception as exc:  # noqa: BLE001
                # Missing files are expected when the user skipped GCP picking;
                # other failures we just skip and log so the job still runs.
                logger.debug(
                    f"GCP sidecar {filename} not pulled from {object_name}: {exc}"
                )
                continue
            paths.append(local_path)
        return paths

    def _load_image_filter(self, client, prefix: str) -> Set[str]:
        """Read the optional image_filter.txt sidecar and return the set
        of excluded basenames. Returns an empty set if the file is absent
        or unreadable. Reads from the scope root (sibling of every
        dataset subdir) so a single exclusion list applies across
        multi-dataset selections.

        Format: one basename per line; lines starting with `#` are comments.
        """
        object_name = f"{prefix.rstrip('/')}/{IMAGE_FILTER_FILENAME}"
        try:
            response = client.get_object(STORAGE_BUCKET, object_name)
            try:
                text = response.read().decode("utf-8", errors="replace")
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                f"image_filter.txt not pulled from {object_name}: {exc}"
            )
            return set()
        excluded: Set[str] = set()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            excluded.add(line)
        return excluded

    def _filter_geo_txt(self, geo_txt_path: str, excluded: Set[str]) -> int:
        """Rewrite a downloaded geo.txt in-place, dropping rows whose
        first whitespace-separated token (the image filename) is in
        `excluded`. Returns the number of rows removed.
        """
        if not excluded or not os.path.exists(geo_txt_path):
            return 0
        with open(geo_txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        kept: list[str] = []
        removed = 0
        for line in lines:
            stripped = line.strip()
            # Preserve header/comment/blank lines untouched.
            if not stripped or stripped.startswith("#") or stripped.startswith("EPSG"):
                kept.append(line)
                continue
            first = stripped.split()[0]
            if first in excluded:
                removed += 1
                continue
            kept.append(line)
        with open(geo_txt_path, "w", encoding="utf-8") as f:
            f.writelines(kept)
        return removed

    def _poll_nodeodm(
        self, job_id: str, task_id: str, tmpdir: str, output_prefix: str, client
    ):
        """
        Poll NodeODM for task progress, mapping to 20-85% range.

        Periodically saves log to MinIO so the frontend can display it.
        Raises _CancelledError if the job is cancelled.
        Fails the job after MAX_POLL_FAILURES consecutive poll errors.
        """
        log_line_offset = 0
        log_buffer = []
        last_log_save = time.time()
        log_save_interval = 5  # seconds
        consecutive_failures = 0

        # Smoothing state for the chunky NodeODM `progress` field — see
        # `_smooth_progress` for the rationale. Without this the UI bar
        # appears frozen on the long opensfm/openmvs plateaus.
        #
        # Plateau is tracked against the *UI segment ceiling*, not the raw
        # ODM progress value. NodeODM emits `progress` as a float that
        # walks in tiny sub-percent steps inside a single ODM stage
        # (e.g. opensfm: 5.0 → 5.4 → 6.6 → 7.2), and resetting on every
        # tick zeros out `plateau_elapsed` before the asymptotic creep
        # ever accumulates — leaving the bar visually stuck. Resetting
        # only on segment crossings (dataset → opensfm → openmvs → tail)
        # lets creep run within a stage while still re-seating the
        # creep window when ODM enters a genuinely new phase.
        prev_segment_ceiling: float | None = None
        plateau_start = time.time()
        last_smoothed = 0.0

        while True:
            if self.is_cancelled(job_id):
                raise _CancelledError()

            try:
                info = self._nodeodm.get_task_info(task_id)
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                logger.warning(
                    f"Failed to get NodeODM task info ({consecutive_failures}/{MAX_POLL_FAILURES}): {e}"
                )
                if consecutive_failures >= MAX_POLL_FAILURES:
                    if log_buffer:
                        self._write_log_to_minio(log_buffer, output_prefix, client)
                    raise RuntimeError(
                        f"NodeODM unreachable after {consecutive_failures} attempts: {e}"
                    ) from e
                time.sleep(POLL_INTERVAL)
                continue

            status_code = info.get("status", {}).get("code", 0)
            odm_progress = info.get("progress", 0)

            # Fetch new log lines (get_task_output returns a list)
            try:
                new_lines = self._nodeodm.get_task_output(task_id, line=log_line_offset)
                if new_lines:
                    log_buffer.extend(new_lines)
                    log_line_offset += len(new_lines)
            except Exception:
                pass

            # Map ODM progress (0-100) to our 20-85 range. NodeODM's `progress`
            # field is the linear sum of ODM stage weights from
            # /code/stages/odm_app.py (dataset 0-5, opensfm 5-25, openmvs 25-50,
            # filterpoints/meshing/texturing/geo/dem 50-90, ortho 90-98). The
            # opensfm and openmvs stages routinely consume ~70% of wall-clock
            # time but only span 5-50 in ODM's own progress, so a linear remap
            # makes the UI bar appear stuck in the low 20s for most of the run.
            # `_remap_odm_progress` widens those slow segments; `_smooth_progress`
            # then asymptotically creeps within each segment so the bar keeps
            # visibly moving while NodeODM sits on the same chunk.
            now = time.time()
            current_ceiling = _segment_ceiling(odm_progress)
            if prev_segment_ceiling is None or current_ceiling != prev_segment_ceiling:
                plateau_start = now
                prev_segment_ceiling = current_ceiling
            plateau_elapsed = now - plateau_start
            smoothed = _smooth_progress(
                odm_progress, plateau_elapsed, last_smoothed
            )
            last_smoothed = smoothed
            mapped_progress = round(smoothed)

            log_tail = log_buffer[-5:] if log_buffer else []
            self.report_progress(job_id, mapped_progress, {
                "stage": "odm_processing",
                "odm_status_code": status_code,
                "odm_progress": odm_progress,
                "processing_time": info.get("processingTime", 0),
                "log_tail": log_tail,
            })

            # Periodically save log to MinIO
            if time.time() - last_log_save > log_save_interval and log_buffer:
                self._write_log_to_minio(log_buffer, output_prefix, client)
                last_log_save = time.time()

            if status_code == STATUS_COMPLETED:
                break
            elif status_code == STATUS_FAILED:
                generic_msg = info.get("status", {}).get("errorMessage", "Unknown ODM error")
                # Save final log before failing.
                if log_buffer:
                    self._write_log_to_minio(log_buffer, output_prefix, client)
                # NodeODM's `errorMessage` is almost always the generic
                # "Cannot process dataset". The real cause lives in the task
                # log — scan the tail for the common signatures so the user
                # gets an actionable message instead of digging through MinIO.
                # When no pattern matches, point the user at the saved log
                # so they (or support) can read it without docker-exec'ing.
                detail = _diagnose_odm_failure(log_buffer)
                log_pointer = (
                    f"Full ODM log: {STORAGE_BUCKET}/{output_prefix}odm_log.txt"
                )
                if detail:
                    raise RuntimeError(
                        f"ODM processing failed: {generic_msg} — "
                        f"likely cause: {detail}\n{log_pointer}"
                    )
                raise RuntimeError(
                    f"ODM processing failed: {generic_msg}. The failure "
                    f"signature isn't one we recognize automatically — "
                    f"check the saved log for the underlying error.\n"
                    f"{log_pointer}"
                )
            elif status_code == STATUS_CANCELLED:
                raise _CancelledError()

            time.sleep(POLL_INTERVAL)

        # Save final log
        if log_buffer:
            self._write_log_to_minio(log_buffer, output_prefix, client)

    def _save_log(self, task_id: str, output_prefix: str, client):
        """Fetch the complete log from NodeODM and save to MinIO."""
        try:
            log_lines = self._nodeodm.get_task_output(task_id, line=0)
            if log_lines:
                self._write_log_to_minio(log_lines, output_prefix, client)
        except Exception as e:
            logger.warning(f"Failed to save final ODM log: {e}")

    def _write_log_to_minio(self, log_lines: list[str], output_prefix: str, client):
        """Write log lines to MinIO as odm_log.txt."""
        import io

        log_text = "\n".join(log_lines)
        log_bytes = log_text.encode("utf-8")
        log_path = f"{output_prefix}odm_log.txt"
        client.put_object(
            STORAGE_BUCKET,
            log_path,
            io.BytesIO(log_bytes),
            len(log_bytes),
            content_type="text/plain",
        )

    def _cancel_and_remove_nodeodm_task(self, task_id: str):
        """Cancel a running/queued NodeODM task, then remove it."""
        try:
            self._nodeodm.cancel_task(task_id)
        except Exception:
            pass
        self._remove_nodeodm_task(task_id)

    def _submit_cog_job(
        self, ortho_path: str, experiment_id: str | None = None,
    ) -> str:
        """Submit a CREATE_COG job to convert the orthophoto to a tiled pyramid for map display."""
        try:
            payload: dict = {
                "job_type": "CREATE_COG",
                "parameters": {"input_path": ortho_path},
            }
            if experiment_id:
                payload["experiment_id"] = experiment_id
            resp = self._http.post(
                "/api/jobs/submit",
                json=payload,
            )
            if resp.status_code in (200, 201):
                return str(resp.json().get("id", ""))
            else:
                logger.warning(f"Failed to submit CREATE_COG job: {resp.status_code} {resp.text}")
                return ""
        except Exception as e:
            logger.warning(f"Failed to submit CREATE_COG job: {e}")
            return ""

    def _remove_nodeodm_task(self, task_id: str):
        """Remove a completed/failed NodeODM task to free resources."""
        try:
            self._nodeodm.remove_task(task_id)
        except Exception:
            pass


class _CancelledError(Exception):
    """Internal signal for job cancellation."""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = OdmWorker()
    worker.run()
