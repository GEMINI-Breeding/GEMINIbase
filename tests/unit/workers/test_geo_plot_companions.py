"""A flight's thermal frames beside its RGB frames (SPLIT_ORTHOMOSAIC source="frames"):
matched by capture time, lined up by their content, cut per plot, and each plot's
canopy temperature measured over its plants. A synthetic field: green plants on
brown soil, plants at 27 °C on plot 101 and 30 °C on plot 102, soil at 45 °C."""
import io
import json

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("rasterio")

from gemini.workers.geo import companions as C  # noqa: E402
from gemini.workers.geo import frames as F  # noqa: E402
from gemini.workers.geo import plot_frames  # noqa: E402

from .test_geo_frames import LENS, NADIR, rotvec  # noqa: E402
from .test_geo_plot_frames import GROUND, X0, Y0, Store, Worker, _with_xmp, lonlat  # noqa: E402

pytestmark = pytest.mark.unit

SCOPE = "2026/E/Davis/Cowpea/2026-08-17/Drone"
TH_W, TH_H, K, TX, TY = 160, 128, 1.6, 78.0, 43.6     # the thermal camera inside the RGB frame


def plants(x, y):
    """Where plants are on the ground: blobs (about half the ground)."""
    return (np.sin(x * 2.3) * np.cos(y * 1.7) + 0.3 * np.sin(x * 0.7 + y * 0.9)) > 0.0


def rgb_ground(x, y):
    p = plants(x, y)[..., None]
    shade = (10 * np.sin(x * 9) * np.cos(y * 7))[..., None]
    return np.where(p, [55, 140, 45], [135, 112, 92]) + shade


def temp_ground(x, y):
    leaf = np.where(x < 5.0, 27.0, 30.0)
    return np.where(plants(x, y), leaf, 45.0) + 0.2 * np.sin(x * 5)


def render_fn(s: F.Shot, fn) -> np.ndarray:
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
    rays = np.stack([x, y, np.ones_like(x)], axis=-1) @ s.rotation
    t = -s.center[2] / rays[..., 2]
    return fn(s.center[0] + t * rays[..., 0], s.center[1] + t * rays[..., 1])


def build(store: Store, thermal: bool = True):
    cams = {"cam": {"projection_type": "brown", "width": LENS.width, "height": LENS.height, "focal_x": LENS.fx,
                    "focal_y": LENS.fy, "c_x": 0, "c_y": 0, "k1": LENS.k1, "k2": LENS.k2, "p1": LENS.p1,
                    "p2": LENS.p2, "k3": 0}}
    th_lens = C.companion_lens(LENS, TH_W, TH_H, K, TX, TY)
    feats = []
    for i, (dx, dy) in enumerate(((2, 3.5), (7, 3.5), (4.5, 4.0)), start=1):
        name = f"DJI_2026081710000{i}_000{i}_V.JPG"
        c = np.array([X0 + dx, Y0 + dy, GROUND + 25])
        local = c - np.array([X0, Y0, GROUND])
        img = render_fn(F.Shot(name, local, NADIR, LENS), rgb_ground).clip(0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, "JPEG", quality=95)
        store.data[f"Raw/{SCOPE}/RGB/abcd1234/Images/{name}"] = _with_xmp(buf.getvalue())
        if thermal:
            # One second later by its clock, same sequence number.
            tname = f"DJI_2026081710000{i + 1}_000{i}_T.tif"
            t = render_fn(F.Shot(tname, local, NADIR, th_lens), temp_ground).astype(np.float32)
            tb = io.BytesIO()
            Image.fromarray(t).save(tb, "TIFF")
            store.data[f"Raw/{SCOPE}/Thermal/ef015678/Images/{tname}"] = tb.getvalue()
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [*lonlat(*c[:2]), c[2]]},
                      "properties": {"filename": name, "camera": "cam", "translation": c.tolist(),
                                     "rotation": rotvec(NADIR)}})
    if thermal:
        # A frame from another flight that day: matched to nothing.
        tb = io.BytesIO()
        Image.fromarray(np.full((TH_H, TH_W), 40, np.float32)).save(tb, "TIFF")
        store.data[f"Raw/{SCOPE}/Thermal/ef015678/Images/DJI_20260817153000_0001_T.tif"] = tb.getvalue()
    folder = f"Processed/{SCOPE}/RGB"
    store.data[f"{folder}/odm_orthophoto-job1.tif"] = b"ortho"
    store.data[f"{folder}/odm_shots-job1.geojson"] = json.dumps({"type": "FeatureCollection",
                                                                 "features": feats}).encode()
    store.data[f"{folder}/odm_cameras-job1.json"] = json.dumps(cams).encode()
    plots = []
    for n, (ax, ay) in enumerate(((1, 2), (6, 2)), start=101):
        ring = [lonlat(X0 + x, Y0 + y) for x, y in ((ax, ay), (ax + 2, ay), (ax + 2, ay + 3), (ax, ay + 3),
                                                    (ax, ay))]
        plots.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"plot": n, "accession": f"PI {n}", "row": 1, "col": n - 100}})
    return {"year": "2026", "experiment": "E", "location": "Davis", "population": "Cowpea",
            "date": "2026-08-17", "source": "frames", "orthomosaic_path": f"{folder}/odm_orthophoto-job1.tif",
            "boundaries": {"type": "FeatureCollection", "features": plots}}


