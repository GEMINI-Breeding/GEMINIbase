"""Raw drone frames placed on the ground with the camera positions of an ODM
run, so each plot can be given the frames that show it best.

ODM writes, for every frame it placed, the camera's position and rotation
(``odm_report/shots.geojson``, in the projected CRS of its orthomosaic) and
the lens of each camera model (``cameras.json``: OpenSfM's ``perspective`` or
``brown`` model). With those, a point on the ground projects into a frame
exactly as the reconstruction saw it. Because the orthomosaic comes from the
same reconstruction, plot boundaries aligned to that orthomosaic line up with
these cameras too, whatever the GPS error of that flight.

Pure numpy: used by the geo worker's SPLIT_ORTHOMOSAIC (source="frames").
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Lens:
    width: int
    height: int
    fx: float          # focal length / max(width, height)
    fy: float
    cx: float = 0.0    # principal point offset / max(width, height)
    cy: float = 0.0
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    p1: float = 0.0
    p2: float = 0.0


@dataclass
class Shot:
    filename: str
    center: np.ndarray        # (3,) camera position, in the orthomosaic's CRS (metres)
    rotation: np.ndarray      # (3, 3) world -> camera
    lens: Lens


def _rodrigues(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    theta = float(np.linalg.norm(v))
    if theta < 1e-12:
        return np.eye(3)
    k = v / theta
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(theta) * kx + (1 - math.cos(theta)) * kx @ kx


def read_lenses(cameras: dict) -> dict[str, Lens]:
    """ODM's cameras.json -> {camera id: Lens}."""
    out = {}
    for cid, c in cameras.items():
        kind = c.get("projection_type", "perspective")
        if kind not in ("perspective", "brown"):
            raise ValueError(f"camera model {kind} is not supported (perspective or brown only)")
        f = c.get("focal")
        out[cid] = Lens(
            width=int(c["width"]), height=int(c["height"]),
            fx=float(c.get("focal_x", f)), fy=float(c.get("focal_y", f)),
            cx=float(c.get("c_x", 0.0)), cy=float(c.get("c_y", 0.0)),
            k1=float(c.get("k1", 0.0)), k2=float(c.get("k2", 0.0)), k3=float(c.get("k3", 0.0)),
            p1=float(c.get("p1", 0.0)), p2=float(c.get("p2", 0.0)),
        )
    return out


def read_shots(geojson: dict, lenses: dict[str, Lens]) -> list[Shot]:
    """ODM's shots.geojson -> shots, with the rotation's direction checked.

    OpenSfM's rotation takes world to camera coordinates; a drone camera then
    looks down (its optical axis has a negative world z). If the file's
    rotations look the other way round, they are taken as camera -> world."""
    rows = []
    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        lens = lenses.get(str(p.get("camera")))
        if lens is None and len(lenses) == 1:
            lens = next(iter(lenses.values()))
        if lens is None or p.get("translation") is None or p.get("rotation") is None:
            continue
        rows.append((str(p["filename"]), np.array(p["translation"], float), _rodrigues(p["rotation"]), lens))
    if not rows:
        return []
    axis_z = np.median([(r.T @ np.array([0.0, 0.0, 1.0]))[2] for _, _, r, _ in rows])
    flip = axis_z > 0
    return [Shot(n, c, (r.T if flip else r), lens) for n, c, r, lens in rows]


