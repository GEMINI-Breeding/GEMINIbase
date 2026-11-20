"""Raw frames placed on the ground with ODM's camera positions: projection,
the rotation's direction, ranking the frames of a plot, straightening one."""
import math

import numpy as np
import pytest

from gemini.workers.geo import frames as F

pytestmark = pytest.mark.unit

# A nadir camera: image x = east, image y = south, looking down.
NADIR = np.array([[1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]])
LENS = F.Lens(width=400, height=300, fx=0.9, fy=0.9, k1=-0.05, k2=0.01, p1=0.001, p2=-0.001)


def rotvec(r: np.ndarray) -> list:
    """Rotation matrix -> axis-angle (what shots.geojson stores)."""
    angle = math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2)))
    if angle < 1e-9:
        return [0.0, 0.0, 0.0]
    if abs(angle - math.pi) < 1e-6:
        # 180°: axis from the symmetric part
        m = (r + np.eye(3)) / 2
        axis = np.sqrt(np.maximum(np.diag(m), 0))
        i = int(np.argmax(axis))
        axis = m[:, i] / math.sqrt(m[i, i])
        return list(axis * angle)
    axis = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]]) / (2 * math.sin(angle))
    return list(axis * angle)


def tilt(deg: float) -> np.ndarray:
    """The nadir camera pitched forward (about image x) by `deg`."""
    a = math.radians(deg)
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    return rx @ NADIR


def shot(name, x, y, z=30.0, rot=NADIR):
    return F.Shot(name, np.array([x, y, z]), rot, LENS)


def ground_texture(x, y):
    """A pattern on the ground (z = 0): a smooth ramp plus stripes, 0-255."""
    return (127 + 60 * np.sin(x * 2.0) + 60 * np.cos(y * 1.3)).clip(0, 255)


def render(s: F.Shot) -> np.ndarray:
    """What the camera sees of the textured ground plane z = 0: each pixel's ray, undistorted
    by fixed-point iteration, meets the ground."""
    L = s.lens
    u, v = np.meshgrid(np.arange(L.width), np.arange(L.height))
    sz = max(L.width, L.height)
    xd = ((u + 0.5 - L.width / 2) / sz - L.cx) / L.fx
    yd = ((v + 0.5 - L.height / 2) / sz - L.cy) / L.fy
    x, y = xd.copy(), yd.copy()
    for _ in range(20):
        r2 = x * x + y * y
        radial = 1 + L.k1 * r2 + L.k2 * r2 * r2 + L.k3 * r2 ** 3
        dx = 2 * L.p1 * x * y + L.p2 * (r2 + 2 * x * x)
        dy = L.p1 * (r2 + 2 * y * y) + 2 * L.p2 * x * y
        x, y = (xd - dx) / radial, (yd - dy) / radial
    rays = np.stack([x, y, np.ones_like(x)], axis=-1) @ s.rotation      # camera -> world: R^T v
    t = -s.center[2] / rays[..., 2]
    gx = s.center[0] + t * rays[..., 0]
    gy = s.center[1] + t * rays[..., 1]
    return ground_texture(gx, gy).astype(np.uint8)


def test_project_round_trip_with_distortion():
    s = shot("a", 0, 0, rot=tilt(10))
    img = render(s)
    pts = np.array([[1.0, 2.0, 0.0], [-3.0, 1.5, 0.0], [2.5, -2.0, 0.0]])
    uv, depth = F.project(s, pts)
    assert (depth > 0).all()
    for (u, v), (x, y, _) in zip(uv, pts):
        assert abs(img[int(round(v)), int(round(u))] - ground_texture(x, y)) < 6


def test_nadir_frame_is_north_up():
    s = shot("a", 0, 0)
    (uv_n, _), (uv_e, _) = F.project(s, np.array([[0, 5.0, 0]])), F.project(s, np.array([[5.0, 0, 0]]))
    assert uv_n[0, 1] < LENS.height / 2      # north is up in the frame
    assert uv_e[0, 0] > LENS.width / 2       # east is right