class HttpWorker(Worker):
    _http = object()


def test_thermal_frames_are_matched_lined_up_and_measured(monkeypatch):
    stored = {}

    def fake_ingest(http, **kw):
        stored.update(kw)
        return {"Temp_veg_avg_C": len(kw["geojson"]["features"])}

    import gemini.workers.ml.trait_ingest as ti
    monkeypatch.setattr(ti, "ingest_trait_features", fake_ingest)

    store = Store()
    out = plot_frames.run(HttpWorker(), "j", build(store), store, "gemini")
    th = out["companions"]["Thermal"]
    assert "error" not in th, th
    assert th["matched"] == 3 and th["values"] == "temperature (°C)"
    a = th["alignment"]
    assert a["k"] == pytest.approx(K, rel=0.03)
    assert abs(a["x0"] - TX) < 4 and abs(a["y0"] - TY) < 4

    prefix = f"Processed/{SCOPE}/RGB/PlotFrames/"
    man = json.loads(store.data[prefix + "manifest.json"])
    assert man["companions"]["Thermal"]["plots_seen"] == 2
    by = {p["plot"]: p["companions"]["Thermal"] for p in man["plots"]}
    assert by[101]["canopy"]["canopy_mean_c"] == pytest.approx(27.0, abs=0.3)
    assert by[102]["canopy"]["canopy_mean_c"] == pytest.approx(30.0, abs=0.3)
    assert by[101]["canopy"]["soil_mean_c"] == pytest.approx(45.0, abs=0.5)
    assert by[101]["cover"] == 1.0
    best = by[101]["frames"][0]
    assert best["image"].endswith("_0001_T.tif") or best["image"].endswith("_T.tif")
    assert abs(best["seconds_from_rgb"]) == 1.0
    crop = np.asarray(Image.open(io.BytesIO(store.data[best["crop"]])))
    assert crop.dtype == np.float32 and 26 < float(np.nanmin(crop)) < 46
    assert store.data[best["crop_preview"]][:2] == b"\xff\xd8"
    flat = np.asarray(Image.open(io.BytesIO(store.data[by[101]["straightened"]])))
    assert np.isfinite(flat).mean() > 0.8
    assert store.data[by[101]["straightened_preview"]][:4] == b"\x89PNG"

    gj = json.loads(store.data[f"{prefix}Thermal/traits.geojson"])
    assert {f["properties"]["plot"] for f in gj["features"]} == {101, 102}
    assert stored["trait_columns"] == (("Temp_veg_avg_C", "°C"),) and stored["source"] == "PLOT_FRAMES"
    rows = store.data[prefix + "manifest.csv"].decode().splitlines()
    assert rows[0].endswith("Thermal_image,Thermal_crop,Thermal_canopy_temp_c")
    table = store.data[f"{prefix}Thermal/plots.csv"].decode().splitlines()
    assert table[0].startswith("plot,accession,canopy_temp_mean_c") and len(table) == 3


