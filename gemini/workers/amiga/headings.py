"""
Direction of travel for Amiga GPS tracks (ported from GEMINI-App main).

Kept apart from bin_to_images so code without the extractor's heavy
dependencies (cv2, kornia, farm-ng) can label a msgs_synced.csv that was
uploaded rather than extracted: `add_direction_columns`.

    direction_raw  — per-row compass bucket of the lat/lon bearing
    direction      — the same, smoothed per recording segment
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def heading_to_direction(heading):
    if heading is not None:
        # Convert radians to degrees
        heading_deg = np.degrees(heading) % 360  # Ensure 0-360 range
        
        if (heading_deg > 315 or heading_deg <= 45):
            return 'North'
        elif (heading_deg > 45 and heading_deg <= 135):
            return 'East'
        elif (heading_deg > 135 and heading_deg <= 225):
            return 'South'
        elif (heading_deg > 225 and heading_deg <= 315):
            return 'West'
    else:
        return None

def compute_latlon_bearing(lat: pd.Series, lon: pd.Series, stride: int = 5) -> pd.Series:
    """
    Compute direction of travel from lat/lon using a strided baseline.

    Rather than measuring bearing frame-to-frame (noisy at low speed), each
    row's bearing is computed from the position `stride` rows behind to the
    position `stride` rows ahead. This longer baseline averages out GPS
    positional noise before any further smoothing is applied.

    Returns a Series of bearings in radians (same unit as heading_motion),
    measured clockwise from North, range [-π, π].
    """
    lat_r = np.radians(pd.to_numeric(lat, errors='coerce'))
    lon_r = np.radians(pd.to_numeric(lon, errors='coerce'))

    lat_from = lat_r.shift(stride)
    lon_from = lon_r.shift(stride)
    lat_to   = lat_r.shift(-stride)
    lon_to   = lon_r.shift(-stride)

    d_lon = lon_to - lon_from
    x = np.sin(d_lon) * np.cos(lat_to)
    y = np.cos(lat_from) * np.sin(lat_to) - np.sin(lat_from) * np.cos(lat_to) * np.cos(d_lon)
    bearing = np.arctan2(x, y)  # radians, clockwise from North

    # Fill edges (first/last `stride` rows) with nearest valid interior value
    bearing = bearing.ffill().bfill()
    return bearing


def _smooth_segment(heading_segment: pd.Series, window: int, min_run: int) -> pd.Series:
    """Apply circular rolling mean + min-run-length filter to one continuous segment."""
    sin_s = np.sin(heading_segment).rolling(window, center=True, min_periods=1).mean()
    cos_s = np.cos(heading_segment).rolling(window, center=True, min_periods=1).mean()
    smoothed_rad = np.arctan2(sin_s, cos_s)
    directions = smoothed_rad.apply(heading_to_direction)

    labels = directions.tolist()
    n = len(labels)
    i = 0
    while i < n:
        j = i
        while j < n and labels[j] == labels[i]:
            j += 1
        if (j - i) < min_run:
            prev_dir = labels[i - 1] if i > 0 else None
            next_dir = labels[j] if j < n else None
            if prev_dir is not None and prev_dir == next_dir:
                for k in range(i, j):
                    labels[k] = prev_dir
        i = j

    return pd.Series(labels, index=directions.index)


def smooth_headings(
    heading_series: pd.Series,
    stamp_series: pd.Series | None = None,
    window: int = 15,
    min_run: int = 7,
    gap_threshold_s: float = 5.0,
) -> pd.Series:
    """
    Segment-aware heading smoother.

    Recordings that are stopped and resumed produce hard direction changes
    (e.g. North → South) that should never be blurred together. This function
    detects those gaps from the timestamp column and applies the two-stage
    filter independently within each continuous recording segment so that a
    real direction reversal is always preserved.

    Stage 1 — circular rolling mean (per segment):
      Converts heading_motion radians to unit vectors (sin θ, cos θ), applies
      a rolling mean of `window` frames centered on each row, then atan2 back.
      Handles 0/360 wraparound and eliminates GPS jitter before bucketing.

    Stage 2 — minimum run-length filter (per segment):
      Isolated direction islands shorter than `min_run` frames that are
      surrounded on both sides by the same other direction are collapsed.

    Parameters
    ----------
    heading_series   Raw heading_motion column (radians).
    stamp_series     Timestamp column (seconds). Used to detect recording gaps.
                     If None, the whole series is treated as one segment.
    window           Rolling-mean half-width in frames (default 15).
    min_run          Minimum frames for a direction change to be kept (default 7).
    gap_threshold_s  Timestamp gap in seconds that marks a new segment (default 5 s).
    """
    if stamp_series is None or len(heading_series) == 0:
        return _smooth_segment(heading_series, window, min_run)

    # Identify segment boundaries: gaps larger than gap_threshold_s
    stamps = pd.to_numeric(stamp_series, errors='coerce')
    deltas = stamps.diff().fillna(0)
    segment_ids = (deltas > gap_threshold_s).cumsum()

    result = pd.Series(index=heading_series.index, dtype=object)
    for _, seg_idx in heading_series.groupby(segment_ids).groups.items():
        seg = heading_series.loc[seg_idx]
        result.loc[seg_idx] = _smooth_segment(seg, window, min_run).values

    return result


def add_direction_columns(df: pd.DataFrame) -> bool:
    """Add direction_raw / direction to a msgs_synced frame in place.

    Uses the lat/lon bearing (main's choice: steadier than heading_motion
    at low speed), falling back to heading_motion. Returns False if the
    frame has neither.
    """
    lat_col = next((c for c in df.columns if c.lower() in ("lat", "latitude")), None)
    lon_col = next((c for c in df.columns if c.lower() in ("lon", "lng", "longitude")), None)
    if lat_col and lon_col:
        bearing = compute_latlon_bearing(df[lat_col], df[lon_col])
    elif "heading_motion" in df.columns:
        bearing = df["heading_motion"]
    else:
        return False
    stamp_s = (
        pd.to_numeric(df["stamp"], errors="coerce") / 1e6 if "stamp" in df.columns else None
    )
    df["direction_raw"] = bearing.apply(heading_to_direction)
    df["direction"] = smooth_headings(bearing, stamp_series=stamp_s, window=50, min_run=26)
    return True
