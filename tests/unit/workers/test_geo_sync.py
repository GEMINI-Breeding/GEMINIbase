"""Data Sync rules (gemini.workers.geo.sync)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gemini.workers.geo import sync

DRONE = (
    Path(__file__).resolve().parents[4]
    / "frontend/tests/fixtures/images/drone/2022-06-27_100MEDIA_DJI_0876.JPG"
)


@pytest.mark.skipif(not DRONE.exists(), reason="needs the app's test fixtures")
def test_exif_record_from_a_real_drone_image():
    rec = sync.exif_record(DRONE.read_bytes()[: 256 * 1024])  # the worker reads a prefix
    assert rec["lat"] == pytest.approx(38.5337, abs=1e-3)
    assert rec["lon"] == pytest.approx(-121.7825, abs=1e-3)
    assert rec["alt"] == pytest.approx(11.515, abs=1e-3)
    # No GPS time tags on this camera: DateTimeOriginal, read as UTC.
    assert rec["timestamp"] == pd.Timestamp("2022-06-27 11:03:29", tz="UTC").timestamp()


def test_exif_record_of_garbage_is_empty():
    assert sync.exif_record(b"not an image") == {
        "timestamp": None, "lat": None, "lon": None, "alt": None,
    }


def images(*rows):
    return pd.DataFrame(rows, columns=["image", "timestamp", "lat", "lon", "alt", "gps_source"])


def test_platform_log_fix_within_5s_replaces_exif():
    imgs = images(
        ("a.jpg", 100.0, 1.0, 1.0, 50.0, "exif"),
        ("b.jpg", 200.0, 1.0, 1.0, 50.0, "exif"),
        ("c.jpg", None, 1.0, 1.0, 50.0, "exif"),
    )
    log = pd.DataFrame({"timestamp": [98.0, 150.0], "lat": [2.0, 3.0],
                        "lon": [2.0, 3.0], "alt": [12.3, None]})
    out = sync.merge_log_gps(imgs, log)
    assert out.loc[0, ["lat", "lon", "alt", "gps_source"]].tolist() == [2.0, 2.0, 12.3, "platform_log"]
    assert out.loc[1, "gps_source"] == "exif"  # nearest fix is 50 s away
    assert out.loc[2, "gps_source"] == "exif"  # no capture time


REF = pd.DataFrame({
    "timestamp": [10.0, 20.0],
    "lat": [38.0, 38.001],
    "lon": [-121.0, -121.0],
    "alt": [5.0, 5.0],
})


def test_cross_sensor_tiers():
    imgs = images(
        ("inside.jpg", 15.0, None, None, None, "none"),
        ("just_after.jpg", 35.0, None, None, None, "none"),
        ("far_own_gps.jpg", 500.0, 40.0, -100.0, 1.0, "exif"),
        ("far_no_gps.jpg", 500.0, None, None, None, "none"),
        ("no_time.jpg", None, 40.0, -100.0, 1.0, "exif"),
    )
    out = sync.cross_sensor(imgs, REF, max_extrapolation=30).set_index("image")
    assert out.loc["inside.jpg", "lat"] == pytest.approx(38.0005)
    assert out.loc["inside.jpg", "gps_source"] == "interpolated"
    assert out.loc["just_after.jpg", "lat"] == 38.001
    assert out.loc["just_after.jpg", "gps_source"] == "clamped"
    assert out.loc["far_own_gps.jpg", ["lat", "gps_source"]].tolist() == [40.0, "own_gps"]
    assert out.loc["far_no_gps.jpg", "gps_source"] == "none"
    assert np.isnan(out.loc["far_no_gps.jpg", "lat"])
    assert out.loc["no_time.jpg", "gps_source"] == "own_gps"


def test_reference_track_reads_an_amiga_msgs_synced():
    amiga = pd.DataFrame({
        "/top/rgb_file": ["/top/rgb-2.jpg", "/top/rgb-1.jpg", "/top/rgb-3.jpg"],
        "gps_time": [2e6, 1e6, None],  # microseconds, as the extractor writes
        "lat": [38.1, 38.0, 38.2],
        "lon": [-121.0, -121.0, -121.0],
        "altitude": [4.0, 3.0, 5.0],
    })
    ref = sync.reference_track(amiga)
    assert ref["timestamp"].tolist() == [1.0, 2.0]  # sorted; row without time dropped
    assert ref["alt"].tolist() == [3.0, 4.0]


def test_reference_track_without_positions_is_refused():
    with pytest.raises(ValueError, match="no lat"):
        sync.reference_track(pd.DataFrame({"timestamp": [1.0]}))


def test_geo_txt_lists_located_images_only():
    df = images(("a.jpg", 1.0, 38.5, -121.7, 29.5, "exif"), ("b.jpg", 1.0, None, None, None, "none"))
    # Nothing after the altitude: ODM would read more columns as camera
    # yaw/pitch/roll and GPS accuracy.
    assert sync.geo_txt(df) == "EPSG:4326\na.jpg -121.7 38.5 29.5\n"


def test_geo_txt_leaves_out_an_unknown_altitude():
    df = images(("a.jpg", 1.0, 38.5, -121.7, None, "exif"))
    assert sync.geo_txt(df) == "EPSG:4326\na.jpg -121.7 38.5\n"


def test_missing_altitude_takes_the_nearest_image_in_time():
    df = images(
        ("a.jpg", 10.0, 38.5, -121.7, 29.0, "platform_log"),
        ("b.jpg", 11.0, 38.5, -121.7, None, "exif"),       # nearest: a
        ("c.jpg", 19.0, 38.5, -121.7, None, "exif"),       # nearest: d
        ("d.jpg", 20.0, 38.5, -121.7, 31.0, "platform_log"),
        ("e.jpg", None, 38.5, -121.7, None, "exif"),       # no time: median
        ("f.jpg", 12.0, None, None, None, "none"),         # no position: left alone
    )
    out, n = sync.fill_missing_altitude(df)
    assert n == 3
    assert out["alt"].tolist()[:5] == [29.0, 29.0, 31.0, 31.0, 30.0]
    assert out["alt_estimated"].tolist() == [False, True, True, False, True, False]
    assert pd.isna(out["alt"].iloc[5])
    # Never 0 m: in geo.txt every located camera is on the same scale.
    rows = [line.split() for line in sync.geo_txt(out).splitlines()[1:]]
    assert [float(r[3]) for r in rows] == [29.0, 29.0, 31.0, 31.0, 30.0]


def test_no_altitude_anywhere_stays_unknown_rather_than_0():
    df = images(("a.jpg", 1.0, 38.5, -121.7, None, "exif"), ("b.jpg", 2.0, 38.5, -121.7, None, "exif"))
    out, n = sync.fill_missing_altitude(df)
    assert n == 0 and out["alt"].isna().all()
    assert sync.geo_txt(out) == "EPSG:4326\na.jpg -121.7 38.5\nb.jpg -121.7 38.5\n"


def test_reference_track_without_altitude_is_unknown_not_0():
    ref = sync.reference_track(pd.DataFrame({"timestamp": [1.0, 2.0], "lat": [38.5, 38.6], "lon": [-121.7, -121.7]}))
    assert ref["alt"].isna().all()


def test_normalise_columns_uses_main_aliases():
    df = sync.normalise_columns(pd.DataFrame(columns=["filename", "Latitude", "Longitude", "unix_time"]))
    assert list(df.columns) == ["image_path", "lat", "lon", "timestamp"]
