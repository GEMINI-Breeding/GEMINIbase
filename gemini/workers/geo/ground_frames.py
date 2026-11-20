"""Plot images from a ground track's raw frames (GROUND_PLOT_FRAMES): the
rover's or a handheld pass's own frames between each plot's marked start and
end, instead of a stitched mosaic.

For each marked plot:

  tiles/plot_{n}_accession_{a}_tile{k}.{ext}  the frames of the plot's stretch
                                              that do not overlap: each starts
                                              where the last one's view ends
  straightened/plot_{n}_accession_{a}.{ext}   the middle tile, the plot's one
                                              image (the plot viewer, Query,
                                              and a model's single image)
  manifest.json                               every plot's frames, tiles, and
                                              how it was named

Overlap is measured from the frames themselves: consecutive frames are
registered by phase correlation, and the shift along the direction of travel
adds up until a whole frame has passed. Counting on the tiles and summing per
plot (LOCATE_PLANTS with sum_per_plot) counts each plant once, where every
frame of an overlapping track would count it several times.

Which plot a stretch is, in order of trust:
  1. the drone plot boundary it was marked from (the marking records it);
  2. a field design paired with the markings, in marking order (no GPS);
  3. the plot boundary holding the stretch's mean GPS position;
  4. otherwise the marking's own number.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

THUMB = 256            # registration size (px, longer side)
MIN_PEAK = 8.0         # peak-to-sidelobe ratio below this: no reliable overlap
NEW_TILE = 0.98        # a new tile once this share of a frame has passed


def _gray(img) -> np.ndarray:
    """A PIL image → float grey thumbnail, longer side THUMB."""
    from PIL import Image

    g = img.convert("L")
    w, h = g.size
    s = THUMB / max(w, h)
    g = g.resize((max(16, int(w * s)), max(16, int(h * s))), Image.BILINEAR)
    a = np.asarray(g, dtype=np.float32)
    return a - a.mean()


def frame_step(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """(dx, dy, trust): how far b's view has moved from a's, as shares of
    the frame's width and height, and the trust in it: how many standard
    deviations the correlation peak stands above the rest of the surface
    (peak-to-sidelobe ratio; unrelated frames give about 4, overlapping ones
    tens). Phase correlation: reliable while consecutive frames overlap by
    more than about half."""
    if a.shape != b.shape:
        return 0.0, 0.0, 0.0
    h, w = a.shape
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    fa = np.fft.fft2(a * win)
    fb = np.fft.fft2(b * win)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    corr = np.fft.ifft2(r).real
    iy, ix = np.unravel_index(int(np.argmax(corr)), corr.shape)
    # The surface away from the peak (a small window round it left out).
    mask = np.ones_like(corr, dtype=bool)
    for yy in range(iy - 2, iy + 3):
        for xx in range(ix - 2, ix + 3):
            mask[yy % h, xx % w] = False
    side = corr[mask]
    peak = float((corr[iy, ix] - side.mean()) / (side.std() + 1e-12))
    dy = iy - h if iy > h // 2 else iy
    dx = ix - w if ix > w // 2 else ix
    return dx / w, dy / h, peak


def travel_steps(thumbs: Sequence[np.ndarray]) -> tuple[list[float], int]:
    """Per consecutive pair, how much of a frame passed along the direction
    of travel; and how many pairs could not be registered (counted as a
    whole frame: no overlap assumed, so nothing is counted twice)."""
    raw = [frame_step(thumbs[i], thumbs[i + 1]) for i in range(len(thumbs) - 1)]
    ok = [(dx, dy) for dx, dy, pk in raw if pk >= MIN_PEAK]
    # The direction of travel: the axis that moved most over the stretch.
    along_x = sum(abs(dx) for dx, _ in ok) >= sum(abs(dy) for _, dy in ok)
    steps, bad = [], 0
    for dx, dy, pk in raw:
        if pk < MIN_PEAK:
            steps.append(1.0)
            bad += 1
        else:
            steps.append(min(1.0, abs(dx if along_x else dy)))
    return steps, bad


def pick_tiles(steps: Sequence[float], new_tile: float = NEW_TILE) -> list[int]:
    """Indices of the frames that tile the stretch without overlap: the
    first frame, then each frame by which a whole frame has passed since
    the last tile."""
    tiles, moved = [0], 0.0
    for i, s in enumerate(steps, start=1):
        moved += s
        if moved >= new_tile:
            tiles.append(i)
            moved = 0.0
    return tiles


def stretch(frames: Sequence[str], start: str, end: str) -> list[str]:
    """The frames from a plot's start to its end, in track order (either way
    round: a pass driven back along the bed marks end before start)."""
    pos = {f: i for i, f in enumerate(frames)}
    if start not in pos or end not in pos:
        return []
    i, j = sorted((pos[start], pos[end]))
    return list(frames[i:j + 1])


def name_plot(
    sel: dict,
    order: int,
    *,
    design: Optional[Sequence[dict]],
    by_label: dict,
    centre: Optional[tuple[float, float]],
    polygons: list,
    match: Callable,
) -> tuple[dict, str]:
    """(plot properties, how it was named) for one marked plot (see the
    module's order of trust). `order` is the plot's place in the markings."""
    b = sel.get("boundary")
    if isinstance(b, dict) and b.get("label") not in (None, ""):
        label = str(b["label"])
        if label in by_label:
            return dict(by_label[label].get("properties") or {}), "drone plot boundary"
        return {**(b.get("properties") or {}), "plot": label}, "drone plot boundary"
    if design and order < len(design):
        return dict(design[order]), "field design, in marking order"
    if centre is not None and polygons:
        hit = match({"c": centre}, polygons).get("c")
        if hit is not None:
            return hit, "GPS inside a plot boundary"
    return {"plot": str(sel.get("plot_id"))}, "marking number"
