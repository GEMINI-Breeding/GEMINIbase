"""Ground plot images from raw frames (gemini.workers.geo.ground_frames)."""
import numpy as np
import pytest

from gemini.workers.geo import ground_frames as G
from gemini.workers.stitch import associate


def _field(h=200, w=2000, seed=1):
    """A textured strip of ground, wider than one frame."""
    rng = np.random.default_rng(seed)
    base = rng.random((h // 4, w // 4)).astype(np.float32)
    big = np.kron(base, np.ones((4, 4), dtype=np.float32))
    return big[:h, :w]


def _frames(step_px, n, fw=320):
    """Frames of a camera moving along the strip by step_px each shot."""
    field = _field()
    out = []
    for i in range(n):
        crop = field[:, i * step_px: i * step_px + fw]
        out.append(crop - crop.mean())
    return out


def test_frame_step_measures_the_shift():
    a, b = _frames(64, 2)
    dx, dy, peak = G.frame_step(a, b)
    assert abs(abs(dx) - 64 / 320) < 0.02
    assert abs(dy) < 0.02
    assert peak > G.MIN_PEAK


def test_tiles_do_not_overlap():
    # A fifth of a frame per shot: every fifth frame starts a new view.
    thumbs = _frames(64, 16)
    steps, bad = G.travel_steps(thumbs)
    assert bad == 0
    assert G.pick_tiles(steps) == [0, 5, 10, 15]


def test_frames_that_cannot_be_registered_each_count_once():
    # Unrelated frames (sparse handheld photos): no overlap is assumed.
    rng = np.random.default_rng(3)
    thumbs = [rng.random((64, 64)).astype(np.float32) - 0.5 for _ in range(4)]
    steps, bad = G.travel_steps(thumbs)
    assert bad == 3
    assert G.pick_tiles(steps) == [0, 1, 2, 3]


def test_stretch_either_way_round():
    frames = ["a", "b", "c", "d", "e"]
    assert G.stretch(frames, "b", "d") == ["b", "c", "d"]
    assert G.stretch(frames, "d", "b") == ["b", "c", "d"]
    assert G.stretch(frames, "b", "x") == []


SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
POLYS = [{"type": "Feature", "geometry": SQUARE, "properties": {"plot": "101", "accession": "SC56"}}]


def _name(sel, order=0, design=None, centre=None, polygons=POLYS):
    return G.name_plot(sel, order, design=design, by_label=associate.by_label(polygons),
                       centre=centre, polygons=polygons, match=associate.match)


def test_named_from_the_drone_boundary_first():
    props, how = _name({"plot_id": 3, "boundary": {"label": "101", "properties": {}}},
                       design=[{"plot": "999"}], centre=(5.0, 5.0))
    assert props["accession"] == "SC56" and how == "drone plot boundary"


def test_named_from_a_field_design_in_marking_order():
    props, how = _name({"plot_id": 2}, order=1, design=[{"plot": "1"}, {"plot": "2", "accession": "X"}])
    assert props == {"plot": "2", "accession": "X"} and how.startswith("field design")


def test_named_by_gps_inside_a_boundary():
    props, how = _name({"plot_id": 7}, centre=(0.5, 0.5))
    assert props["plot"] == "101" and how == "GPS inside a plot boundary"


def test_otherwise_the_marking_number():
    props, how = _name({"plot_id": 7}, centre=(5.0, 5.0))
    assert props == {"plot": "7"} and how == "marking number"
