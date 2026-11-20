"""
Data Sync (ported from GEMINI-App main, backend/app/processing/sync.py):
give every image of a run a capture time and a position.

    own metadata   each image's EXIF GPS + time, refined by any GPS log
                   uploaded to Metadata/: an ArduPilot platform log
                   (.bin/.log/.tlog), or a handheld or RTK receiver's track
                   (GPX, NMEA, CSV, RTKLIB/Emlid .pos). The position at the
                   capture time is interpolated between the log's fixes
                   either side of it (or the nearest fix within 5 s)
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
# Everything that can hold a GPS track: platform logs plus the handheld and
# RTK formats parse_gps_log reads.
GPS_LOG_EXTS = LOG_EXTS + (".gpx", ".nmea", ".pos", ".csv", ".txt")
# Files under Metadata/ that are not logs: the per-image table Data Sync
# writes there (or a person uploads per image as Synced Metadata). Its
# merged copy of the logs, drone_msgs.csv, goes to the scope root instead,
# so a flight log uploaded under that name into Metadata/ is still read.
NOT_LOGS = {"msgs_synced.csv"}

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


def _offset_seconds(v) -> Optional[float]:
    """"+02:00" / "-07:00" (EXIF OffsetTime*) → seconds east of UTC."""
    try:
        t = str(v).strip()
        sign = -1 if t.startswith("-") else 1
        h, m = t.lstrip("+-").split(":")[:2]
        return sign * (int(h) * 3600 + int(m) * 60)
    except Exception:
        return None


def exif_record(blob: bytes) -> dict:
    """{timestamp, lat, lon, alt, time_zone_known} from an image's EXIF
    (None where absent).

    Time, best first:
      1. DateTimeOriginal with its OffsetTimeOriginal (phones write both)
         and SubSecTimeOriginal: the capture time, to the sub-second;
      2. the GPS UTC date/time tags (the time of the position fix);
      3. DateTimeOriginal/Digitized/DateTime alone, read as UTC — the
         camera's clock with no time zone (time_zone_known False), which a
         GPS log is matched to by a clock offset (see clock_offset).
    """
    from PIL import Image

    rec: dict = {"timestamp": None, "lat": None, "lon": None, "alt": None,
                 "time_zone_known": False}
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
    # The camera's clock: DateTimeOriginal (else Digitized, else DateTime),
    # with its sub-seconds and time zone offset when written.
    local, subsec, offset = None, 0.0, None
    for tag, sub_tag, off_tag in ((36867, 37521, 36881), (36868, 37522, 36882)):
        if sub.get(tag):
            local = sub.get(tag)
            try:
                subsec = float("0." + str(sub.get(sub_tag) or "0").strip().split()[0])
            except ValueError:
                subsec = 0.0
            offset = _offset_seconds(sub.get(off_tag)) if sub.get(off_tag) else None
            break
    else:
        local = exif.get(306)
        offset = _offset_seconds(sub.get(36880)) if sub.get(36880) else None
    clock = None
    if local:
        try:
            clock = datetime.strptime(str(local)[:19], "%Y:%m:%d %H:%M:%S") \
                .replace(tzinfo=timezone.utc).timestamp() + subsec
        except ValueError:
            clock = None
    if clock is not None and offset is not None:
        rec["timestamp"] = clock - offset
        rec["time_zone_known"] = True
        return rec
    if gps.get(29) and gps.get(7):
        try:
            h, m, s = (_ratio(x) for x in gps[7])
            day = datetime.strptime(str(gps[29]), "%Y:%m:%d").replace(tzinfo=timezone.utc)
            rec["timestamp"] = day.timestamp() + h * 3600 + m * 60 + s
            rec["time_zone_known"] = True
            return rec
        except Exception:
            pass
    rec["timestamp"] = clock
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


# A rangefinder reading counts only with RFND.Stat "Good". Out of range
# (too near/far) readings carry a clamped, wrong distance; old firmware logs
# no Stat, and those readings are taken as given.
_RFND_GOOD = 4
# GPS altitude is only meaningful with a 3D fix (Status >= 3).
_GPS_3D_FIX = 3


def parse_platform_log(path: str) -> pd.DataFrame:
    """GPS fixes from an ArduPilot DataFlash/telemetry log: timestamp, lat,
    lon, alt, gps_alt, rangefinder_distance, alt_source, roll, pitch, yaw.

    `alt` is the GPS altitude (above sea level), the same reference as a
    photo's EXIF altitude and ground control points, so every camera in
    geo.txt is on one vertical scale. (main's parser preferred the
    rangefinder's height above ground and fell back to GPS altitude, mixing
    two scales ~20 m apart in one flight, and used out-of-range rangefinder
    readings.) A valid rangefinder reading within 1 s is kept, for reference,
    as rangefinder_distance. Fixes without a 3D fix get no altitude (filled
    later by fill_missing_altitude)."""
    from pymavlink import mavutil

    mlog = mavutil.mavlink_connection(path)
    gps, rf, att = [], [], []
    while True:
        msg = mlog.recv_match(blocking=False)
        if msg is None:
            break
        t = msg.get_type()
        if t == "GPS" and getattr(msg, "Lat", None) and getattr(msg, "Lng", None):
            status = getattr(msg, "Status", _GPS_3D_FIX)
            alt = getattr(msg, "Alt", None) if status >= _GPS_3D_FIX else None
            gps.append((msg._timestamp, msg.Lat, msg.Lng, alt))
        elif t == "RFND":
            # Keep bad readings too, so a fix whose nearest reading is out of
            # range gets none, not an older good one.
            good = getattr(msg, "Stat", _RFND_GOOD) == _RFND_GOOD
            rf.append((msg._timestamp, getattr(msg, "Dist", None) if good else None))
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
        gps_alt = round(float(alt), 2) if alt is not None else None
        rows.append({
            "timestamp": round(float(ts), 6), "lat": float(lat), "lon": float(lon),
            "alt": gps_alt, "gps_alt": gps_alt,
            "rangefinder_distance": round(float(dist), 2) if dist is not None and float(dist) > 0 else None,
            "alt_source": "gps" if gps_alt is not None else None,
            "roll": roll, "pitch": pitch, "yaw": yaw,
        })
    return pd.DataFrame(rows)


def fill_missing_altitude(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Give every located image without an altitude the altitude of the
    nearest image in time that has one (the median, if it has no time), and
    mark it alt_estimated. Returns (df, number estimated).

    ODM treats a missing altitude as 0 m, so one image without altitude in
    a flight at 30 m would sit 30 m below the rest. When no image has an
    altitude, nothing is filled: all-unknown is at least consistent."""
    out = df.copy()
    if "alt" not in out:
        out["alt"] = np.nan
    out["alt"] = pd.to_numeric(out["alt"], errors="coerce")
    if "alt_estimated" not in out:
        out["alt_estimated"] = False
    located = out["lat"].notna() & out["lon"].notna()
    known = located & out["alt"].notna()
    missing = located & out["alt"].isna()
    if not missing.any() or not known.any():
        return out, 0
    ts = pd.to_numeric(out.get("timestamp"), errors="coerce") if "timestamp" in out else pd.Series(np.nan, index=out.index)
    timed = known & ts.notna()
    ref_t = ts[timed].to_numpy(dtype=float)
    ref_alt = out.loc[timed, "alt"].to_numpy(dtype=float)
    median = float(out.loc[known, "alt"].median())
    for i in out.index[missing]:
        if pd.notna(ts[i]) and len(ref_t):
            out.at[i, "alt"] = float(ref_alt[np.abs(ref_t - float(ts[i])).argmin()])
        else:
            out.at[i, "alt"] = median
        out.at[i, "alt_estimated"] = True
    return out, int(missing.sum())