def test_no_other_sensor_leaves_the_rgb_job_as_it_was():
    store = Store()
    out = plot_frames.run(Worker(), "j", build(store, thermal=False), store, "gemini")
    assert out["companions"] == {} and out["plots_processed"] == 2
    man = json.loads(store.data[f"Processed/{SCOPE}/RGB/PlotFrames/manifest.json"])
    assert man["companions"] == {} and all("companions" not in p for p in man["plots"])


def test_companions_false_skips_them():
    store = Store()
    params = {**build(store), "companions": False}
    out = plot_frames.run(Worker(), "j", params, store, "gemini")
    assert out["companions"] == {}


def test_frame_names_give_time_and_sequence():
    t, seq = C.frame_key("Raw/x/DJI_20260817100534_0513_T.tif")
    t2, seq2 = C.frame_key("DJI_20260817100535_0513_V.JPG")
    assert seq == seq2 == 513 and t2 - t == 1.0
    assert C.frame_key("IMG_1234.JPG") == (None, None)
    assert C.exif_time(b"xx2026:08:17 10:05:34\x00") == pytest.approx(t)


def test_pairing_prefers_the_same_sequence_number_within_the_window():
    rgb = {"a": (100.0, 12), "b": (101.0, 13), "c": (500.0, 14)}
    th = {"t12": (101.0, 12), "t13": (101.0, 13), "far": (300.0, 99)}
    got = C.pair(rgb, th)
    assert got["a"] == ("t12", 1.0) and got["b"] == ("t13", 0.0)
    assert "c" not in got                       # nothing within 2 s


def test_companion_lens_is_the_scale_and_shift():
    lens = F.Lens(4032, 3024, 0.7, 0.71, 0.002, -0.001, -0.02, 0.004, 0.0, 0.0005, -0.0003)
    th = C.companion_lens(lens, 640, 512, 2.88, 1110.0, 722.0)
    pts = np.array([[1.0, 2.0, 0.0], [-3.0, 1.0, 0.0], [0.5, -2.0, 0.0]])
    a, _ = F.project(F.Shot("a", np.array([0, 0, 30.0]), NADIR, lens), pts)
    b, _ = F.project(F.Shot("a", np.array([0, 0, 30.0]), NADIR, th), pts)
    assert np.allclose((a - [1110.0, 722.0]) / 2.88, b, atol=1e-6)


def test_flight_alignment_drops_pairs_that_disagree():
    A = C.Alignment
    got = C.flight_alignment([A(2.88, 1106, 697, 0.5), A(2.87, 1115, 718, 0.4), A(1.0, 1148, 0, 0.3),
                              A(2.92, 1076, 725, 0.7), A(3.6, 961, 491, 0.75), A(2.83, 1121, 753, 0.68)])
    assert got["pairs_used"] == 4 and got["k"] == pytest.approx(2.875, abs=0.02)
    with pytest.raises(ValueError, match="do not agree"):
        C.flight_alignment([A(1.0, 0, 0, 0.3), A(3.0, 900, 400, 0.3), A(5.0, 10, 10, 0.3)])


def test_refine_finds_one_frames_own_shift_near_the_flights():
    rng = np.random.default_rng(3)
    big = rng.random((90, 120)).astype(np.float32)
    rgb = np.asarray(Image.fromarray(big).resize((1200, 900), Image.BICUBIC), dtype=np.float32)
    k, x0, y0 = 2.5, 310.0, 205.0
    comp = np.asarray(Image.fromarray(rgb[int(y0):int(y0) + 400, int(x0):int(x0) + 500]).resize((200, 160),
                                                                                                 Image.BILINEAR))
    got = C.refine(rgb, comp, {"k": 2.5, "x0": x0 + 25, "y0": y0 - 18})
    assert got is not None and got.score > 0.8
    assert abs(got.x0 - x0) < 2 and abs(got.y0 - y0) < 2 and got.k == pytest.approx(k, rel=0.011)
    # Too far from the flight's alignment: not taken.
    assert C.refine(rgb, comp, {"k": 2.5, "x0": x0 + 300, "y0": y0}, search_px=60) is None or \
        C.refine(rgb, comp, {"k": 2.5, "x0": x0 + 300, "y0": y0}, search_px=60).score < 0.8
