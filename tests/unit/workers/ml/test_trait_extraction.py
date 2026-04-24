"""Unit tests for the trait-extraction kernels."""
import numpy as np
import pytest

from gemini.workers.ml.trait_extraction import (
    compute_exg_mask,
    estimate_height_from_dem,
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