def merge_log_gps(images: pd.DataFrame, log: pd.DataFrame, max_diff: float = 5.0) -> pd.DataFrame:
    """Each image's position from the log at its capture time.

    Between two fixes no more than 2·max_diff apart, the position is
    interpolated linearly in time (a walker at 1.4 m/s moves 0.7 m between
    1 Hz fixes, so the nearest fix alone is up to that far off). Otherwise
    the nearest fix within max_diff seconds is taken; an image with neither
    keeps its own EXIF position. Altitude is interpolated only where both
    fixes have one."""
    out = images.copy()
    if log.empty or "timestamp" not in out:
        return out
    log = log.dropna(subset=["timestamp", "lat", "lon"]).sort_values("timestamp")
    log = log.drop_duplicates("timestamp").reset_index(drop=True)
    if log.empty:
        return out
    times = log["timestamp"].to_numpy(dtype=float)
    lats = log["lat"].to_numpy(dtype=float)
    lons = log["lon"].to_numpy(dtype=float)
    alts = pd.to_numeric(log["alt"], errors="coerce").to_numpy(dtype=float) \
        if "alt" in log else np.full(len(log), np.nan)
    for i, row in out.iterrows():
        if pd.isna(row.get("timestamp")):
            continue
        t = float(row["timestamp"])
        k = int(np.searchsorted(times, t))
        if 0 < k < len(times) and times[k] - times[k - 1] <= 2 * max_diff:
            a, b = k - 1, k
            w = (t - times[a]) / (times[b] - times[a]) if times[b] > times[a] else 0.0
            out.at[i, "lat"] = lats[a] + w * (lats[b] - lats[a])
            out.at[i, "lon"] = lons[a] + w * (lons[b] - lons[a])
            if not (np.isnan(alts[a]) or np.isnan(alts[b])):
                out.at[i, "alt"] = alts[a] + w * (alts[b] - alts[a])
            out.at[i, "gps_source"] = "platform_log"
            continue
        if k < len(times) and times[k] == t:
            j: Optional[int] = k
        else:
            j = _nearest(times, t, max_diff)
        if j is None:
            continue
        out.at[i, "lat"] = lats[j]
        out.at[i, "lon"] = lons[j]
        if not np.isnan(alts[j]):
            out.at[i, "alt"] = alts[j]
        out.at[i, "gps_source"] = "platform_log"
    return out


