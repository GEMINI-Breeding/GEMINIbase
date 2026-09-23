"""
Match stitched ground plots to plot-boundary polygons (main's
run_associate_boundaries): a stitched plot belongs to the polygon that
contains the centre of its georeferenced mosaic.

Pure geometry, no raster dependencies, so it can be unit-tested; the
worker supplies the centres.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]  # (lon, lat)


def _in_ring(pt: Point, ring: Sequence[Sequence[float]]) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def contains(geometry: dict, pt: Point) -> bool:
    """Point in (Multi)Polygon, holes respected."""
    kind = geometry.get("type")
    polys = (
        [geometry.get("coordinates") or []] if kind == "Polygon"
        else geometry.get("coordinates") or [] if kind == "MultiPolygon"
        else []
    )
    for rings in polys:
        if rings and _in_ring(pt, rings[0]) and not any(_in_ring(pt, h) for h in rings[1:]):
            return True
    return False


def plot_polygons(boundaries: dict) -> List[dict]:
    """The plot features of a boundary FeatureCollection (not block outlines)."""
    return [
        f for f in (boundaries or {}).get("features") or []
        if f.get("geometry") and (f.get("properties") or {}).get("role") != "outer"
    ]


def match(centres: Dict[str, Point], features: List[dict]) -> Dict[str, Optional[dict]]:
    """{stitched plot id: properties of the polygon containing it, or None}."""
    out: Dict[str, Optional[dict]] = {}
    for pid, pt in centres.items():
        hit = next((f for f in features if contains(f["geometry"], pt)), None)
        out[pid] = dict(hit.get("properties") or {}) if hit else None
    return out


def plot_label(props: dict, fallback: str) -> str:
    """The plot's number/label, as the aerial split names plot images."""
    for k in ("plot", "Plot", "plot_number", "plot_id"):
        v = props.get(k)
        if v not in (None, ""):
            return str(v)
    return fallback


def accession_of(props: dict) -> str:
    for k in ("accession", "Accession", "Label", "label"):
        v = props.get(k)
        if v not in (None, ""):
            return str(v)
    return "unknown"


def plot_image_name(props: dict, fallback: str) -> str:
    """plot_{n}_accession_{a}.png — the aerial split's naming, so Analyze and
    inference find ground plot images the same way."""
    safe = lambda s: re.sub(r"[/\s]+", "_", s)  # noqa: E731
    return f"plot_{safe(plot_label(props, fallback))}_accession_{safe(accession_of(props))}.png"
