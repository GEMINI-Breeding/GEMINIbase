"""
Pure planning for RUN_STITCH: which frames make up each plot, which crop
rule applies to it, and the AgRowStitch config it runs with. Ported from
GEMINI-App main's ground.run_stitching; kept free of AgRowStitch, torch
and MinIO so it can be unit-tested.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

# UI direction → AgRowStitch stitching_direction (legacy names included,
# as main accepts them).
DIRECTION_MAP = {
    "down": "DOWN",
    "up": "UP",
    "left": "LEFT",
    "right": "RIGHT",
    "north_to_south": "DOWN",
    "south_to_north": "UP",
    "east_to_west": "LEFT",
    "west_to_east": "RIGHT",
}

# The only keys AgRowStitch.load_config accepts — any other key is a
# KeyError inside AgRowStitch, so unknown ones are dropped (and reported).
AGROWSTITCH_KEYS = {
    "image_directory", "parent_directory", "save_output", "device",
    "batch_size", "final_resolution", "seam_resolution",
    "stitching_direction", "mask", "camera", "GPS", "keypoint_prop",
    "forward_limit", "xy_ratio", "scale_constraint", "min_inliers",
    "max_RANSAC_thresh", "max_reprojection_error", "final_straighten",
    "change_orientation", "save_full_resolution", "save_resized_resolution",
    "final_size", "crop_size", "save_low_resolution", "low_resolution",
    "verbose", "points_per_image", "straightening_threshold",
}

# Knobs the pipeline settings expose directly (main's agrowstitch_params).
STRUCTURED_KEYS = ("forward_limit", "max_reprojection_error", "batch_size", "min_inliers")


def image_column(df: pd.DataFrame) -> Optional[str]:
    """The msgs_synced column naming each row's top-camera frame."""
    col = next((c for c in df.columns if "top" in c.lower() and "file" in c.lower()), None)
    if col:
        return col
    col = next(
        (c for c in df.columns if c.lower() in ("image_path", "image", "filename", "file", "path")),
        None,
    )
    if col:
        return col
    return next((c for c in df.columns if "file" in c.lower() or "path" in c.lower()), None)


def basenames(df: pd.DataFrame) -> pd.Series:
    col = image_column(df)
    if col is None:
        raise ValueError(
            "msgs_synced.csv has no image column (expected e.g. /top/rgb_file)."
        )
    return df[col].apply(
        lambda v: str(v).replace("\\", "/").split("/")[-1] if pd.notna(v) and str(v) else ""
    )


def plot_rows(df: pd.DataFrame, names: pd.Series, start: str, end: str) -> pd.DataFrame:
    """Rows from the plot's start frame to its end frame, in capture order.

    Either order of marking works (end before start is swapped). Raises if
    a marked frame isn't in this track.
    """
    s = names == start
    e = names == end
    missing = [n for n, m in ((start, s), (end, e)) if not m.any()]
    if missing:
        raise ValueError(f"marked frame(s) not in this track: {', '.join(missing)}")
    si = df.index[s][0]
    ei = df.index[e][-1]
    if si > ei:
        si, ei = df.index[e][0], df.index[s][-1]
    return df.loc[si:ei]


def _rule_mask(rule: dict) -> List[int]:
    return [
        int(rule.get("mask_left", 0)),
        int(rule.get("mask_right", 0)),
        int(rule.get("mask_top", 0)),
        int(rule.get("mask_bottom", 0)),
    ]


def dominant_heading(rows: pd.DataFrame) -> str:
    if "direction" not in rows.columns:
        return ""
    mode = rows["direction"].dropna().astype(str).str.strip().str.lower().mode()
    return mode.iloc[0] if not mode.empty else ""


def choose_crop_mask(
    crop_rules: Optional[List[dict]], ui_direction: str, heading: str
) -> Optional[List[int]]:
    """The mask of the first crop rule that matches this plot, as main does.

    A "heading" rule matches the plot's dominant GPS heading (north/east/…);
    any other rule matches its marked stitching direction. A rule with no
    headings/directions listed matches every plot.
    """
    for rule in crop_rules or []:
        if rule.get("filterMode", "heading") == "heading":
            wanted = [h.lower() for h in (rule.get("headings") or [])]
            if not wanted or (heading and heading in wanted):
                return _rule_mask(rule)
        else:
            wanted = [d.lower() for d in (rule.get("directions") or [])]
            if not wanted or ui_direction.lower() in wanted:
                return _rule_mask(rule)
    return None


def default_mask(params: dict) -> Optional[List[int]]:
    """Pipeline-wide mask: the rule without directions, or legacy flat keys."""
    rules = params.get("crop_rules")
    if rules:
        rule = next((r for r in rules if not r.get("directions")), rules[0])
        return _rule_mask(rule)
    if {"mask_left", "mask_right", "mask_top", "mask_bottom"} & set(params):
        return _rule_mask(params)
    return None


def build_base_config(
    defaults: dict, params: dict, custom: Optional[dict] = None
) -> tuple[Dict[str, Any], List[str]]:
    """AgRowStitch's own defaults, then the pipeline's knobs, then any custom
    options. Returns (config, dropped_keys)."""
    config = dict(defaults)
    mask = default_mask(params)
    if mask is not None:
        config["mask"] = mask
    for k in STRUCTURED_KEYS:
        if params.get(k) is not None:
            config[k] = params[k]
    if custom:
        config.update(custom)
    dropped = sorted(k for k in config if k not in AGROWSTITCH_KEYS)
    for k in dropped:
        config.pop(k)
    return config, dropped