def clock_offset(images: pd.DataFrame, log: pd.DataFrame, slack: float = 60.0) -> tuple[float, int]:
    """The whole-hour shift of the images' clock (seconds to add) that puts
    most of their capture times inside the log's time span, and how many
    that puts inside.

    Only for images whose time has no time zone (time_zone_known False): a
    camera set to local time writes e.g. 10:02 for 17:02 UTC, and matched
    to a UTC GPS log as is, no photo would fall inside the log. A tie keeps
    no shift. Returns (0, n inside unshifted) when nothing does better."""
    if log.empty or "timestamp" not in images:
        return 0.0, 0
    naive = images
    if "time_zone_known" in images:
        naive = images[~images["time_zone_known"].fillna(False).astype(bool)]
    ts = pd.to_numeric(naive["timestamp"], errors="coerce").dropna().to_numpy(dtype=float)
    lt = pd.to_numeric(log["timestamp"], errors="coerce").dropna().to_numpy(dtype=float)
    if not ts.size or not lt.size:
        return 0.0, 0
    lo, hi = lt.min() - slack, lt.max() + slack
    best, best_n = 0.0, int(((ts >= lo) & (ts <= hi)).sum())
    for h in [x / 2 for x in range(-28, 29)]:  # half hours too (UTC+5:30, +9:30…)
        if h == 0:
            continue
        n = int(((ts + h * 3600 >= lo) & (ts + h * 3600 <= hi)).sum())
        if n > best_n:
            best, best_n = h * 3600, n
    return best, best_n


# ── Handheld and RTK GPS logs ───────────────────────────────────────────────

_GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc).timestamp()
# GPS time runs ahead of UTC by the leap seconds since 1980 (18 since 2017).
_GPS_UTC_LEAP = 18.0


def _gpx(text: str) -> pd.DataFrame:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(text)
    rows = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("trkpt", "rtept", "wpt"):
            continue
        t = ele = None
        for child in el:
            ct = child.tag.rsplit("}", 1)[-1]
            if ct == "time":
                t = child.text
            elif ct == "ele":
                ele = child.text
        if not t:
            continue
        ts = pd.Timestamp(t)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        rows.append({"timestamp": ts.timestamp(), "lat": float(el.get("lat")),
                     "lon": float(el.get("lon")),
                     "alt": float(ele) if ele not in (None, "") else None})
    return pd.DataFrame(rows, columns=["timestamp", "lat", "lon", "alt"])


