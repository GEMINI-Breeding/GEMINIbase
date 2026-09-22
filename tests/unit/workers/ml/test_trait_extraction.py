"""Unit tests for the trait-extraction kernels."""
import numpy as np
import pytest

# These kernels import cv2 at call time. cv2 lives in the ml worker image,
# not in the backend's top-level deps; skip the whole module when it isn't
# available (running these in the worker container stays the source of
# truth).
pytest.importorskip("cv2")

from gemini.workers.ml.trait_extraction import (  # noqa: E402
    compute_exg_mask,
    estimate_canopy_temperature,
    estimate_height_from_dem,
    extract_traits_from_ortho,
)


# ---------------------------------------------------------------------------
# compute_exg_mask
# ---------------------------------------------------------------------------


def test_compute_exg_mask_pure_green_detects_vegetation():
    # 10x10 image, all pixels pure green.
    arr = np.zeros((10, 10, 3), dtype=np.uint8)
    arr[:, :, 1] = 255
    mask = compute_exg_mask(arr, threshold=0.1)
    assert mask.shape == (10, 10)
    # Every pixel should be classified as vegetation.
    assert (mask == 255).all()


def test_compute_exg_mask_pure_red_is_not_vegetation():
    arr = np.zeros((10, 10, 3), dtype=np.uint8)
    arr[:, :, 0] = 255
    mask = compute_exg_mask(arr, threshold=0.1)
    assert (mask == 0).all()


def test_compute_exg_mask_all_black_returns_zero():
    # Total=0 is handled defensively; result should be non-vegetation.
    arr = np.zeros((10, 10, 3), dtype=np.uint8)
    mask = compute_exg_mask(arr, threshold=0.1)
    assert (mask == 0).all()


def test_compute_exg_mask_mixed_quadrants():
    # Top half green, bottom half red. After morph-close the boundary softens
    # slightly; the green half still dominates and the red half stays zero.
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    arr[0:10, :, 1] = 220
    arr[10:20, :, 0] = 220
    mask = compute_exg_mask(arr, threshold=0.1)
    # Upper half almost entirely vegetation; lower half essentially bare.
    assert (mask[:8, :] == 255).all()
    assert (mask[12:, :] == 0).all()


# ---------------------------------------------------------------------------
# estimate_height_from_dem
# ---------------------------------------------------------------------------


def test_estimate_height_from_dem_zero_size_returns_none():
    empty = np.zeros((0, 0), dtype=np.float32)
    mask = np.zeros((10, 10), dtype=np.uint8)
    assert estimate_height_from_dem(empty, mask) is None


def test_estimate_height_from_dem_all_zero_returns_none():
    # `valid_mask = dem != 0` → all invalid.
    dem = np.zeros((20, 20), dtype=np.float32)
    mask = np.full((20, 20), 255, dtype=np.uint8)
    assert estimate_height_from_dem(dem, mask) is None


def test_estimate_height_from_dem_flat_field_yields_zero():
    # Constant elevation, full vegetation → canopy_top == ground → height 0.
    dem = np.full((20, 20), 50.0, dtype=np.float32)
    mask = np.full((20, 20), 255, dtype=np.uint8)
    h = estimate_height_from_dem(dem, mask)
    assert h == 0.0


def test_estimate_height_from_dem_recovers_synthetic_canopy():
    # Ground at 100m, canopy at 102m covering the right half.
    dem = np.full((40, 40), 100.0, dtype=np.float32)
    dem[:, 20:] = 102.0
    mask = np.zeros((40, 40), dtype=np.uint8)
    mask[:, 20:] = 255  # vegetation on the canopy half
    h = estimate_height_from_dem(dem, mask)
    assert h is not None
    # 95th-percentile of canopy (102) − median of soil (100) = 2m, rounded to 4dp
    assert pytest.approx(h, abs=1e-3) == 2.0


