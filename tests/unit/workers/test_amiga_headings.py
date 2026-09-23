"""Direction of travel from an Amiga GPS track (gemini.workers.amiga.headings)."""
import numpy as np
import pandas as pd

from gemini.workers.amiga.headings import (
    add_direction_columns,
    compute_latlon_bearing,
    heading_to_direction,
    smooth_headings,
)

LAT0, LON0 = 38.5382, -121.7617
STEP = 1e-6  # ~0.1 m per frame, a crawling rover


def track(dlat: float, dlon: float, n: int, start=(LAT0, LON0)):
    lat = start[0] + dlat * np.arange(n)
    lon = start[1] + dlon * np.arange(n)
    return lat, lon


def test_heading_buckets():
    assert heading_to_direction(0.0) == "North"
    assert heading_to_direction(np.pi / 2) == "East"
    assert heading_to_direction(np.pi) == "South"
    assert heading_to_direction(-np.pi / 2) == "West"
    assert heading_to_direction(None) is None


def test_bearing_follows_the_track():
    lat, lon = track(STEP, 0, 40)
    b = compute_latlon_bearing(pd.Series(lat), pd.Series(lon))
    assert b.notna().all()  # edges are filled, not NaN
    assert set(b.apply(heading_to_direction)) == {"North"}

    lat, lon = track(0, -STEP, 40)
    b = compute_latlon_bearing(pd.Series(lat), pd.Series(lon))
    assert set(b.apply(heading_to_direction)) == {"West"}


def test_jitter_island_is_absorbed():
    # Heading east throughout, with a short burst pointing north.
    heading = pd.Series([np.pi / 2] * 60)
    heading.iloc[28:31] = 0.0
    raw = heading.apply(heading_to_direction)
    assert (raw == "North").sum() == 3
    smoothed = smooth_headings(heading, window=15, min_run=7)
    assert set(smoothed) == {"East"}


def test_reversal_across_a_recording_gap_is_kept():
    # North for 60 frames, a 30 s pause, then South — two recordings.
    heading = pd.Series([0.0] * 60 + [np.pi] * 60)
    stamps = pd.Series(np.r_[np.arange(60) * 0.1, 36 + np.arange(60) * 0.1])
    smoothed = smooth_headings(heading, stamp_series=stamps, window=50, min_run=26)
    assert list(smoothed[:60]) == ["North"] * 60
    assert list(smoothed[60:]) == ["South"] * 60


def test_add_direction_columns_prefers_lat_lon():
    lat, lon = track(-STEP, 0, 80)  # southbound
    df = pd.DataFrame({
        "lat": lat,
        "lon": lon,
        "heading_motion": [0.0] * 80,  # says north; lat/lon wins
        "stamp": (np.arange(80) * 1e5).astype("int64"),  # microseconds
    })
    assert add_direction_columns(df) is True
    assert set(df["direction"]) == {"South"}
    assert set(df["direction_raw"]) == {"South"}


def test_add_direction_columns_falls_back_to_heading_motion():
    df = pd.DataFrame({"heading_motion": [np.pi / 2] * 30})
    assert add_direction_columns(df) is True
    assert set(df["direction"]) == {"East"}


def test_add_direction_columns_without_position_is_a_no_op():
    df = pd.DataFrame({"image": ["a.jpg", "b.jpg"]})
    assert add_direction_columns(df) is False
    assert "direction" not in df.columns