def project(shot: Shot, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """World points (N, 3) -> pixel coordinates (N, 2) and depth (N,) in front of the camera."""
    cam = (shot.rotation @ (np.asarray(pts, float) - shot.center).T).T
    z = cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        x, y = cam[:, 0] / z, cam[:, 1] / z
    L = shot.lens
    r2 = x * x + y * y
    radial = 1 + L.k1 * r2 + L.k2 * r2 * r2 + L.k3 * r2 * r2 * r2
    xd = x * radial + 2 * L.p1 * x * y + L.p2 * (r2 + 2 * x * x)
    yd = y * radial + L.p1 * (r2 + 2 * y * y) + 2 * L.p2 * x * y
    s = max(L.width, L.height)
    u = (L.fx * xd + L.cx) * s + L.width / 2.0 - 0.5
    v = (L.fy * yd + L.cy) * s + L.height / 2.0 - 0.5
    return np.stack([u, v], axis=1), z


def densify(ring: np.ndarray, step: float) -> np.ndarray:
    """A polygon's outline (M, 2) with points every `step` metres (lens distortion bends edges)."""
    out = []
    for a, b in zip(ring[:-1], ring[1:]):
        n = max(1, int(math.ceil(float(np.linalg.norm(b - a)) / step)))
        out.extend(a + (b - a) * (i / n) for i in range(n))
    return np.array(out)


@dataclass
class Candidate:
    shot: Shot
    inside: float             # share of the plot's outline inside the frame (1 = all of it)
    off_nadir_deg: float      # angle between the view of the plot's centre and straight down
    center_offset: float      # plot centre's distance from the frame centre / half diagonal (0 = centre)
    bbox: tuple[int, int, int, int]  # the plot's pixel box in the frame (x0, y0, x1, y1)
    gsd_m: float              # ground size of one pixel at the plot (metres)


def rank(shots: list[Shot], outline: np.ndarray, ground_z: float, keep: int = 3,
         margin_px: int = 8) -> list[Candidate]:
    """The frames that show a plot best: the whole plot in frame first, then the most
    top-down view of it. `outline`: the plot's polygon (M, 2) in the shots' CRS."""
    ring = densify(outline, step=max(0.05, float(np.ptp(outline, axis=0).max()) / 40))
    pts = np.column_stack([ring, np.full(len(ring), ground_z)])
    centre = np.array([*outline[:-1].mean(axis=0), ground_z])
    found = []
    for s in shots:
        ray = centre - s.center
        if ray[2] >= 0:
            continue
        uv, depth = project(s, pts)
        if (depth <= 0).any():
            continue
        L = s.lens
        ok = ((uv[:, 0] >= margin_px) & (uv[:, 0] <= L.width - 1 - margin_px)
              & (uv[:, 1] >= margin_px) & (uv[:, 1] <= L.height - 1 - margin_px))
        inside = float(ok.mean())
        if inside == 0:
            continue
        off = math.degrees(math.acos(min(1.0, -ray[2] / float(np.linalg.norm(ray)))))
        c_uv, _ = project(s, centre[None, :])
        half_diag = math.hypot(L.width, L.height) / 2
        offset = float(math.hypot(c_uv[0, 0] - L.width / 2, c_uv[0, 1] - L.height / 2) / half_diag)
        x0, y0 = np.floor(uv.min(axis=0)).astype(int)
        x1, y1 = np.ceil(uv.max(axis=0)).astype(int)
        focal_px = L.fx * max(L.width, L.height)
        gsd = float(np.linalg.norm(ray)) / focal_px
        found.append(Candidate(s, inside, off, offset, (int(x0), int(y0), int(x1), int(y1)), gsd))
    found.sort(key=lambda c: (-round(c.inside, 3), c.off_nadir_deg))
    return found[:keep]


def straighten(image: np.ndarray, shot: Shot, outline: np.ndarray, ground_z: float,
               gsd: float, max_px: int = 4000) -> tuple[np.ndarray, tuple[float, float, float]]:
    """The plot as seen from straight above, from one frame: a north-up grid over the plot's
    box at `gsd` metres per pixel, each cell sampled where it projects in the frame
    (bilinear), outside the plot black. Returns (image, (x_min, y_max, gsd)) — where its
    top-left corner is on the ground, so it can be written as a georeferenced file."""
    x_min, y_min = outline.min(axis=0)
    x_max, y_max = outline.max(axis=0)
    gsd = max(gsd, max(x_max - x_min, y_max - y_min) / max_px)
    w = max(1, int(math.ceil((x_max - x_min) / gsd)))
    h = max(1, int(math.ceil((y_max - y_min) / gsd)))
    gx = x_min + (np.arange(w) + 0.5) * gsd
    gy = y_max - (np.arange(h) + 0.5) * gsd
    X, Y = np.meshgrid(gx, gy)
    pts = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, ground_z)])
    uv, depth = project(shot, pts)
    out = sample_bilinear(image, uv[:, 0], uv[:, 1]).reshape(h, w, -1)
    inside = points_in_polygon(np.column_stack([X.ravel(), Y.ravel()]), outline).reshape(h, w)
    out[~inside | (depth.reshape(h, w) <= 0)] = 0
    return out.astype(image.dtype), (float(x_min), float(y_max), float(gsd))


def sample_bilinear(img: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """img (H, W[, C]) at fractional pixel positions; outside the image -> 0."""
    if img.ndim == 2:
        img = img[:, :, None]
    H, W = img.shape[:2]
    valid = (u >= 0) & (u <= W - 1) & (v >= 0) & (v <= H - 1)
    u = np.clip(u, 0, W - 1)
    v = np.clip(v, 0, H - 1)
    x0 = np.floor(u).astype(int)
    y0 = np.floor(v).astype(int)
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    ax = (u - x0)[:, None]
    ay = (v - y0)[:, None]
    f = img.astype(np.float32)
    top = f[y0, x0] * (1 - ax) + f[y0, x1] * ax
    bot = f[y1, x0] * (1 - ax) + f[y1, x1] * ax
    out = top * (1 - ay) + bot * ay
    out[~valid] = 0
    return out


def points_in_polygon(pts: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """Even-odd rule, vectorised over points; `ring` closed or not."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    r = ring if np.allclose(ring[0], ring[-1]) else np.vstack([ring, ring[:1]])
    for (xa, ya), (xb, yb) in zip(r[:-1], r[1:]):
        crosses = (ya > y) != (yb > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = xa + (y - ya) * (xb - xa) / (yb - ya)
        inside ^= crosses & (x < xi)
    return inside


def ground_from_dsm(dsm_values: np.ndarray, nodata: Optional[float]) -> Optional[float]:
    """The plot's ground height from DSM samples inside it: a low percentile (soil
    between plants rather than canopy), None when there is nothing usable."""
    v = np.asarray(dsm_values, float).ravel()
    v = v[np.isfinite(v)]
    if nodata is not None:
        v = v[v != nodata]
    v = v[v > -1000]
    return float(np.percentile(v, 10)) if v.size else None