def test_estimate_height_from_dem_negative_height_clamped_to_zero():
    # Pathological case: "canopy" below the ground. Should report 0, not
    # negative.
    dem = np.full((40, 40), 100.0, dtype=np.float32)
    dem[:, 20:] = 95.0
    mask = np.zeros((40, 40), dtype=np.uint8)
    mask[:, 20:] = 255
    h = estimate_height_from_dem(dem, mask)
    assert h == 0.0


# ---------------------------------------------------------------------------
# estimate_canopy_temperature
# ---------------------------------------------------------------------------


def test_canopy_temperature_averages_vegetation_pixels_only():
    # Left half vegetation at 25 °C, right half soil at 40 °C.
    thermal = np.full((4, 4), 40.0)
    thermal[:, :2] = 25.0
    mask = np.zeros((40, 40), np.uint8)
    mask[:, :20] = 255  # RGB mask is 10× finer; resized onto the thermal grid
    assert estimate_canopy_temperature(thermal, mask) == 25.0


def test_canopy_temperature_ignores_nodata_and_nan():
    thermal = np.array([[20.0, -9999.0], [np.nan, 30.0]])
    mask = np.full((2, 2), 255, np.uint8)
    assert estimate_canopy_temperature(thermal, mask, nodata=-9999.0) == 25.0


def test_canopy_temperature_none_without_vegetation_or_data():
    thermal = np.full((3, 3), 22.0)
    assert estimate_canopy_temperature(thermal, np.zeros((3, 3), np.uint8)) is None
    assert estimate_canopy_temperature(np.zeros((0, 0)), np.zeros((0, 0), np.uint8)) is None


# ---------------------------------------------------------------------------
# extract_traits_from_ortho with a thermal ortho
# ---------------------------------------------------------------------------


def _write_tif(path, bands, transform, crs="EPSG:4326", nodata=None):
    import rasterio

    arr = np.asarray(bands)
    if arr.ndim == 2:
        arr = arr[np.newaxis]
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[1], width=arr.shape[2],
        count=arr.shape[0], dtype=arr.dtype, crs=crs, transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(arr)


def test_extract_traits_reports_canopy_temperature(tmp_path):
    import json

    from rasterio.transform import from_origin

    # 100×100 px RGB over a 0.001° square: left half green, right half soil.
    rgb = np.zeros((3, 100, 100), np.uint8)
    rgb[1, :, :50] = 200  # green canopy
    rgb[:, :, 50:] = 120  # grey soil
    rgb_tf = from_origin(-121.0, 38.001, 0.00001, 0.00001)
    _write_tif(tmp_path / "rgb.tif", rgb, rgb_tf)

    # Thermal at 10× coarser resolution: canopy 24 °C, soil 38 °C.
    th = np.full((10, 10), 38.0, np.float32)
    th[:, :5] = 24.0
    _write_tif(
        tmp_path / "th.tif", th, from_origin(-121.0, 38.001, 0.0001, 0.0001),
        nodata=-9999.0,
    )

    boundary = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"plot": 1},
            "geometry": {"type": "Polygon", "coordinates": [[
                [-121.0, 38.0], [-120.999, 38.0], [-120.999, 38.001],
                [-121.0, 38.001], [-121.0, 38.0],
            ]]},
        }],
    }
    (tmp_path / "b.geojson").write_text(json.dumps(boundary))

    records, gj = extract_traits_from_ortho(
        rgb_path=str(tmp_path / "rgb.tif"),
        boundary_geojson_path=str(tmp_path / "b.geojson"),
        thermal_path=str(tmp_path / "th.tif"),
    )
    assert records[0]["Temp_veg_avg_C"] == pytest.approx(24.0)
    assert records[0]["Vegetation_Fraction"] == pytest.approx(0.5, abs=0.05)
    assert gj["features"][0]["properties"]["Temp_veg_avg_C"] == pytest.approx(24.0)

    # Without a thermal ortho the column is present but empty.
    records, _ = extract_traits_from_ortho(
        rgb_path=str(tmp_path / "rgb.tif"),
        boundary_geojson_path=str(tmp_path / "b.geojson"),
    )
    assert records[0]["Temp_veg_avg_C"] is None
