"""A flight's other cameras: frames another sensor took at the same moments as
the RGB frames (a drone's thermal camera beside its wide camera, say), lined
up with them so each plot can be cut from those frames too.

  pair            each RGB frame's companion frame, by capture time (the time in
                  DJI-style names, ``DJI_20260817100534_0513_T.tif``, else EXIF);
                  the sequence number decides between frames a second apart.
  register        where a companion frame sits in its RGB frame: a scale and a
                  shift (the two cameras share the gimbal), found by correlating
                  the RGB frame's greenness with the companion's signal (plants
                  are cooler than soil, so a thermal frame's minus temperature).
  flight_alignment the flight's alignment: the median over several pairs, after
                  dropping pairs that disagree (a frame of uniform canopy has
                  nothing to line up on).
  refine          one frame's own alignment near the flight's: the cameras do not
                  fire at quite the same instant on a moving drone (a few cm on
                  the ground); kept only where the frame lines up clearly.
  companion_lens  that alignment as a lens on the RGB frame's pose, so the
                  companion frames rank, crop and straighten with frames.py
                  exactly as the RGB frames do.
  canopy_from_fraction  a plot's canopy temperature from its thermal pixels that
                  are (nearly) all plant, each pixel's plant share measured in the
                  RGB view of the same ground (plant_fraction).

Pure numpy, like frames.py.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

import numpy as np

from .frames import Lens

# DJI_YYYYMMDDhhmmss_NNNN_<kind>.<ext> (and names that carry the same two numbers).
_NAME_TIME = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})_?(\d{2})(\d{2})(\d{2})(?:[._-]?(\d{1,3}))?_(\d{3,5})(?!\d)")
_EXIF_TIME = re.compile(rb"(20\d{2}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})")

EXG_PLANT = 0.1               # excess green above which an RGB pixel is plant (as EXTRACT_TRAITS)


def frame_key(name: str) -> tuple[Optional[float], Optional[int]]:
    """(capture time in seconds, sequence number) from a frame's file name; None where absent."""
    m = _NAME_TIME.search(name.rsplit("/", 1)[-1])
    if not m:
        return None, None
    y, mo, d, h, mi, s, ms, seq = m.groups()
    try:
        t = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s)).timestamp()
    except ValueError:
        return None, None
    if ms:
        t += int(ms) / 10 ** len(ms)
    return t, int(seq)


def exif_time(head: bytes) -> Optional[float]:
    """The first EXIF date-time in a file's first bytes (DateTimeOriginal comes first in
    most cameras' EXIF), in seconds."""
    m = _EXIF_TIME.search(head)
    if not m:
        return None
    try:
        return datetime(*map(int, m.groups())).timestamp()
    except ValueError:
        return None


def pair(primary: dict[str, tuple[Optional[float], Optional[int]]],
         companion: dict[str, tuple[Optional[float], Optional[int]]],
         max_dt_s: float = 2.0) -> dict[str, tuple[str, float]]:
    """Each primary frame's companion frame: {primary: (companion, seconds apart)}.

    Frames are matched by time within ``max_dt_s``. Of the companions that close, the one
    with the same sequence number wins (the cameras count together, while their clocks
    round to the second differently), then the closest in time. A companion is used once."""
    comp = sorted(((t, seq, n) for n, (t, seq) in companion.items() if t is not None), key=lambda x: x[0])
    times = np.array([c[0] for c in comp]) if comp else np.zeros(0)
    taken: set[str] = set()
    out: dict[str, tuple[str, float]] = {}
    for name, (t, seq) in sorted(primary.items(), key=lambda kv: (kv[1][0] is None, kv[1][0] or 0)):
        if t is None or not len(times):
            continue
        lo, hi = np.searchsorted(times, t - max_dt_s), np.searchsorted(times, t + max_dt_s, side="right")
        near = [c for c in comp[lo:hi] if c[2] not in taken]
        if not near:
            continue
        best = min(near, key=lambda c: (seq is None or c[1] != seq, abs(c[0] - t),
                                        abs((c[1] or 0) - (seq or 0))))
        taken.add(best[2])
        out[name] = (best[2], round(best[0] - t, 3))
    return out


