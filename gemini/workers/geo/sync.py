"""
Data Sync (ported from GEMINI-App main, backend/app/processing/sync.py):
give every image of a run a capture time and a position.

    own metadata   each image's EXIF GPS + time, refined by any ArduPilot
                   platform logs (.bin/.log/.tlog) uploaded to Metadata/ —
                   a log fix within 5 s of the capture replaces the EXIF one,
                   and a rangefinder height beats GPS altitude
    cross-sensor   positions interpolated from another sensor's synced track
                   (e.g. the Amiga's RTK GPS for a phone camera riding on
                   it) at each image's capture time

Pure functions here; the DATA_SYNC job (worker.py) does the I/O.
Unlike main, images are never rotated and rewritten: the raw upload is
the user's data (ODM honours the EXIF orientation itself).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

LOG_EXTS = (".bin", ".log", ".tlog")

# Column aliases for a user- or extractor-written msgs_synced.csv (main's).
COL_ALIASES: dict[str, list[str]] = {
    "image_path": ["image_path", "image", "filename", "file", "name", "path",
                   "/top/rgb_file", "/top/rgb", "/left/rgb_file", "/right/rgb_file"],
    "timestamp": ["timestamp", "unix_time", "unix_ts", "epoch", "posix", "ts"],
    "lat": ["lat", "latitude"],
    "lon": ["lon", "long", "lng", "longitude"],
    "alt": ["alt", "altitude", "height", "elevation"],
}


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}
    rename: dict[str, str] = {}
    for target, aliases in COL_ALIASES.items():
        if target in df.columns:
            continue
        for alias in aliases:
            if alias in lower and lower[alias] not in rename.values():
                rename[lower[alias]] = target
                break
    return df.rename(columns=rename) if rename else df


# ── EXIF ────────────────────────────────────────────────────────────────────


def _ratio(v) -> float:
    try:
        return float(v)
    except TypeError:
        return v[0] / v[1]


def exif_record(blob: bytes) -> dict:
    """{timestamp, lat, lon, alt} from an image's EXIF (None where absent).

    Time: the GPS UTC date/time tags first (what main uses), else
    DateTimeOriginal/Digitized/DateTime read as UTC.
    """
    from PIL import Image

    rec: dict = {"timestamp": None, "lat": None, "lon": None, "alt": None}
    try:
        with Image.open(io.BytesIO(blob)) as img:
            exif = img.getexif()
            gps = exif.get_ifd(34853) or {}
            sub = exif.get_ifd(34665) or {}
    except Exception:
        return rec
    try:
        if 2 in gps and 4 in gps:
            lat = sum(_ratio(x) / 60 ** i for i, x in enumerate(gps[2]))
            lon = sum(_ratio(x) / 60 ** i for i, x in enumerate(gps[4]))
            rec["lat"] = -lat if gps.get(1) == "S" else lat
            rec["lon"] = -lon if gps.get(3) == "W" else lon
            if 6 in gps:
                alt = _ratio(gps[6])
                rec["alt"] = -alt if gps.get(5) in (1, b"\x01") else alt
    except Exception:
        pass
    if gps.get(29) and gps.get(7):
        try:
            h, m, s = (_ratio(x) for x in gps[7])
            day = datetime.strptime(str(gps[29]), "%Y:%m:%d").replace(tzinfo=timezone.utc)
            rec["timestamp"] = day.timestamp() + h * 3600 + m * 60 + s
        except Exception:
            pass
    if rec["timestamp"] is None:
        for tag in (36867, 36868):
            v = sub.get(tag)
            if v:
                break
        else:
            v = exif.get(306)
        if v:
            try:
                dt = datetime.strptime(str(v)[:19], "%Y:%m:%d %H:%M:%S")
                rec["timestamp"] = dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
    return rec


# ── ArduPilot logs ──────────────────────────────────────────────────────────


def _nearest(times: np.ndarray, t: float, tol: float) -> Optional[int]:
    if times.size == 0:
        return None
    i = int(np.searchsorted(times, t))
    best = min(
        (j for j in (i - 1, i) if 0 <= j < times.size),
        key=lambda j: abs(times[j] - t),
    )
    return best if abs(times[best] - t) <= tol else None


def parse_platform_log(path: str) -> pd.DataFrame:
    """GPS fixes from an ArduPilot DataFlash/telemetry log (main's parser):
    timestamp, lat, lon, alt, gps_alt, rangefinder_distance, alt_source,
    roll, pitch, yaw. A rangefinder reading within 1 s gives height above
    ground, which beats GPS altitude."""
    from pymavlink import mavutil

    mlog = mavutil.mavlink_connection(path)
    gps, rf, att = [], [], []
    while True:
        msg = mlog.recv_match(blocking=False)
        if msg is None:
            break
        t = msg.get_type()
        if t == "GPS" and getattr(msg, "Lat", None) and getattr(msg, "Lng", None):
            gps.append((msg._timestamp, msg.Lat, msg.Lng, getattr(msg, "Alt", None)))
        elif t == "RFND":
            rf.append((msg._timestamp, getattr(msg, "Dist", None)))
        elif t == "ATT":
            att.append((msg._timestamp, getattr(msg, "Roll", None),
                        getattr(msg, "Pitch", None), getattr(msg, "Yaw", None)))
    if not gps:
        return pd.DataFrame()
    rf.sort()
    att.sort()
    rf_t = np.array([r[0] for r in rf], dtype=float)
    att_t = np.array([a[0] for a in att], dtype=float)
    rows = []
    for ts, lat, lon, alt in gps:
        j = _nearest(rf_t, ts, 1.0)
        dist = rf[j][1] if j is not None else None
        k = _nearest(att_t, ts, 1.0)
        roll, pitch, yaw = att[k][1:] if k is not None else (None, None, None)
        gps_alt = float(alt) if alt is not None else None
        if dist is not None and float(dist) > 0:
            height, source = round(float(dist), 2), "rangefinder"
        elif gps_alt is not None:
            height, source = round(gps_alt, 2), "gps"
        else:
            height, source = None, None
        rows.append({
            "timestamp": round(float(ts), 6), "lat": float(lat), "lon": float(lon),
            "alt": height, "gps_alt": gps_alt,
            "rangefinder_distance": float(dist) if dist is not None else None,
            "alt_source": source, "roll": roll, "pitch": pitch, "yaw": yaw,
        })
    return pd.DataFrame(rows)


def merge_log_gps(images: pd.DataFrame, log: pd.DataFrame, max_diff: float = 5.0) -> pd.DataFrame:
    """Replace each image's position with the nearest log fix within
    max_diff seconds (main's _merge_drone_gps)."""
    out = images.copy()
    if log.empty or "timestamp" not in out:
        return out
    log = log.dropna(subset=["timestamp"]).sort_values("timestamp")
    times = log["timestamp"].to_numpy(dtype=float)
    for i, row in out.iterrows():
        if pd.isna(row.get("timestamp")):
            continue
        j = _nearest(times, float(row["timestamp"]), max_diff)
        if j is None:
            continue
        fix = log.iloc[j]
        out.at[i, "lat"] = fix["lat"]
        out.at[i, "lon"] = fix["lon"]
        if pd.notna(fix.get("alt")):
            out.at[i, "alt"] = fix["alt"]
        out.at[i, "gps_source"] = "platform_log"
    return out


# ── Cross-sensor ────────────────────────────────────────────────────────────


def reference_track(df: pd.DataFrame) -> pd.DataFrame:
    """timestamp/lat/lon/alt rows of a synced track, sorted by time."""
    df = normalise_columns(df)
    if "timestamp" not in df and "gps_time" in df:
        df["timestamp"] = pd.to_numeric(df["gps_time"], errors="coerce") / 1e6
    for c in ("timestamp", "lat", "lon"):
        if c not in df:
            raise ValueError(f"reference track has no {c} column")
    ref = pd.DataFrame({
        "timestamp": pd.to_numeric(df["timestamp"], errors="coerce"),
        "lat": pd.to_numeric(df["lat"], errors="coerce"),
        "lon": pd.to_numeric(df["lon"], errors="coerce"),
        "alt": pd.to_numeric(df["alt"], errors="coerce") if "alt" in df else 0.0,
    }).dropna(subset=["timestamp", "lat", "lon"])
    if ref.empty:
        raise ValueError("reference track has no rows with a time and a position")
    return ref.sort_values("timestamp").reset_index(drop=True)


def cross_sensor(images: pd.DataFrame, ref: pd.DataFrame, max_extrapolation: float = 30.0) -> pd.DataFrame:
    """Each image's position from the reference track at its capture time
    (main's run_cross_sensor_sync):

        inside the track's time span      → interpolated
        within max_extrapolation outside  → the track's nearest end (clamped)
        beyond, image has its own GPS      → kept (own_gps)
        beyond, no GPS                     → none
    """
    out = images.copy()
    t = ref["timestamp"].to_numpy(dtype=float)
    lo, hi = t[0], t[-1]
    for i, row in out.iterrows():
        ts = row.get("timestamp")
        has_own = pd.notna(row.get("lat")) and pd.notna(row.get("lon"))
        if pd.notna(ts) and lo <= float(ts) <= hi:
            ts = float(ts)
            for c in ("lat", "lon", "alt"):
                out.at[i, c] = float(np.interp(ts, t, ref[c].to_numpy(dtype=float)))
            out.at[i, "gps_source"] = "interpolated"
        elif pd.notna(ts) and min(abs(float(ts) - lo), abs(float(ts) - hi)) <= max_extrapolation:
            end = 0 if float(ts) < lo else -1
            for c in ("lat", "lon", "alt"):
                out.at[i, c] = float(ref[c].iloc[end])
            out.at[i, "gps_source"] = "clamped"
        else:
            out.at[i, "gps_source"] = "own_gps" if has_own else "none"
    return out


def geo_txt(df: pd.DataFrame) -> str:
    """ODM's image geolocation file (EPSG:4326)."""
    lines = ["EPSG:4326"]
    for _, r in df.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
            alt = r["alt"] if pd.notna(r.get("alt")) else 0
            lines.append(f"{r['image']} {r['lon']} {r['lat']} {alt} 0 0 0 0 0")
    return "\n".join(lines) + "\n"
