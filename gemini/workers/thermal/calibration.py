"""
Pixel → temperature conversion + palette mapping for the THERMAL_EXTRACT worker.

Three sources land here:

1. FLIR Boson radiometric TIFFs (TLinear high-gain / low-gain) — uint16
   pixels with a fixed firmware scale baked into the camera mode. The
   wizard collects the mode at import time because the file alone
   doesn't say which mode it was captured in.

2. User-defined scale + offset — same shape as Boson modes but with
   constants the user typed instead of the named TLinear pair.

3. FLIR One Pro JPEGs — Planck-constant-based, fully self-describing.
   We extract the embedded RawThermalImage PNG plus the Planck params
   from EXIF, then invert with the standard FLIR Planck equation.

Boson AGC (non-radiometric) skips temperature entirely — we only window
and palette the raw uint16. The viewer hides °C readouts for those.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------

# Pre-baked (scale K/count, offset K) for the named Boson firmware modes.
#
#   - centikelvin (Amiga + BosonUSB default): T_K = pixel * 0.01. The
#     pixel value is the temperature in centikelvin (1/100 K). This
#     is what FLIR's BosonUSB capture tool emits by default and what
#     the farm-ng Amiga thermal rig writes:
#     https://github.com/FLIR/BosonUSB/blob/master/BosonUSB.cpp
#     A pixel of 33400 → 334.0 K → 60.85 °C. Some scenes produce
#     elevated readings even via FLIR's own UI; that's a camera-
#     side issue, not a calibration error.
#   - TLinear high-gain: T_K = pixel * 0.04. A documented Boson
#     radiometric firmware mode with 0.04 K resolution.
#   - TLinear low-gain : T_K = pixel * 0.4. The 0.4 K-resolution mode.
#
# All three write temperature directly into the pixel; the offset is
# always 0 (no 273.15 K subtraction baked into the pixel value).
BOSON_PRESETS: dict[str, tuple[float, float]] = {
    "boson_centikelvin": (0.01, 0.0),
    "boson_tlinear_high": (0.04, 0.0),
    "boson_tlinear_low": (0.4, 0.0),
}

KELVIN_TO_CELSIUS = 273.15


@dataclass
class LinearMode:
    """Resolved scale/offset for a linear Boson-class radiometric mode."""

    scale: float
    offset: float

    def to_celsius(self, counts: np.ndarray) -> np.ndarray:
        """Vectorised T_C = (counts * scale + offset) - 273.15."""
        return (counts.astype(np.float32) * self.scale + self.offset) - KELVIN_TO_CELSIUS


def resolve_linear_mode(
    mode: str,
    *,
    scale: float | None = None,
    offset: float | None = None,
) -> LinearMode:
    """Pick the (scale, offset) pair for a linear radiometric mode.

    `mode` must be one of the named Boson presets or `user_defined`.
    For `user_defined`, scale must be a positive number; offset
    defaults to 0 when omitted.
    """
    if mode in BOSON_PRESETS:
        s, o = BOSON_PRESETS[mode]
        return LinearMode(scale=s, offset=o)
    if mode == "user_defined":
        if scale is None or not math.isfinite(scale) or scale <= 0:
            raise ValueError(
                "user_defined thermal calibration requires a positive scale"
            )
        return LinearMode(scale=float(scale), offset=float(offset or 0.0))
    raise ValueError(f"Not a linear radiometric mode: {mode!r}")


# ---------------------------------------------------------------------------
# FLIR One Pro / Planck inversion
# ---------------------------------------------------------------------------


@dataclass
class PlanckParams:
    """FLIR Planck constants extracted from a per-image EXIF block.

    The forward direction (temperature → raw count) is:

        S = R1 / (R2 * (exp(B / T_K) - F)) - O

    The inverse — which is what we want — is:

        T_K = B / ln( R1 / (R2 * (S + O)) + F )

    Reflectivity / atmospheric corrections (emissivity, distance,
    humidity, etc.) are folded in upstream by computing an effective
    `S` from the raw S; we keep that out of this dataclass since the
    correction policy can vary. For our v1 we use the raw signal with
    the user's emissivity setting applied as a single multiplier.
    """

    r1: float
    b: float
    f: float
    o: float
    r2: float


def planck_signal_to_celsius(
    counts: np.ndarray,
    p: PlanckParams,
    *,
    emissivity: float = 1.0,
) -> np.ndarray:
    """Invert the FLIR Planck equation for a uint16 raw-thermal frame.

    Returns °C as float32. Pixels with non-finite intermediate values
    (e.g. zeros that send the log to -inf) become NaN, which the
    caller should mask before computing min/max.
    """
    if emissivity <= 0 or emissivity > 1:
        raise ValueError("emissivity must be in (0, 1]")
    s = counts.astype(np.float64) / emissivity
    # The denominator can go non-positive for pathological values; let
    # numpy emit NaN/Inf and we mask after.
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = p.r2 * (s + p.o)
        ratio = p.r1 / denom + p.f
        t_k = p.b / np.log(ratio)
    t_c = (t_k - KELVIN_TO_CELSIUS).astype(np.float32)
    t_c[~np.isfinite(t_c)] = np.nan
    return t_c


# ---------------------------------------------------------------------------
# Palette / preview
# ---------------------------------------------------------------------------


def _build_iron_palette() -> np.ndarray:
    """256×3 uint8 lookup table for the "iron" thermal palette.

    Stops sampled from the standard FLIR iron ramp. Good enough for the
    server-side preview; the viewer can re-render with any palette it
    likes from the raw uint16.
    """
    # Anchors: (position 0..1, R, G, B).
    stops = [
        (0.00, 0, 0, 0),
        (0.20, 32, 0, 96),
        (0.40, 128, 0, 128),
        (0.55, 224, 32, 32),
        (0.75, 255, 160, 0),
        (0.90, 255, 240, 128),
        (1.00, 255, 255, 255),
    ]
    lut = np.zeros((256, 3), dtype=np.uint8)
    positions = np.array([s[0] for s in stops])
    colors = np.array([(s[1], s[2], s[3]) for s in stops], dtype=np.float32)
    xs = np.linspace(0.0, 1.0, 256)
    for c in range(3):
        lut[:, c] = np.clip(np.interp(xs, positions, colors[:, c]), 0, 255).astype(np.uint8)
    return lut


IRON_LUT = _build_iron_palette()


def apply_palette(
    values: np.ndarray,
    *,
    vmin: float,
    vmax: float,
    lut: np.ndarray = IRON_LUT,
) -> np.ndarray:
    """Window `values` to [vmin, vmax] and apply a 256-entry LUT.

    NaNs (e.g. from Planck inversion) render as solid black. `values`
    can be raw uint16 counts or °C — the function just rescales.
    """
    if not math.isfinite(vmin) or not math.isfinite(vmax) or vmax <= vmin:
        # Degenerate window: emit a flat black image rather than crash.
        rgb = np.zeros((*values.shape, 3), dtype=np.uint8)
        return rgb
    arr = values.astype(np.float32)
    # NaNs become 0 in the index path here; the mask below paints them
    # black afterwards. `np.nan_to_num` keeps the cast warning-free.
    nan_mask = ~np.isfinite(arr)
    arr_for_index = np.nan_to_num(arr, nan=vmin, posinf=vmax, neginf=vmin)
    norm = np.clip((arr_for_index - vmin) / (vmax - vmin), 0.0, 1.0)
    idx = (norm * 255).astype(np.uint8)
    rgb = lut[idx]
    if nan_mask.any():
        rgb[nan_mask] = (0, 0, 0)
    return rgb


def percentile_window(
    values: np.ndarray,
    *,
    lo: float = 2.0,
    hi: float = 98.0,
) -> tuple[float, float]:
    """Return (vmin, vmax) at the requested percentiles, NaN-safe.

    Used for the default preview window when the dataset doesn't carry
    an explicit user-set range. The 2/98 default matches what
    radiometric viewers like FLIR Tools do when "auto-range" is on —
    enough headroom for hot/cold outliers (sky, glints) without
    sacrificing scene contrast.
    """
    flat = values[np.isfinite(values)]
    if flat.size == 0:
        return (0.0, 1.0)
    vmin = float(np.percentile(flat, lo))
    vmax = float(np.percentile(flat, hi))
    if vmax <= vmin:
        vmax = vmin + 1.0
    return (vmin, vmax)
