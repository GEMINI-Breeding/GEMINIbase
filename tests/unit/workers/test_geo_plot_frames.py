"""SPLIT_ORTHOMOSAIC source="frames" end to end, against an in-memory store:
a synthetic flight (frames rendered from a known ground), ODM's camera files
in UTM, boundaries in WGS84."""
import io
import json

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("rasterio")
from rasterio.warp import transform  # noqa: E402

from gemini.workers.geo import frames as F  # noqa: E402
from gemini.workers.geo import plot_frames  # noqa: E402

from .test_geo_frames import LENS, NADIR, ground_texture, render, rotvec  # noqa: E402

pytestmark = pytest.mark.unit

EPSG = "EPSG:32610"            # Davis
X0, Y0 = 609000.0, 4265000.0   # a field corner in UTM 10N
GROUND = 15.0                  # ground height (m)
SCOPE = "2026/E/Davis/Sorghum/2026-08-17/Drone/RGB"


class Obj:
    def __init__(self, name):
        self.object_name = name


class Store:
    def __init__(self):
        self.data = {}

    def list_objects(self, bucket, prefix="", recursive=True):
        return [Obj(k) for k in sorted(self.data) if k.startswith(prefix)]

    def get_object(self, bucket, name, offset=0, length=None):
        if name not in self.data:
            raise KeyError(name)
        d = self.data[name][offset:]
        return io.BytesIO(d[:length] if length else d)

    def fget_object(self, bucket, name, path):
        if name not in self.data:
            raise KeyError(name)
        open(path, "wb").write(self.data[name])

    def put_object(self, bucket, name, stream, length, content_type=None):
        self.data[name] = stream.read()


class Worker:
    def __init__(self):
        self.progress = []

    def report_progress(self, job_id, pct, info):
        self.progress.append(pct)

    def is_cancelled(self, job_id):
        return False


def lonlat(x, y):
    lo, la = transform(EPSG, "EPSG:4326", [x], [y])
    return lo[0], la[0]


def build(store: Store):
    """Three frames over two plots; frames record their height above takeoff (no DSM)."""
    cams = {"cam": {"projection_type": "brown", "width": LENS.width, "height": LENS.height, "focal_x": LENS.fx,
                    "focal_y": LENS.fy, "c_x": 0, "c_y": 0, "k1": LENS.k1, "k2": LENS.k2, "p1": LENS.p1,
                    "p2": LENS.p2, "k3": 0}}
    feats = []
    for name, dx, dy in (("DJI_0001.JPG", 2, 3), ("DJI_0002.JPG", 7, 3), ("DJI_0003.JPG", 4.5, 9)):
        c = np.array([X0 + dx, Y0 + dy, GROUND + 25])
        shot = F.Shot(name, c - np.array([X0, Y0, GROUND]), NADIR, LENS)   # render in a local frame
        img = render(shot)
        buf = io.BytesIO()
        Image.fromarray(np.stack([img] * 3, -1)).save(buf, "JPEG", quality=95)
        store.data[f"Raw/{SCOPE}/abcd1234/Images/{name}"] = _with_xmp(buf.getvalue())
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [*lonlat(*c[:2]), c[2]]},
                      "properties": {"filename": name, "camera": "cam", "translation": c.tolist(),
                                     "rotation": rotvec(NADIR)}})
    folder = f"Processed/{SCOPE}"
    store.data[f"{folder}/odm_orthophoto-job1.tif"] = b"ortho"
    store.data[f"{folder}/odm_shots-job1.geojson"] = json.dumps({"type": "FeatureCollection",
                                                                 "features": feats}).encode()
    store.data[f"{folder}/odm_cameras-job1.json"] = json.dumps(cams).encode()
    plots = []
    for n, (ax, ay) in enumerate(((1, 2), (6, 2)), start=101):
        ring = [lonlat(X0 + x, Y0 + y) for x, y in ((ax, ay), (ax + 2, ay), (ax + 2, ay + 3), (ax, ay + 3),
                                                    (ax, ay))]
        plots.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"plot": n, "accession": f"PI {n}"}})
    plots.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[lonlat(X0, Y0)] * 4]},
                  "properties": {"role": "outer"}})
    return {"year": "2026", "experiment": "E", "location": "Davis", "population": "Sorghum",
            "date": "2026-08-17", "source": "frames", "orthomosaic_path": f"{folder}/odm_orthophoto-job1.tif",
            "boundaries": {"type": "FeatureCollection", "features": plots}}


def _with_xmp(jpeg: bytes) -> bytes:
    """A DJI-like XMP packet in an APP1 segment after SOI."""
    xmp = b'http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta drone-dji:RelativeAltitude="+25.00"/>'
    seg = b"\xff\xe1" + (len(xmp) + 2).to_bytes(2, "big") + xmp
    return jpeg[:2] + seg + jpeg[2:]


def test_frames_job_end_to_end():
    store = Store()
    params = build(store)
    out = plot_frames.run(Worker(), "j", params, store, "gemini")
    assert out["plots_processed"] == 2 and out["plots_unseen"] == []
    prefix = f"Processed/{SCOPE}/PlotFrames/"
    man = json.loads(store.data[prefix + "manifest.json"])
    assert man["ground"] == ["takeoff height"] and man["crs"] == "EPSG:32610"
    by = {p["plot"]: p for p in man["plots"]}
    # Plot 101 is under DJI_0001, plot 106's twin (102) under DJI_0002.
    assert by[101]["frames"][0]["image"].endswith("DJI_0001.JPG")
    assert by[102]["frames"][0]["image"].endswith("DJI_0002.JPG")
    assert by[101]["ground_z"] == pytest.approx(GROUND, abs=0.01)
    for p in man["plots"]:
        assert [f["rank"] for f in p["frames"]] == list(range(1, len(p["frames"]) + 1))
        assert p["frames"][0]["inside"] == 1.0
        crop = store.data[p["frames"][0]["crop"]]
        assert Image.open(io.BytesIO(crop)).size[0] > 10
        assert "accession_PI_" in p["frames"][0]["crop"]
    # The straightened view matches the ground it shows.
    p = by[101]
    flat = np.asarray(Image.open(io.BytesIO(store.data[p["straightened"]])))[..., 0].astype(float)
    o = p["straightened_origin"]
    h, w = flat.shape
    ys, xs = np.mgrid[0:h, 0:w]
    gx = o["x_min"] + (xs + 0.5) * o["gsd_m"] - X0
    gy = o["y_max"] - (ys + 0.5) * o["gsd_m"] - Y0
    inside = flat > 0
    assert inside.mean() > 0.8
    err = np.abs(flat - ground_texture(gx, gy))[inside]
    assert np.median(err) < 6
    csv_text = store.data[prefix + "manifest.csv"].decode()
    assert csv_text.splitlines()[0].startswith("plot,accession,rank,raw_image")


def test_frames_job_needs_camera_positions():
    store = Store()
    params = build(store)
    del store.data[f"Processed/{SCOPE}/odm_shots-job1.geojson"]
    with pytest.raises(ValueError, match="did not keep its camera positions"):
        plot_frames.run(Worker(), "j", params, store, "gemini")
    params["orthomosaic_path"] = f"Raw/{SCOPE}/Orthomosaic/x.tif"
    with pytest.raises(ValueError, match="no camera positions"):
        plot_frames.run(Worker(), "j", params, store, "gemini")