def test_read_shots_takes_either_rotation_direction():
    lenses = {"cam": LENS}
    for r in (NADIR, NADIR.T, tilt(15), tilt(15).T):
        gj = {"features": [{"properties": {"filename": "a.jpg", "camera": "cam", "translation": [0, 0, 30],
                                           "rotation": rotvec(r)}}]}
        (s,) = F.read_shots(gj, lenses)
        assert (s.rotation.T @ np.array([0, 0, 1.0]))[2] < 0   # looks down either way


def test_read_lenses_brown_and_perspective():
    lenses = F.read_lenses({
        "b": {"projection_type": "brown", "width": 400, "height": 300, "focal_x": 0.8, "focal_y": 0.81,
              "c_x": 0.01, "c_y": -0.02, "k1": -0.1, "k2": 0.02, "p1": 0, "p2": 0, "k3": 0},
        "p": {"projection_type": "perspective", "width": 400, "height": 300, "focal": 0.9, "k1": 0, "k2": 0},
    })
    assert lenses["b"].fy == 0.81 and lenses["p"].fx == lenses["p"].fy == 0.9
    with pytest.raises(ValueError):
        F.read_lenses({"f": {"projection_type": "fisheye", "width": 1, "height": 1, "focal": 1}})


def test_rank_prefers_whole_plot_then_most_top_down():
    plot = np.array([[10, 10], [12, 10], [12, 15], [10, 15], [10, 10]], float)
    shots = [
        shot("over", 11, 12.5),            # straight above: best
        shot("near", 13, 13),              # a little off
        shot("tilted", 11, 0, rot=tilt(-20)),   # sees it at an angle
        shot("edge", 11 + 12, 12.5),       # plot partly out of frame
        shot("away", 100, 100),            # does not see it
    ]
    ranked = F.rank(shots, plot, ground_z=0.0, keep=3)
    names = [c.shot.filename for c in ranked]
    assert names[0] == "over" and names[1] == "near"
    assert "away" not in names
    assert ranked[0].inside == 1.0 and ranked[0].off_nadir_deg < 1
    x0, y0, x1, y1 = ranked[0].bbox
    assert 0 <= x0 < x1 <= LENS.width and 0 <= y0 < y1 <= LENS.height
    assert 0.0 <= ranked[0].center_offset < 0.05


def test_straighten_recovers_the_ground():
    s = shot("a", 1, 2, rot=tilt(8))
    img = render(s)
    plot = np.array([[-1, 0], [3, 0], [3, 4], [-1, 4], [-1, 0]], float)
    out, (x0, y_top, gsd) = F.straighten(img, s, plot, ground_z=0.0, gsd=0.05)
    assert out.shape[:2] == (80, 80) and gsd == pytest.approx(0.05)
    ys, xs = np.mgrid[0:80, 0:80]
    gx = x0 + (xs + 0.5) * gsd
    gy = y_top - (ys + 0.5) * gsd
    err = np.abs(out[..., 0].astype(float) - ground_texture(gx, gy))
    assert np.median(err) < 3 and np.percentile(err, 99) < 15


def test_straighten_blacks_out_beyond_the_plot():
    s = shot("a", 0, 0)
    img = np.full((300, 400, 3), 200, np.uint8)
    tri = np.array([[-2, -2], [2, -2], [-2, 2], [-2, -2]], float)
    out, _ = F.straighten(img, s, tri, ground_z=0.0, gsd=0.1)
    # North-up: the triangle's right angle (south-west) is bottom-left; north-east is outside it.
    assert out[-3, 2].tolist() == [200, 200, 200]
    assert out[2, -3].tolist() == [0, 0, 0]


def test_points_in_polygon_and_ground():
    sq = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    got = F.points_in_polygon(np.array([[0.5, 0.5], [1.5, 0.5], [-0.1, 0.2]]), sq)
    assert got.tolist() == [True, False, False]
    assert F.ground_from_dsm(np.array([[-9999, 10, 11], [12, 30, 31]]), nodata=-9999) == pytest.approx(10.4, abs=0.6)
    assert F.ground_from_dsm(np.array([-9999.0]), nodata=-9999) is None
