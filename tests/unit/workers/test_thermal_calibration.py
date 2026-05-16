"""Unit tests for thermal-calibration helpers and ThermalWorker routing.

The end-to-end MinIO/job side is covered by the docker-compose live
verification in plan Phase B.6; here we pin the pure-math contracts so
regressions in the calibration formulas surface as failures rather than
weird preview pixels.
"""
from __future__ import annotations

import numpy as np
import pytest

from gemini.workers.types import JobType


# ---------------------------------------------------------------------------
# Linear (Boson TLinear + user-defined)
# ---------------------------------------------------------------------------


def test_boson_centikelvin_maps_to_celsius():
    """Centikelvin: T_K = pixel * 0.01 — what BosonUSB and the farm-ng
    Amiga thermal rig emit. A pixel value of 33400 should resolve to
    ~60.85 °C. The Amiga's elevated scene readings are a camera-side
    artifact (also visible in FLIR's UI) and not a math error in our
    conversion — pinning the conversion contract here keeps that
    distinction observable from CI."""
    from gemini.workers.thermal.calibration import resolve_linear_mode

    lin = resolve_linear_mode("boson_centikelvin")
    assert lin.scale == 0.01
    assert lin.offset == 0.0
    counts = np.array([[33400]], dtype=np.uint16)
    t_c = lin.to_celsius(counts)
    assert pytest.approx(float(t_c[0, 0]), abs=0.01) == 60.85


def test_boson_tlinear_high_maps_to_celsius():
    """TLinear high-gain: T_K = pixel * 0.04, so T_C = pixel*0.04 - 273.15.

    A pixel value of 7500 should resolve to ~26.85 °C — a realistic
    field temperature. Bug if this drifts: previews would be palette-
    valid but the temperature HUD in the viewer would lie by tens of
    degrees.
    """
    from gemini.workers.thermal.calibration import resolve_linear_mode

    lin = resolve_linear_mode("boson_tlinear_high")
    counts = np.array([[7500]], dtype=np.uint16)
    t_c = lin.to_celsius(counts)
    assert t_c.shape == (1, 1)
    assert pytest.approx(float(t_c[0, 0]), abs=0.01) == 26.85


def test_boson_tlinear_low_maps_to_celsius():
    """Low-gain: 10x coarser scale, so the same 7500 counts → 26.85 K offset
    + 10x — basically a hot-blackbody check (~2726.85 °C in this synthetic
    case). We just verify the scale is 10x relative to high-gain at the
    same counts value, not the absolute value (which is unphysical for
    actual scenes captured in low gain — those scenes use much smaller
    counts)."""
    from gemini.workers.thermal.calibration import resolve_linear_mode

    high = resolve_linear_mode("boson_tlinear_high")
    low = resolve_linear_mode("boson_tlinear_low")
    counts = np.array([1000, 2000, 3000], dtype=np.uint16)
    # Difference between high and low temperatures should grow linearly
    # in counts: T_low - T_high = counts * (0.4 - 0.04) = counts * 0.36 K.
    diff = low.to_celsius(counts) - high.to_celsius(counts)
    assert np.allclose(diff, counts.astype(np.float32) * 0.36, rtol=1e-5)


def test_user_defined_mode_validates_scale():
    """User-defined needs a positive finite scale or we'd silently emit NaN
    for every pixel and the viewer would look broken without any error
    message."""
    from gemini.workers.thermal.calibration import resolve_linear_mode

    with pytest.raises(ValueError):
        resolve_linear_mode("user_defined", scale=None)
    with pytest.raises(ValueError):
        resolve_linear_mode("user_defined", scale=-0.04)
    with pytest.raises(ValueError):
        resolve_linear_mode("user_defined", scale=float("nan"))
    # Positive scale + offset accepted.
    lin = resolve_linear_mode("user_defined", scale=0.01, offset=0.0)
    assert lin.scale == 0.01 and lin.offset == 0.0


def test_unknown_mode_raises():
    from gemini.workers.thermal.calibration import resolve_linear_mode

    # `flir_one_pro` is Planck-based, not a linear mode — passing it to
    # `resolve_linear_mode` is a caller bug and should raise so the
    # worker's dispatch can't accidentally treat a FLIR JPEG as Boson.
    with pytest.raises(ValueError):
        resolve_linear_mode("flir_one_pro")
    with pytest.raises(ValueError):
        resolve_linear_mode("not_a_mode")


# ---------------------------------------------------------------------------
# Planck inversion (FLIR One Pro)
# ---------------------------------------------------------------------------


