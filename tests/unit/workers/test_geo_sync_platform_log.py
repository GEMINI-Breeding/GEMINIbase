"""ArduPilot DataFlash log parsing for Data Sync.

There is no real flight log in the example data, so this writes a small
DataFlash log with ArduPilot's own message layouts (FMT, GPS with GPS
week/milliseconds, RFND, ATT) and reads it back with pymavlink, the same
parser main uses. Needs pymavlink (the geo worker image):

    docker compose run --rm --no-deps -v "$PWD/backend/tests:/app/tests" \\
        --entrypoint bash geminibase-worker-geo -c \\
        "pip install -q pytest && cd /app && python -m pytest tests/unit/workers/test_geo_sync_platform_log.py"
"""
import struct

import pandas as pd
import pytest

pytest.importorskip("pymavlink")

from gemini.workers.geo import sync  # noqa: E402

HEAD = b"\xa3\x95"
FMTS = {
    # type: (name, format, columns)
    129: ("GPS", "QBIHBcLLeff", "TimeUS,Status,GMS,GWk,NSats,HDop,Lat,Lng,Alt,Spd,GCrs"),
    130: ("RFND", "QBf", "TimeUS,Instance,Dist"),
    131: ("ATT", "Qccc", "TimeUS,Roll,Pitch,Yaw"),
}
PACK = {"Q": "Q", "B": "B", "I": "I", "H": "H", "c": "h", "L": "i", "e": "i", "f": "f"}
# 2024-07-15 15:50:00 UTC as GPS week / ms of week (18 leap seconds).
GWK, GMS0 = 2323, 143_418_000


def _msg(mtype: int, fmt: str, *values) -> bytes:
    body = struct.pack("<" + "".join(PACK[c] for c in fmt), *values)
    return HEAD + bytes([mtype]) + body


def write_log(path):
    out = bytearray()
    fmt_fmt = "BB4s16s64s"
    for mtype, (name, fmt, cols) in FMTS.items():
        length = 3 + struct.calcsize("<" + "".join(PACK[c] for c in fmt))
        out += HEAD + bytes([128]) + struct.pack(
            "<" + fmt_fmt, mtype, length, name.encode(), fmt.encode(), cols.encode()
        )
    # Also describe FMT itself, as real logs do.
    out = HEAD + bytes([128]) + struct.pack(
        "<BB4s16s64s", 128, 89, b"FMT", b"BBnNZ", b"Type,Length,Name,Format,Columns"
    ) + out
    for i in range(10):  # 1 Hz for 10 s, heading north
        t_us = 60_000_000 + i * 1_000_000
        out += _msg(129, FMTS[129][1], t_us, 3, GMS0 + i * 1000, GWK, 12, 70,
                    int((38.5 + i * 1e-5) * 1e7), int(-121.7 * 1e7), 1500, 1.0, 0.0)
        out += _msg(130, FMTS[130][1], t_us + 100_000, 0, 7.25 if i < 5 else 0.0)
        out += _msg(131, FMTS[131][1], t_us + 200_000, 150, -250, 9000)
    path.write_bytes(bytes(out))


def test_parse_platform_log(tmp_path):
    log = tmp_path / "00000001.BIN"
    write_log(log)
    df = sync.parse_platform_log(str(log))
    assert len(df) == 10
    assert df["lat"].iloc[0] == pytest.approx(38.5)
    assert df["lon"].iloc[0] == pytest.approx(-121.7)
    # GPS week/ms → UTC: the first fix is 2024-07-15 15:50:00.
    assert df["timestamp"].iloc[0] == pytest.approx(1721058600.0, abs=1.0)
    assert df["timestamp"].diff().iloc[1] == pytest.approx(1.0, abs=0.01)
    # Altitude is always the GPS altitude (one vertical scale for the whole
    # flight); a rangefinder reading is kept only for reference.
    assert (df["alt"] == 15.0).all() and (df["alt_source"] == "gps").all()
    assert df["rangefinder_distance"].iloc[0] == 7.25
    assert pd.isna(df["rangefinder_distance"].iloc[9])  # 0.0 = no reading
    assert df["yaw"].iloc[0] == pytest.approx(90.0)


FMTS_V2 = {
    # Current firmware: GPS Status and RFND Stat are logged.
    129: ("GPS", "QBIHBcLLeff", "TimeUS,Status,GMS,GWk,NSats,HDop,Lat,Lng,Alt,Spd,GCrs"),
    130: ("RFND", "QBfB", "TimeUS,Instance,Dist,Stat"),
}


def write_log_v2(path, fixes):
    """fixes: (gps_status, gps_alt_m, rfnd_dist_m, rfnd_stat) per second."""
    out = HEAD + bytes([128]) + struct.pack(
        "<BB4s16s64s", 128, 89, b"FMT", b"BBnNZ", b"Type,Length,Name,Format,Columns"
    )
    for mtype, (name, fmt, cols) in FMTS_V2.items():
        length = 3 + struct.calcsize("<" + "".join(PACK[c] for c in fmt))
        out += HEAD + bytes([128]) + struct.pack(
            "<BB4s16s64s", mtype, length, name.encode(), fmt.encode(), cols.encode()
        )
    for i, (status, alt, dist, stat) in enumerate(fixes):
        t_us = 60_000_000 + i * 1_000_000
        out += _msg(129, FMTS_V2[129][1], t_us, status, GMS0 + i * 1000, GWK, 12, 70,
                    int(38.5 * 1e7), int(-121.7 * 1e7), int(alt * 100), 1.0, 0.0)
        out += _msg(130, FMTS_V2[130][1], t_us + 100_000, 0, dist, stat)
    path.write_bytes(bytes(out))


def test_out_of_range_rangefinder_and_2d_fixes_are_not_used(tmp_path):
    # Shaped like a real survey (2025-07-18, ArduCopter 4.5.6): flying at the
    # rangefinder's 10 m limit, some readings are "out of range high" (Stat
    # 3) with a clamped, wrong distance; the first fix is only 2D.
    log = tmp_path / "flight.bin"
    write_log_v2(log, [
        (2, 0.0, 0.2, 4),     # 2D fix: altitude meaningless
        (4, 29.0, 9.2, 4),    # good
        (4, 30.5, 12.0, 3),   # out of range high
        (6, 29.5, 9.6, 4),    # RTK fixed, good
    ])
    df = sync.parse_platform_log(str(log))
    assert pd.isna(df["alt"].iloc[0]) and df["alt_source"].iloc[0] is None
    assert df["alt"].tolist()[1:] == [29.0, 30.5, 29.5]
    assert df["rangefinder_distance"].iloc[1] == pytest.approx(9.2)
    # Its own reading is out of range: none, not the good one from 0.9 s ago.
    assert pd.isna(df["rangefinder_distance"].iloc[2])