# -- lining a companion frame up with its RGB frame ------------------------------------------------

@dataclass
class Alignment:
    k: float          # RGB pixels per companion pixel
    x0: float         # where the companion frame's top-left corner is in the RGB frame
    y0: float
    score: float      # normalised cross-correlation of the two (1 = identical)


def greenness(rgb: np.ndarray) -> np.ndarray:
    """Excess green, normalised by brightness: (2G - R - B) / (R + G + B)."""
    v = rgb.astype(np.float32)
    return (2 * v[..., 1] - v[..., 0] - v[..., 2]) / (v.sum(axis=2) + 1e-6)


def _resize(a: np.ndarray, w: int, h: int) -> np.ndarray:
    from PIL import Image

    return np.asarray(Image.fromarray(a.astype(np.float32)).resize((w, h), Image.BILINEAR), dtype=np.float32)


def _box_blur(a: np.ndarray) -> np.ndarray:
    p = np.pad(a, 1, mode="edge")
    return sum(p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9.0


def _ncc(img: np.ndarray, tpl: np.ndarray) -> np.ndarray:
    """Normalised cross-correlation of ``tpl`` at every offset where it fits inside ``img``."""
    H, W = img.shape
    h, w = tpl.shape
    t = tpl - tpl.mean()
    t /= t.std() + 1e-9
    num = np.fft.irfft2(np.fft.rfft2(img, s=(H, W)) * np.fft.rfft2(t[::-1, ::-1], s=(H, W)), s=(H, W))
    num = num[h - 1:H, w - 1:W]
    c1 = np.pad(img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    c2 = np.pad(img * img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    s1 = c1[h:, w:] - c1[:-h, w:] - c1[h:, :-w] + c1[:-h, :-w]
    s2 = c2[h:, w:] - c2[:-h, w:] - c2[h:, :-w] + c2[:-h, :-w]
    n = h * w
    return num / (np.sqrt(np.maximum(s2 - s1 * s1 / n, 1e-9)) * math.sqrt(n))


def _peak(m: np.ndarray) -> tuple[float, float, float]:
    """The correlation map's highest point, to a fraction of a cell (a parabola through
    the peak and its neighbours, along each axis)."""
    iy, ix = np.unravel_index(int(np.argmax(m)), m.shape)

    def off(a, b, c):
        d = a - 2 * b + c
        return 0.0 if d >= 0 else float(np.clip(0.5 * (a - c) / d, -0.5, 0.5))

    dx = off(m[iy, ix - 1], m[iy, ix], m[iy, ix + 1]) if 0 < ix < m.shape[1] - 1 else 0.0
    dy = off(m[iy - 1, ix], m[iy, ix], m[iy + 1, ix]) if 0 < iy < m.shape[0] - 1 else 0.0
    return ix + dx, iy + dy, float(m[iy, ix])


def register(rgb_signal: np.ndarray, comp_signal: np.ndarray, k_range: tuple[float, float] = (1.0, 8.0),
             work: float = 0.5) -> Optional[Alignment]:
    """Where ``comp_signal`` (a companion frame turned into something that looks like
    ``rgb_signal``: minus temperature for greenness) sits in the RGB frame. The scale is
    searched over ``k_range`` with the companion frame at ``work`` of its size, then
    refined at its full size; at each scale the shift comes from an FFT correlation, to a
    fraction of a pixel. None when the companion frame cannot fit inside the RGB frame."""
    h, w = comp_signal.shape
    templates: dict[float, np.ndarray] = {}

    def template(wk: float) -> np.ndarray:
        if wk not in templates:
            templates[wk] = _box_blur(_resize(comp_signal, max(8, int(w * wk)), max(8, int(h * wk))))
        return templates[wk]

    if template(work).std() < 1e-6:
        return None

    def at(scales, wk: float) -> Optional[Alignment]:
        tpl = template(wk)
        best = None
        for k in scales:
            f = wk / k
            rw, rh = int(rgb_signal.shape[1] * f), int(rgb_signal.shape[0] * f)
            if rw <= tpl.shape[1] or rh <= tpl.shape[0]:
                continue
            x, y, s = _peak(_ncc(_box_blur(_resize(rgb_signal, rw, rh)), tpl))
            if best is None or s > best.score:
                best = Alignment(float(k), x / f, y / f, s)
        return best

    lo = max(k_range[0], 1e-3)
    hi = min(k_range[1], rgb_signal.shape[1] / w, rgb_signal.shape[0] / h)
    if hi < lo:
        return None
    coarse = at(np.geomspace(lo, hi, 32) if hi > lo else [lo], work)
    if coarse is None:
        return None
    fine = at(np.linspace(max(lo, coarse.k * 0.98), min(hi, coarse.k * 1.02), 11), 1.0)
    return fine if fine is not None else coarse


def refine(rgb_signal: np.ndarray, comp_signal: np.ndarray, flight: dict, search_px: float = 90.0,
           min_score: float = 0.25) -> Optional[Alignment]:
    """One frame's own alignment near the flight's: the scale within 1 % of it, the shift
    within ``search_px`` RGB pixels (the cameras do not fire at quite the same instant, and
    the drone moves). None when nothing there correlates well enough: then the flight's
    alignment stands."""
    h, w = comp_signal.shape
    tpl = _box_blur(comp_signal.astype(np.float32))
    if tpl.std() < 1e-6:
        return None
    best = None
    for k in np.linspace(flight["k"] * 0.99, flight["k"] * 1.01, 5):
        f = 1.0 / k
        # The RGB frame around where the flight's alignment puts this frame, at this camera's scale.
        x0, y0 = flight["x0"] - search_px, flight["y0"] - search_px
        x1, y1 = flight["x0"] + w * k + search_px, flight["y0"] + h * k + search_px
        X0, Y0 = max(0, int(x0)), max(0, int(y0))
        X1, Y1 = min(rgb_signal.shape[1], int(math.ceil(x1))), min(rgb_signal.shape[0], int(math.ceil(y1)))
        rw, rh = int((X1 - X0) * f), int((Y1 - Y0) * f)
        if rw <= w or rh <= h:
            continue
        region = _box_blur(_resize(rgb_signal[Y0:Y1, X0:X1], rw, rh))
        x, y, s = _peak(_ncc(region, tpl))
        a = Alignment(float(k), X0 + x / f, Y0 + y / f, s)
        if best is None or a.score > best.score:
            best = a
    if best is None or best.score < min_score:
        return None
    if math.hypot(best.x0 - flight["x0"], best.y0 - flight["y0"]) > search_px:
        return None
    return best


def flight_alignment(found: list[Alignment], k_tol: float = 0.04, shift_tol_px: float = 80.0) -> dict:
    """One alignment for the flight: the median of the pairs that agree with it.
    Returns {"k", "x0", "y0", "pairs_used", "pairs_tried", "spread_px", "score"}."""
    found = [a for a in found if a is not None and math.isfinite(a.score)]
    if not found:
        raise ValueError("no frame pair could be lined up")
    k = float(np.median([a.k for a in found]))
    x0 = float(np.median([a.x0 for a in found]))
    y0 = float(np.median([a.y0 for a in found]))
    agree = [a for a in found if abs(a.k / k - 1) <= k_tol and math.hypot(a.x0 - x0, a.y0 - y0) <= shift_tol_px]
    if len(agree) < max(2, len(found) // 3):
        raise ValueError(f"the frame pairs do not agree on how the two cameras line up "
                         f"({len(agree)} of {len(found)} agree)")
    k = float(np.median([a.k for a in agree]))
    x0 = float(np.median([a.x0 for a in agree]))
    y0 = float(np.median([a.y0 for a in agree]))
    spread = float(np.median([math.hypot(a.x0 - x0, a.y0 - y0) for a in agree]))
    return {"k": round(k, 4), "x0": round(x0, 1), "y0": round(y0, 1), "pairs_used": len(agree),
            "pairs_tried": len(found), "spread_px": round(spread, 1),
            "score": round(float(np.median([a.score for a in agree])), 3)}


def companion_lens(rgb: Lens, width: int, height: int, k: float, x0: float, y0: float) -> Lens:
    """The companion camera as a lens on the RGB camera's pose: its pixel (u, v) shows RGB
    pixel (x0 + k u, y0 + k v). Same distortion (it acts on the normalised coordinates)."""
    s, st = max(rgb.width, rgb.height), max(width, height)
    fx = rgb.fx * s / (k * st)
    fy = rgb.fy * s / (k * st)
    cx = (rgb.cx * s / k + (rgb.width / 2.0 - 0.5 - x0) / k - (width / 2.0 - 0.5)) / st
    cy = (rgb.cy * s / k + (rgb.height / 2.0 - 0.5 - y0) / k - (height / 2.0 - 0.5)) / st
    return replace(rgb, width=int(width), height=int(height), fx=fx, fy=fy, cx=cx, cy=cy)


# -- what a plot's companion view says -------------------------------------------------------------

def plant_fraction(plant: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Share of plant in each cell of a coarser grid over the same ground: ``plant`` (the
    RGB view's plant cells) averaged into ``size`` = (width, height) cells."""
    from PIL import Image

    return np.asarray(Image.fromarray(plant.astype(np.float32)).resize(size, Image.BOX), dtype=np.float32)


def _neighbourhood(a: np.ndarray, r: int, fn) -> np.ndarray:
    """``fn`` (np.minimum / np.maximum) over each cell's (2r+1)² neighbourhood, edges repeated."""
    p = np.pad(a, r, mode="edge")
    out = a.copy()
    H, W = a.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = fn(out, p[r + dy:r + dy + H, r + dx:r + dx + W])
    return out


def canopy_from_fraction(temp: np.ndarray, plant: np.ndarray, valid: np.ndarray, pure: float = 0.8,
                         bare: float = 0.1, min_cells: int = 10, reach: int = 1) -> dict:
    """A plot's canopy temperature from its thermal cells: the cells that are nearly all plant
    — and whose neighbours are too, within ``reach`` cells, since a thermal reading blends its
    neighbours' (lens blur, resampling); a cell next to soil reads warmer — and, for comparison,
    the nearly bare ones. Few such cells (a sparse canopy): cells over half plant, as
    ``plant_cells_rule`` says."""
    t = temp.astype(np.float64)
    ok = valid & np.isfinite(t) & (t > -80) & (t < 150)
    rule = f">= {pure} with neighbours"
    canopy = ok & (_neighbourhood(plant, reach, np.minimum) >= pure)
    if canopy.sum() < min_cells:
        canopy, rule = ok & (plant >= 0.5), ">= 0.5 (few cells all plant)"
    soil = ok & (_neighbourhood(plant, reach, np.maximum) <= bare)
    out: dict = {"plant_cells": int(canopy.sum()), "seen_cells": int(ok.sum()),
                 "plant_share": round(float(plant[ok].mean()), 3) if ok.any() else 0.0,
                 "plant_cells_rule": rule}
    if canopy.any():
        v = t[canopy]
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        out.update({"canopy_mean_c": round(float(v.mean()), 2), "canopy_median_c": round(float(med), 2),
                    "canopy_iqr_c": round(float(q3 - q1), 2)})
    if soil.any():
        out["soil_mean_c"] = round(float(t[soil].mean()), 2)
    return out
