"""Plot images from the raw frames (SPLIT_ORTHOMOSAIC with source="frames").

For each plot boundary: the frames of the flight that show it best, by the
camera positions of the ODM run that made the orthomosaic the boundaries were
placed on (frames.py). Written under …/{platform}/{sensor}/PlotFrames/:

  crops/plot_{n}_accession_{a}_frame{rank}_{frame}.jpg  the plot cut from each of its best frames
  straightened/plot_{n}_accession_{a}.png              the best frame warped to a top-down view
  manifest.json, manifest.csv                           each plot's frames (the raw frame's path,
                                                        rank, angle, share in frame, pixel box)

The full frames are not copied: the manifest points at them, and downloads
name them by plot and accession.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import tempfile
from collections import defaultdict
from typing import Any

import numpy as np

from . import frames as F

logger = logging.getLogger(__name__)

IMAGE_EXT = (".jpg", ".jpeg", ".tif", ".tiff", ".png")
CROP_MARGIN = 0.12            # around the plot's box in a frame, as a share of its size
RELATIVE_ALT = re.compile(rb'RelativeAltitude="?\s*([+-]?[0-9.]+)')


def _job_suffix(ortho_path: str) -> tuple[str, str]:
    """(folder, ODM job id) of an orthomosaic written by RUN_ODM."""
    folder, name = ortho_path.rsplit("/", 1)
    m = re.match(r"odm_orthophoto-(.+)\.tiff?$", name)
    if not m:
        raise ValueError(f"{name} was not made by an ODM run here, so it has no camera positions; "
                         "plot images from raw frames need an orthomosaic built in the app")
    return folder, m.group(1)


def _utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def _shot_crs(geojson: dict) -> str:
    """The projected CRS of shots.geojson's translations: the UTM zone ODM used,
    checked against the shots' own longitude/latitude."""
    from rasterio.warp import transform

    feats = [f for f in geojson.get("features", []) if f.get("geometry") and f["properties"].get("translation")]
    if not feats:
        raise ValueError("shots.geojson has no placed frames")
    lon, lat = np.median([f["geometry"]["coordinates"][:2] for f in feats], axis=0)
    epsg = _utm_epsg(float(lon), float(lat))
    f0 = feats[len(feats) // 2]
    x, y = transform("EPSG:4326", f"EPSG:{epsg}", [f0["geometry"]["coordinates"][0]], [f0["geometry"]["coordinates"][1]])
    tx, ty = f0["properties"]["translation"][:2]
    if abs(x[0] - tx) > 5 or abs(y[0] - ty) > 5:
        raise ValueError(f"the camera positions are not in UTM zone EPSG:{epsg} "
                         f"(off by {abs(x[0] - tx):.0f} m, {abs(y[0] - ty):.0f} m)")
    return f"EPSG:{epsg}"


def _safe(v: Any) -> str:
    return str(v).replace("/", "_").replace(" ", "_")


def run(worker, job_id: str, p: dict, client, bucket: str) -> dict:
    """The job: rank, cut, straighten, write the manifest."""
    from PIL import Image
    from rasterio.warp import transform_geom

    year, experiment, location, population, date = (p[k] for k in ("year", "experiment", "location",
                                                                     "population", "date"))
    features = (p.get("boundaries") or {}).get("features") or []
    if not features:
        raise ValueError("No plot boundaries provided")
    orthos = list(p.get("orthomosaic_paths") or ([p["orthomosaic_path"]] if p.get("orthomosaic_path") else []))
    if not orthos:
        raise ValueError("name the orthomosaic(s) the boundaries were placed on (orthomosaic_path)")
    keep = max(1, min(int(p.get("frames_per_plot", 3)), 10))

    worker.report_progress(job_id, 3, {"stage": "reading_camera_positions"})
    shots: list[F.Shot] = []
    crs = None
    dsms: list[str] = []
    for ortho in orthos:
        folder, odm_job = _job_suffix(ortho)
        try:
            gj = json.loads(client.get_object(bucket, f"{folder}/odm_shots-{odm_job}.geojson").read())
            cams = json.loads(client.get_object(bucket, f"{folder}/odm_cameras-{odm_job}.json").read())
        except Exception:
            raise ValueError(f"the ODM run of {ortho.rsplit('/', 1)[-1]} did not keep its camera positions "
                             "(runs before this feature): build the orthomosaic again, e.g. with the Quick "
                             "preset, then place the boundaries on it") from None
        here = _shot_crs(gj)
        if crs and here != crs:
            raise ValueError("the orthomosaics' camera positions are in different UTM zones")
        crs = here
        shots += F.read_shots(gj, F.read_lenses(cams))
        dsms.append(f"{folder}/odm_dsm-{odm_job}.tif")
    if not shots:
        raise ValueError("no placed frames in the ODM run's camera positions")

    parts = orthos[0].split("/")
    platform, sensor = parts[6], parts[7]
    raw_prefix = f"Raw/{year}/{experiment}/{location}/{population}/{date}/{platform}/{sensor}/"
    out_prefix = f"Processed/{year}/{experiment}/{location}/{population}/{date}/{platform}/{sensor}/PlotFrames/"

    worker.report_progress(job_id, 6, {"stage": "finding_raw_frames"})
    raw: dict[str, str] = {}
    for obj in client.list_objects(bucket, prefix=raw_prefix, recursive=True):
        name = obj.object_name.rsplit("/", 1)[-1]
        if name.lower().endswith(IMAGE_EXT) and "/Orthomosaic" not in obj.object_name:
            raw.setdefault(name, obj.object_name)
    shots = [s for s in shots if s.filename in raw]
    if not shots:
        raise ValueError(f"none of the ODM run's frames are under {raw_prefix}")

    with tempfile.TemporaryDirectory() as tmp:
        # Plots in the shots' CRS, and their ground height.
        plots = []
        for i, feat in enumerate(features):
            props = feat.get("properties") or {}
            if props.get("role") == "outer" or (feat.get("geometry") or {}).get("type") != "Polygon":
                continue
            geom = transform_geom("EPSG:4326", crs, feat["geometry"])
            ring = np.array(geom["coordinates"][0], float)[:, :2]
            plots.append({"plot": props.get("plot", props.get("Plot", i + 1)),
                          "accession": props.get("accession", props.get("Accession",
                                                 props.get("Label", props.get("label", "unknown")))),
                          "ring": ring, "geom": geom})
        ground = _ground_heights(client, bucket, dsms, plots, crs, shots, raw, tmp)

        worker.report_progress(job_id, 12, {"stage": "ranking", "plots_total": len(plots)})
        need: dict[str, list[tuple[dict, int, F.Candidate]]] = defaultdict(list)
        for k, pl in enumerate(plots):
            pl["candidates"] = F.rank(shots, pl["ring"], pl["ground"], keep=keep)
            for r, c in enumerate(pl["candidates"], 1):
                need[c.shot.filename].append((pl, r, c))
            if k % 50 == 0 and worker.is_cancelled(job_id):
                return {"status": "cancelled"}

        # Each frame once, every crop and straightened view that comes from it.
        done = 0
        for n, (fname, uses) in enumerate(need.items()):
            if worker.is_cancelled(job_id):
                return {"status": "cancelled"}
            local = os.path.join(tmp, "frame" + os.path.splitext(fname)[1])
            client.fget_object(bucket, raw[fname], local)
            with Image.open(local) as im:
                img = np.asarray(im.convert("RGB"))
            for pl, r, c in uses:
                base = f"plot_{pl['plot']}_accession_{_safe(pl['accession'])}"
                x0, y0, x1, y1 = c.bbox
                mx, my = int((x1 - x0) * CROP_MARGIN), int((y1 - y0) * CROP_MARGIN)
                box = (max(0, x0 - mx), max(0, y0 - my), min(img.shape[1], x1 + mx), min(img.shape[0], y1 + my))
                crop_name = f"{out_prefix}crops/{base}_frame{r}_{os.path.splitext(fname)[0]}.jpg"
                _put_image(client, bucket, crop_name, img[box[1]:box[3], box[0]:box[2]], "JPEG")
                frame = {"rank": r, "image": raw[fname], "crop": crop_name, "inside": round(c.inside, 3),
                         "off_nadir_deg": round(c.off_nadir_deg, 2), "center_offset": round(c.center_offset, 3),
                         "bbox": list(c.bbox), "gsd_cm": round(c.gsd_m * 100, 2)}
                pl.setdefault("frames", []).append(frame)
                if r == 1:
                    flat, (gx, gy, gsd) = F.straighten(img, c.shot, pl["ring"], pl["ground"], c.gsd_m)
                    pl["straightened"] = f"{out_prefix}straightened/{base}.png"
                    pl["straightened_origin"] = {"crs": crs, "x_min": gx, "y_max": gy, "gsd_m": gsd}
                    _put_image(client, bucket, pl["straightened"], flat, "PNG")
            os.remove(local)
            done += len(uses)
            worker.report_progress(job_id, 15 + int(80 * (n + 1) / max(1, len(need))),
                                   {"stage": "cutting", "frames_done": n + 1, "frames_total": len(need)})

        manifest = {
            "orthomosaics": orthos, "crs": crs, "frames_per_plot": keep,
            "ground": sorted({pl["ground_from"] for pl in plots}),
            "plots": [{"plot": pl["plot"], "accession": pl["accession"], "ground_z": round(pl["ground"], 2),
                       "straightened": pl.get("straightened"), "straightened_origin": pl.get("straightened_origin"),
                       "frames": sorted(pl.get("frames", []), key=lambda f: f["rank"])} for pl in plots],
        }
        _put_bytes(client, bucket, f"{out_prefix}manifest.json", json.dumps(manifest, indent=1).encode(),
                   "application/json")
        rows = io.StringIO()
        w = csv.writer(rows)
        w.writerow(["plot", "accession", "rank", "raw_image", "crop", "straightened", "inside", "off_nadir_deg",
                    "center_offset", "gsd_cm"])
        for pl in manifest["plots"]:
            for f in pl["frames"] or [{}]:
                w.writerow([pl["plot"], pl["accession"], f.get("rank", ""), f.get("image", ""), f.get("crop", ""),
                            pl["straightened"] if f.get("rank") == 1 else "", f.get("inside", ""),
                            f.get("off_nadir_deg", ""), f.get("center_offset", ""), f.get("gsd_cm", "")])
        _put_bytes(client, bucket, f"{out_prefix}manifest.csv", rows.getvalue().encode(), "text/csv")

    unseen = [str(pl["plot"]) for pl in plots if not pl.get("frames")]
    worker.report_progress(job_id, 100, {"stage": "complete"})
    return {"plots_processed": len(plots) - len(unseen), "plots_unseen": unseen[:50],
            "frames_used": len(need), "output_prefix": out_prefix, "source": "frames"}


def _ground_heights(client, bucket, dsms, plots, crs, shots, raw, tmp) -> None:
    """Each plot's ground height: the DSM of the run (soil between plants), else the
    drone's height above takeoff from a few frames (all plots at the takeoff level)."""
    import rasterio
    from rasterio.mask import mask as rio_mask
    from rasterio.warp import transform_geom

    for dsm in dsms:
        local = os.path.join(tmp, "dsm.tif")
        try:
            client.fget_object(bucket, dsm, local)
        except Exception:
            continue
        with rasterio.open(local) as src:
            for pl in plots:
                if "ground" in pl:
                    continue
                try:
                    g = transform_geom(crs, src.crs, pl["geom"])
                    vals, _ = rio_mask(src, [g], crop=True, filled=False)
                    z = F.ground_from_dsm(vals.compressed(), src.nodata)
                except Exception:
                    z = None
                if z is not None:
                    pl["ground"], pl["ground_from"] = z, "dsm"
        os.remove(local)
    missing = [pl for pl in plots if "ground" not in pl]
    if not missing:
        return
    heights = []
    for s in shots[:: max(1, len(shots) // 8)][:8]:
        try:
            head = client.get_object(bucket, raw[s.filename], offset=0, length=131072).read()
        except Exception:
            continue
        m = RELATIVE_ALT.search(head)
        if m:
            heights.append(float(s.center[2]) - float(m.group(1)))
    if not heights:
        raise ValueError("no ground height for some plots: the ODM run kept no surface model, and the frames "
                         "do not record their height above takeoff")
    z = float(np.median(heights))
    for pl in missing:
        pl["ground"], pl["ground_from"] = z, "takeoff height"


def _put_image(client, bucket, name, arr, fmt) -> None:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(arr)).save(buf, fmt, **({"quality": 92} if fmt == "JPEG" else {}))
    _put_bytes(client, bucket, name, buf.getvalue(), "image/jpeg" if fmt == "JPEG" else "image/png")


def _put_bytes(client, bucket, name, data: bytes, ctype: str) -> None:
    client.put_object(bucket, name, io.BytesIO(data), len(data), content_type=ctype)
