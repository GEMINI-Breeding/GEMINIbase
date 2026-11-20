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
        "time_zone_known": False,
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


def test_log_position_interpolated_between_fixes():
    # A walker logged at 1 Hz: the photo at 10.25 s sits a quarter of the way.
    imgs = images(("a.jpg", 10.25, 9.0, 9.0, None, "exif"))
    log = pd.DataFrame({"timestamp": [10.0, 11.0], "lat": [38.0, 38.0004],
                        "lon": [-121.0, -121.0], "alt": [10.0, 12.0]})
    out = sync.merge_log_gps(imgs, log)
    assert out.loc[0, "lat"] == pytest.approx(38.0001)
    assert out.loc[0, "alt"] == pytest.approx(10.5)
    assert out.loc[0, "gps_source"] == "platform_log"


def test_no_interpolation_across_a_gap_in_the_log():
    # Fixes 60 s apart (the receiver lost the sky): nearest within 5 s only.
    imgs = images(("a.jpg", 30.0, 9.0, 9.0, None, "exif"), ("b.jpg", 58.0, 9.0, 9.0, None, "exif"))
    log = pd.DataFrame({"timestamp": [0.0, 60.0], "lat": [1.0, 2.0], "lon": [1.0, 2.0], "alt": [None, None]})
    out = sync.merge_log_gps(imgs, log)
    assert out.loc[0, "gps_source"] == "exif"
    assert out.loc[1, ["lat", "gps_source"]].tolist() == [2.0, "platform_log"]


def test_clock_offset_finds_a_local_time_camera():
    # Camera at local time (UTC-7): photos 7 h before a UTC log's span.
    log = pd.DataFrame({"timestamp": [100000.0 + i for i in range(600)],
                        "lat": 38.0, "lon": -121.0, "alt": None})
    imgs = pd.DataFrame({"timestamp": [100000.0 - 7 * 3600 + 10 * i for i in range(50)],
                         "time_zone_known": False})
    shift, n = sync.clock_offset(imgs, log)
    assert shift == 7 * 3600 and n == 50
    # Photos with a known time zone are not shifted.
    imgs["time_zone_known"] = True
    assert sync.clock_offset(imgs, log) == (0.0, 0)


def _jpeg(exif_sub=None, exif_gps=None) -> bytes:
    import io
    from PIL import Image

    img = Image.new("RGB", (8, 8))
    exif = Image.Exif()
    if exif_sub:
        exif.get_ifd(34665).update(exif_sub)
    if exif_gps:
        exif.get_ifd(34853).update(exif_gps)
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_exif_time_with_offset_is_utc():
    # An iPhone photo: local time, sub-seconds and the offset.
    rec = sync.exif_record(_jpeg({36867: "2026:08:17 10:02:03", 37521: "250", 36881: "-07:00"}))
    assert rec["time_zone_known"] is True
    assert rec["timestamp"] == pd.Timestamp("2026-08-17 17:02:03.25", tz="UTC").timestamp()


def test_exif_time_without_offset_is_marked_unknown():
    rec = sync.exif_record(_jpeg({36867: "2026:08:17 10:02:03"}))
    assert rec["time_zone_known"] is False
    assert rec["timestamp"] == pd.Timestamp("2026-08-17 10:02:03", tz="UTC").timestamp()


def _write(tmp_path, name, text):
    f = tmp_path / name
    f.write_text(text)
    return str(f)


def test_gpx_track(tmp_path):
    df = sync.parse_gps_log(_write(tmp_path, "walk.gpx", """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="38.5" lon="-121.7"><ele>15.2</ele><time>2026-08-17T17:00:00Z</time></trkpt>
<trkpt lat="38.5001" lon="-121.7"><ele>15.4</ele><time>2026-08-17T17:00:01Z</time></trkpt>
</trkseg></trk></gpx>"""))
    assert len(df) == 2
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-08-17 17:00:00", tz="UTC").timestamp()
    assert df.loc[1, ["lat", "alt"]].tolist() == [38.5001, 15.4]


def test_nmea_track(tmp_path):
    df = sync.parse_gps_log(_write(tmp_path, "walk.nmea", "\n".join([
        "$GPRMC,170000.00,A,3830.0000,N,12142.0000,W,0.5,0,170826,,,A*00",
        "$GPGGA,170001.00,3830.0060,N,12142.0000,W,4,12,0.8,15.3,M,-30.0,M,,*00",
        "$GPGGA,170002.00,3830.0120,N,12142.0000,W,0,0,,,M,,M,,*00",  # no fix
    ])))
    assert len(df) == 2
    assert df.loc[0, "lat"] == pytest.approx(38.5)
    assert df.loc[0, "lon"] == pytest.approx(-121.7)
    assert df.loc[1, "alt"] == 15.3
    assert df.loc[1, "timestamp"] - df.loc[0, "timestamp"] == pytest.approx(1.0)


def test_rtklib_pos_is_turned_into_utc(tmp_path):
    df = sync.parse_gps_log(_write(tmp_path, "rover.pos", "\n".join([
        "% program   : RTKPOST",
        "%  GPST                  latitude(deg) longitude(deg)  height(m)   Q  ns",
        "2026/08/17 17:00:18.000   38.500000000 -121.700000000    15.2000   1  14",
    ])))
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-08-17 17:00:00", tz="UTC").timestamp()
    assert df.loc[0, "alt"] == 15.2


def test_csv_track_from_a_phone_logger(tmp_path):
    df = sync.parse_gps_log(_write(tmp_path, "gpslogger.csv", "\n".join([
        "time,lat,lon,elevation,accuracy",
        "2026-08-17T17:00:00Z,38.5,-121.7,15.0,3.2",
        "2026-08-17T17:00:01Z,38.5001,-121.7,15.1,3.1",
    ])))
    assert len(df) == 2
    assert df.loc[1, "timestamp"] == pd.Timestamp("2026-08-17 17:00:01", tz="UTC").timestamp()


def test_csv_with_units_and_epoch_ms(tmp_path):
    df = sync.parse_gps_log(_write(tmp_path, "reach.csv", "\n".join([
        "Timestamp,Latitude (deg),Longitude (deg),Height (m)",
        "1787072400000,38.5,-121.7,15.0",
    ])))
    assert df.loc[0, "timestamp"] == 1787072400.0
    assert df.loc[0, "alt"] == 15.0


def test_a_table_without_times_is_no_log(tmp_path):
    assert sync.parse_gps_log(_write(tmp_path, "plots.csv", "plot,lat,lon\n1,38.5,-121.7\n")).empty


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
