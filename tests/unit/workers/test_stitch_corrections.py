"""GPS corrections applied to stitched plot footprints before association."""
import math

import pytest

from gemini.workers.stitch import corrections as fix

LAT0, LON0 = 33.9674, -117.3385
KX = 111_320 * math.cos(math.radians(LAT0))


def box(east_m, north_m, w=2.0, h=1.0):
    """A plot footprint centred east_m / north_m from the origin."""
    lon = LON0 + east_m / KX
    lat = LAT0 + north_m / 111_320
    dx, dy = w / 2 / KX, h / 2 / 111_320
    return [[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy],
            [lon - dx, lat + dy], [lon - dx, lat - dy]]


def metres(pt):
    return ((pt[0] - LON0) * KX, (pt[1] - LAT0) * 111_320)


def test_no_corrections_keeps_centres():
    _, centres = fix.apply({"1": box(0, 0)}, None)
    assert metres(centres["1"]) == pytest.approx((0, 0), abs=1e-6)


def test_global_and_bed_shifts_add_up():
    fps = {"1": box(0, 0), "2": box(4, 0), "3": box(0, 3)}
    c = {"shift_m": [1, 0], "beds": {"a": {"shift_m": [0, 2]}}, "plot_bed": {"1": "a", "2": "a", "3": "b"}}
    _, centres = fix.apply(fps, c)
    assert metres(centres["1"]) == pytest.approx((1, 2), abs=1e-3)
    assert metres(centres["2"]) == pytest.approx((5, 2), abs=1e-3)
    assert metres(centres["3"]) == pytest.approx((1, 3), abs=1e-3)  # other bed: global only


def test_straighten_puts_a_wobbly_bed_on_one_line():
    fps = {str(i): box(4 * i, 0.4 if i % 2 else -0.4) for i in range(6)}
    c = {"beds": {"a": {"straighten": True}}, "plot_bed": {str(i): "a" for i in range(6)}}
    _, centres = fix.apply(fps, c)
    pts = [metres(centres[str(i)]) for i in range(6)]
    # All on one line: every point's cross product with the end-to-end
    # direction is ~0.
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    for x, y in pts:
        assert abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) == pytest.approx(0, abs=0.05)


def test_rotate_turns_a_bed_about_its_middle():
    fps = {"1": box(-5, 0), "2": box(5, 0)}
    c = {"beds": {"a": {"rotate_deg": 90}}, "plot_bed": {"1": "a", "2": "a"}}
    _, centres = fix.apply(fps, c)
    # Clockwise 90°: west end goes north, east end goes south.
    assert metres(centres["1"]) == pytest.approx((0, 5), abs=1e-3)
    assert metres(centres["2"]) == pytest.approx((0, -5), abs=1e-3)