def test_planck_roundtrip_recovers_input_temperature():
    """Round-trip: pick a known T_K, compute S via FLIR's forward Planck
    formula, then feed S into planck_signal_to_celsius and verify the
    output matches T_C within float tolerance.

    Constants come from the amiga_low_res example dataset
    (R1=17450.25, B=1435, F=1, O=-2640, R2=0.0125), which is the
    standard FLIR One Pro gen 3 set."""
    from gemini.workers.thermal.calibration import (
        PlanckParams,
        KELVIN_TO_CELSIUS,
        planck_signal_to_celsius,
    )

    p = PlanckParams(r1=17450.25, b=1435.0, f=1.0, o=-2640.0, r2=0.0125)
    target_kelvin = np.array([280.0, 300.0, 320.0], dtype=np.float64)
    # Forward: S = R1 / (R2 * (exp(B/T_K) - F)) - O
    s_float = p.r1 / (p.r2 * (np.exp(p.b / target_kelvin) - p.f)) - p.o
    counts = np.round(s_float).astype(np.uint16)
    recovered_c = planck_signal_to_celsius(counts, p, emissivity=1.0)
    expected_c = target_kelvin - KELVIN_TO_CELSIUS
    # Quantization to uint16 limits accuracy; 0.5 °C is plenty for the
    # contract that "the inversion math is correct".
    assert np.allclose(recovered_c, expected_c, atol=0.5)


def test_planck_emissivity_lower_means_higher_inferred_temp():
    """For a hot object viewed through a low-emissivity surface (e.g. metal),
    the same raw counts must resolve to a *higher* inferred temperature
    when emissivity is lower — the camera reads less radiation, but we
    attribute the deficit to a colder ambient correction, so the object
    itself must be hotter to explain the signal.

    This is the directional contract the viewer's "emissivity" slider
    will rely on; getting the sign wrong is a silent class of bug."""
    from gemini.workers.thermal.calibration import (
        PlanckParams,
        planck_signal_to_celsius,
    )

    p = PlanckParams(r1=17450.25, b=1435.0, f=1.0, o=-2640.0, r2=0.0125)
    counts = np.array([[33000]], dtype=np.uint16)
    t_high_eps = planck_signal_to_celsius(counts, p, emissivity=1.0)
    t_low_eps = planck_signal_to_celsius(counts, p, emissivity=0.5)
    assert float(t_low_eps[0, 0]) > float(t_high_eps[0, 0])


# ---------------------------------------------------------------------------
# Palette + windowing
# ---------------------------------------------------------------------------


def test_apply_palette_emits_rgb_uint8_with_correct_shape():
    from gemini.workers.thermal.calibration import IRON_LUT, apply_palette

    arr = np.array([[0.0, 0.5], [1.0, 0.25]], dtype=np.float32)
    rgb = apply_palette(arr, vmin=0.0, vmax=1.0, lut=IRON_LUT)
    assert rgb.shape == (2, 2, 3)
    assert rgb.dtype == np.uint8
    # Mins/maxes of LUT correspond to vmin/vmax endpoints.
    assert tuple(rgb[0, 0]) == tuple(IRON_LUT[0])
    assert tuple(rgb[1, 0]) == tuple(IRON_LUT[255])


def test_apply_palette_handles_degenerate_window():
    """vmin == vmax used to divide by zero. Now returns solid black."""
    from gemini.workers.thermal.calibration import apply_palette

    arr = np.array([[1.0, 2.0]], dtype=np.float32)
    rgb = apply_palette(arr, vmin=5.0, vmax=5.0)
    assert rgb.shape == (1, 2, 3)
    assert (rgb == 0).all()


def test_apply_palette_renders_nan_as_black():
    """Planck inversion can produce NaNs for pathological pixels; those
    must render as black instead of garbage from the LUT index path."""
    from gemini.workers.thermal.calibration import apply_palette

    arr = np.array([[0.5, np.nan]], dtype=np.float32)
    rgb = apply_palette(arr, vmin=0.0, vmax=1.0)
    assert tuple(rgb[0, 1]) == (0, 0, 0)