def _nmea_deg(v: str, hemi: str) -> Optional[float]:
    if not v:
        return None
    dot = v.index(".") if "." in v else len(v)
    deg = float(v[: dot - 2]) + float(v[dot - 2:]) / 60
    return -deg if hemi in ("S", "W") else deg


def _nmea(text: str) -> pd.DataFrame:
    """$GPRMC/$GNRMC give the date and a position, $..GGA the altitude and
    fix quality; ZDA a date. A GGA fix takes the date of the latest RMC/ZDA
    before it."""
    rows: dict[float, dict] = {}
    day: Optional[float] = None
    for line in text.splitlines():
        line = line.strip()
        i = line.find("$")
        if i < 0:
            continue
        f = line[i:].split("*")[0].split(",")
        kind = f[0][3:] if len(f[0]) >= 6 else ""
        try:
            if kind == "RMC" and len(f) > 9 and f[2] == "A" and f[9]:
                day = datetime.strptime(f[9], "%d%m%y").replace(tzinfo=timezone.utc).timestamp()
                hh, mm, ss = int(f[1][:2]), int(f[1][2:4]), float(f[1][4:])
                t = day + hh * 3600 + mm * 60 + ss
                rows.setdefault(t, {"timestamp": t, "lat": _nmea_deg(f[3], f[4]),
                                    "lon": _nmea_deg(f[5], f[6]), "alt": None})
            elif kind == "ZDA" and len(f) > 4 and f[2]:
                day = datetime(int(f[4]), int(f[3]), int(f[2]), tzinfo=timezone.utc).timestamp()
            elif kind == "GGA" and len(f) > 9 and day is not None and f[6] not in ("", "0"):
                hh, mm, ss = int(f[1][:2]), int(f[1][2:4]), float(f[1][4:])
                t = day + hh * 3600 + mm * 60 + ss
                rows[t] = {"timestamp": t, "lat": _nmea_deg(f[2], f[3]),
                           "lon": _nmea_deg(f[4], f[5]),
                           "alt": float(f[9]) if f[9] else None}
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(list(rows.values()), columns=["timestamp", "lat", "lon", "alt"])


def _pos(text: str) -> pd.DataFrame:
    """RTKLIB / Emlid .pos: '%' header lines, the last naming the columns
    (GPST or UTC time as 'yyyy/mm/dd hh:mm:ss.sss' or 'week tow', then
    latitude(deg) longitude(deg) height(m) …). GPST is turned into UTC."""
    header = ""
    rows = []
    for line in text.splitlines():
        if line.startswith("%"):
            if "lat" in line.lower():
                header = line
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        gpst = "GPST" in header or "UTC" not in header
        try:
            if "/" in parts[0]:
                ts = datetime.strptime(f"{parts[0]} {parts[1]}"[:26], "%Y/%m/%d %H:%M:%S.%f") \
                    .replace(tzinfo=timezone.utc).timestamp()
                rest = parts[2:]
            else:
                ts = _GPS_EPOCH + int(parts[0]) * 604800 + float(parts[1])
                rest = parts[2:]
            if gpst:
                ts -= _GPS_UTC_LEAP
            rows.append({"timestamp": ts, "lat": float(rest[0]), "lon": float(rest[1]),
                         "alt": float(rest[2])})
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(rows, columns=["timestamp", "lat", "lon", "alt"])


def _canon(name: str) -> str:
    """'Latitude (deg)' → 'latitude': units in brackets and separators out."""
    import re

    name = re.sub(r"[\(\[].*?[\)\]]", "", str(name)).strip().lower()
    return re.sub(r"[\s_\-]+", "_", name)


_TIME_COLS = ("timestamp", "time", "datetime", "date_time", "utc", "time_utc", "utc_time",
              "gps_time", "gpst", "unix_time", "epoch", "ts")


