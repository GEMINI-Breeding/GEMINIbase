"""Georeferencing stitched ground plots (gemini.workers.stitch.georef).

Needs rasterio/pyproj, which live in the stitch worker image, not the unit
test environment; run there with

    docker compose run --rm --no-deps -v "$PWD/backend/tests:/app/tests" \\
        --entrypoint python geminibase-worker-stitch -m pytest /app/tests/unit/workers/test_stitch_georef.py
"""
import numpy as np
import pandas as pd
import pytest

rasterio = pytest.importorskip("rasterio")
pytest.importorskip("pyproj")
from PIL import Image  # noqa: E402

from gemini.workers.stitch import georef  # noqa: E402

LAT0, LON0 = 38.53662, -121.77654


def southbound(n=8, step_deg=3e-6):
    return pd.DataFrame({"lat": LAT0 - step_deg * np.arange(n), "lon": [LON0] * n})


def strip(path, w=600, h=200, colour=(40, 160, 40)):
    Image.new("RGB", (w, h), colour).save(path)
    return path


def test_plot_is_laid_along_its_track(tmp_path):
    gps = southbound()
    out = tmp_path / "georeferenced_plot_1_utm.tif"
    assert georef.georeference_plot(strip(tmp_path / "p1.png"), gps, out)
    with rasterio.open(out) as src:
        assert src.crs.to_epsg() == 32610  # UTM 10N for Davis
        assert src.count == 3
    ring = georef.footprint_wgs84(out)
    lats = [lat for _, lat in ring]
    lons = [lon for lon, _ in ring]
    # Spans the track's length north-south (~2.3 m) and ~1 m across it.
    assert min(lats) == pytest.approx(gps.lat.min(), abs=2e-6)
    assert max(lats) == pytest.approx(gps.lat.max(), abs=2e-6)
    assert max(lons) - min(lons) == pytest.approx(1.0 / (111_320 * np.cos(np.radians(LAT0))), rel=0.1)
    lon_c, lat_c = georef.center_wgs84(out)
    assert lat_c == pytest.approx(gps.lat.mean(), abs=1e-6)
    assert lon_c == pytest.approx(LON0, abs=1e-6)


def test_too_little_gps_is_refused(tmp_path):
    assert not georef.georeference_plot(
        strip(tmp_path / "p.png"), southbound(n=1), tmp_path / "x.tif"
    )


def test_combined_mosaic_is_a_cog_with_nodata_between_plots(tmp_path):
    a = tmp_path / "georeferenced_plot_1_utm.tif"
    b = tmp_path / "georeferenced_plot_2_utm.tif"
    track = southbound(n=20)
    georef.georeference_plot(strip(tmp_path / "a.png"), track.iloc[:6], a)
    georef.georeference_plot(strip(tmp_path / "b.png", colour=(200, 60, 60)), track.iloc[12:], b)
    utm, wgs = tmp_path / "combined_mosaic_utm.tif", tmp_path / "combined_mosaic.tif"
    assert georef.combine_utm_tiffs([a, b], utm, wgs)
    with rasterio.open(wgs) as src:
        assert src.crs.to_epsg() == 4326
        assert src.nodata == 0
        assert src.overviews(1), "a COG carries overviews"
        assert src.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") == "COG"
        data = src.read()
    covered = data.any(axis=0)
    # Both plots are there, with a gap of nodata between them.
    assert 0.2 < covered.mean() < 0.9
    rows = covered.any(axis=1)
    edges = np.flatnonzero(np.diff(rows.astype(int)))
    assert len(edges) >= 2, "expected a nodata band between the two plots"
    assert not (tmp_path / "combined_mosaic.plain.tif").exists()