def test_percentile_window_robust_to_outliers():
    """2/98 percentile window must clip rail-pinned outliers so the preview
    isn't washed out by a single hot sky pixel. Pin a scene where 99%
    of pixels are in [10, 20] and 1% are at 1000 — the 98th percentile
    of the 10×10000 scene should land near 20, not anywhere near 1000."""
    from gemini.workers.thermal.calibration import percentile_window

    rng = np.random.default_rng(seed=0)
    scene = rng.uniform(10.0, 20.0, size=(100, 100)).astype(np.float32)
    # 1% of pixels (=100) get pinned to 1000 — well under the 2%
    # bottom and over the 98% top, so the clip should ignore them.
    flat = scene.reshape(-1)
    flat[:100] = 1000.0
    scene = flat.reshape(100, 100)
    vmin, vmax = percentile_window(scene)
    assert vmin == pytest.approx(10.0, abs=1.0)
    # vmax must be inside the [10, 20] uniform band, not pulled toward
    # the 1000-valued outliers.
    assert vmax < 25.0, f"vmax={vmax} should not be pulled to outlier band"


# ---------------------------------------------------------------------------
# Worker dispatch
# ---------------------------------------------------------------------------


class TestThermalWorkerDispatch:
    """Smoke checks for the worker class. The full MinIO + exiftool round
    trip is covered by Phase B.6's live verification — here we just pin
    the routing contracts."""

    def test_supported_job_types(self):
        from gemini.workers.thermal.worker import ThermalWorker

        worker = ThermalWorker(worker_id="test-thermal")
        assert worker.supported_job_types == {JobType.THERMAL_EXTRACT}

    def test_rejects_unknown_job_type(self):
        from gemini.workers.thermal.worker import ThermalWorker

        worker = ThermalWorker(worker_id="test")
        with pytest.raises(ValueError):
            worker.process("job-1", "RUN_ODM", {})

    def test_rejects_missing_calibration_mode(self):
        from gemini.workers.thermal.worker import ThermalWorker

        worker = ThermalWorker(worker_id="test")
        with pytest.raises(ValueError):
            worker.process(
                "job-1",
                "THERMAL_EXTRACT",
                {"year": "2024", "experiment": "X"},
            )


class TestThermalPrefixBuilder:
    """The thermal worker accepts either an explicit dataset_prefix
    (wizard path) or structured year/.../sensor fields (ODM path).
    Both must end in `/`."""

    def test_explicit_dataset_prefix_wins(self):
        from gemini.workers.thermal.worker import _build_dataset_prefix

        out = _build_dataset_prefix({
            "dataset_prefix": "Raw/2024-07-25/GEMINI",
            "year": "ignored",
        })
        assert out == "Raw/2024-07-25/GEMINI/"

    def test_explicit_prefix_keeps_trailing_slash_if_present(self):
        from gemini.workers.thermal.worker import _build_dataset_prefix

        out = _build_dataset_prefix({"dataset_prefix": "Raw/X/"})
        assert out == "Raw/X/"

    def test_structured_prefix_matches_odm_layout(self):
        from gemini.workers.thermal.worker import _build_dataset_prefix

        out = _build_dataset_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "DavisFarm",
            "population": "PopA",
            "date": "2024-07-25",
            "platform": "DJI",
            "sensor": "FLIR-One-Pro",
        })
        assert out == "Raw/2024/GEMINI/DavisFarm/PopA/2024-07-25/DJI/FLIR-One-Pro/"

    def test_structured_prefix_skips_empty_fields(self):
        from gemini.workers.thermal.worker import _build_dataset_prefix

        # location/population are commonly empty in wizard imports; the
        # prefix collapses cleanly rather than emitting `//`.
        out = _build_dataset_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "DJI",
            "sensor": "FLIR-One-Pro",
        })
        assert out == "Raw/2024/GEMINI/2024-07-25/DJI/FLIR-One-Pro/"

    def test_structured_prefix_with_dataset_short_id(self):
        """Per-dataset isolation: the short-id segment lands between
        sensor and the trailing slash so two uploads at the same scope
        don't commingle on disk."""
        from gemini.workers.thermal.worker import _build_dataset_prefix

        out = _build_dataset_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "Davis",
            "population": "Cowpea MAGIC",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "Thermal",
            "dataset_short_id": "a2f31b04",
        })
        assert out == (
            "Raw/2024/GEMINI/Davis/Cowpea MAGIC/2024-07-25/Drone/Thermal/"
            "a2f31b04/"
        )

    def test_structured_prefix_without_dataset_short_id(self):
        """Backward-compatible fallback for legacy callers that never
        pass the short-id."""
        from gemini.workers.thermal.worker import _build_dataset_prefix

        out = _build_dataset_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "DJI",
            "sensor": "Thermal",
        })
        assert out == "Raw/2024/GEMINI/2024-07-25/DJI/Thermal/"