def _csv(text: str) -> pd.DataFrame:
    """A table of fixes (a phone GPS logger's or an RTK receiver's export):
    a time column (epoch seconds/ms/µs, or a date-time; a separate date
    column is joined to it) and latitude/longitude columns. A date-time
    with no zone is read as UTC, as GPS devices record."""
    df = pd.read_csv(io.StringIO(text), sep=None, engine="python", on_bad_lines="skip")
    cols = {_canon(c): c for c in df.columns}
    lat = next((cols[c] for c in ("lat", "latitude") if c in cols), None)
    lon = next((cols[c] for c in ("lon", "lng", "long", "longitude") if c in cols), None)
    tcol = next((cols[c] for c in _TIME_COLS if c in cols), None)
    if not (lat and lon and tcol):
        return pd.DataFrame(columns=["timestamp", "lat", "lon", "alt"])
    alt = next((cols[c] for c in ("alt", "altitude", "height", "elevation", "ele",
                                   "ellipsoidal_height", "elevation_m") if c in cols), None)
    raw = df[tcol]
    num = pd.to_numeric(raw, errors="coerce")
    if num.notna().mean() > 0.9:
        med = float(num.median())
        ts = num / (1e6 if med > 1e14 else 1e3 if med > 1e11 else 1.0)
        if "gps_time" == _canon(tcol) and med < 1e9:  # GPS seconds since 1980
            ts = _GPS_EPOCH + num - _GPS_UTC_LEAP
    else:
        text_t = raw.astype(str)
        if "date" in cols and cols["date"] != tcol:
            text_t = df[cols["date"]].astype(str) + " " + text_t
        dt = pd.to_datetime(text_t, errors="coerce", utc=True, format="mixed")
        ts = (dt - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    out = pd.DataFrame({
        "timestamp": ts,
        "lat": pd.to_numeric(df[lat], errors="coerce"),
        "lon": pd.to_numeric(df[lon], errors="coerce"),
        "alt": pd.to_numeric(df[alt], errors="coerce") if alt else np.nan,
    })
    return out.dropna(subset=["timestamp", "lat", "lon"])


def parse_gps_log(path: str) -> pd.DataFrame:
    """GPS fixes (timestamp UTC seconds, lat, lon, alt) from any log a
    platform or a person's GPS writes: ArduPilot .bin/.tlog/.log, GPX,
    NMEA (.nmea/.txt/.log), RTKLIB/Emlid .pos, or a CSV table. The format
    is told by content where extensions are shared (.log, .txt)."""
    import os

    ext = os.path.splitext(path)[1].lower()
    if ext in (".bin", ".tlog"):
        return parse_platform_log(path)
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8", errors="ignore")
    head = text[:4096]
    if ext == ".log" and "$GP" not in head and "$GN" not in head:
        return parse_platform_log(path)
    if "<gpx" in head or ext == ".gpx":
        df = _gpx(text)
    elif ext == ".nmea" or "$GP" in head or "$GN" in head:
        df = _nmea(text)
    elif ext == ".pos" or (head.startswith("%") and "lat" in head.lower()):
        df = _pos(text)
    else:
        df = _csv(text)
    df = df.dropna(subset=["timestamp", "lat", "lon"])
    df = df[(df["lat"].abs() <= 90) & (df["lon"].abs() <= 180) & ~((df["lat"] == 0) & (df["lon"] == 0))]
    return df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)


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
        # No altitude column → unknown, not 0 m (see fill_missing_altitude).
        "alt": pd.to_numeric(df["alt"], errors="coerce") if "alt" in df else np.nan,
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
    """ODM's image geolocation file (EPSG:4326): `image lon lat [alt]`.

    Altitude is written only where known (run fill_missing_altitude first;
    ODM reads a missing altitude as 0 m). Nothing follows it: ODM would read
    further columns as the camera's yaw/pitch/roll and GPS accuracy, and
    zeros there overrode the orientation in the images' own metadata."""
    lines = ["EPSG:4326"]
    for _, r in df.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
            pos = f"{r['image']} {r['lon']} {r['lat']}"
            alt = r.get("alt")
            lines.append(f"{pos} {alt}" if pd.notna(alt) else pos)
    return "\n".join(lines) + "\n"
