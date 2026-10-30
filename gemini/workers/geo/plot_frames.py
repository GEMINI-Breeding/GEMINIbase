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

Other sensors uploaded for the same date and platform (a thermal camera beside
the RGB one) are matched to these frames by capture time and cut the same way,
under PlotFrames/{Sensor}/ (plot_companions.py); a thermal camera's frames also
give each plot's canopy temperature.
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
from typing import Any, Optional

import numpy as np

from . import frames as F
from . import plot_companions as PC

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
    without: list[str] = []
    for ortho in orthos:
        folder, odm_job = _job_suffix(ortho)
        try:
            gj = json.loads(client.get_object(bucket, f"{folder}/odm_shots-{odm_job}.geojson").read())
            cams = json.loads(client.get_object(bucket, f"{folder}/odm_cameras-{odm_job}.json").read())
        except Exception:
            # An older orthomosaic of the same flight (built before camera positions were kept):
            # the others give the frames; only when none has them is that an error.
            without.append(ortho.rsplit("/", 1)[-1])
            continue
        here = _shot_crs(gj)
        if crs and here != crs:
            raise ValueError("the orthomosaics' camera positions are in different UTM zones")
        crs = here
        shots += F.read_shots(gj, F.read_lenses(cams))
        dsms.append(f"{folder}/odm_dsm-{odm_job}.tif")
    if not shots and without:
        raise ValueError(f"the ODM run of {without[0]} did not keep its camera positions "
                         "(runs before this feature): build the orthomosaic again, e.g. with the Quick "
                         "preset, then place the boundaries on it")
    if not shots:
        raise ValueError("no placed frames in the ODM run's camera positions")

    parts = orthos[0].split("/")
    platform, sensor = parts[6], parts[7]
    raw_prefix = f"Raw/{year}/{experiment}/{location}/{population}/{date}/{platform}/{sensor}/"
    out_prefix = f"Processed/{year}/{experiment}/{location}/{population}/{date}/{platform}/{sensor}/PlotFrames/"
    # One of several flights that day (a diurnal run, a treatment flown on its own): its own folder,
    # so the day's runs do not overwrite each other's plot images.
    run_key = re.sub(r"[^A-Za-z0-9]+", "-", str(p.get("run_key") or "")).strip("-")
    if run_key:
        out_prefix += f"{run_key}/"

    worker.report_progress(job_id, 6, {"stage": "finding_raw_frames"})
    raw: dict[str, str] = {}
    for obj in client.list_objects(bucket, prefix=raw_prefix, recursive=True):
        name = obj.object_name.rsplit("/", 1)[-1]
        if name.lower().endswith(IMAGE_EXT) and "/Orthomosaic" not in obj.object_name:
            raw.setdefault(name, obj.object_name)
    shots = [s for s in shots if s.filename in raw]
    if not shots:
        raise ValueError(f"none of the ODM run's frames are under {raw_prefix}")
    # The flight's other cameras (thermal beside RGB): every other sensor uploaded for this
    # date and platform, unless `companions` names some (or is [] / false for none).
    wanted = p.get("companions")
    others = {} if wanted is False or wanted == [] else PC.sensors_beside(
        client, bucket, raw_prefix[: -len(sensor) - 1], sensor, wanted if isinstance(wanted, list) else None)
    span = 45 if others else 80

    with tempfile.TemporaryDirectory() as tmp:
        # Plots in the shots' CRS, and their ground height.
        plots = []
        for i, feat in enumerate(features):
            props = feat.get("properties") or {}
            if props.get("role") == "outer" or (feat.get("geometry") or {}).get("type") != "Polygon":
                continue
            geom = transform_geom("EPSG:4326", crs, feat["geometry"])
            ring = np.array(geom["coordinates"][0], float)[:, :2]
            plots.append({"feature": feat, "plot": props.get("plot", props.get("Plot", i + 1)),
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
                    if others:
                        # Where the plants are, for the other cameras' canopy temperature (1 byte a cell).
                        pl["_plant"] = PC.plant_mask(flat)
                    _put_image(client, bucket, pl["straightened"], flat, "PNG")
            os.remove(local)
            done += len(uses)
            worker.report_progress(job_id, 15 + int(span * (n + 1) / max(1, len(need))),
                                   {"stage": "cutting", "frames_done": n + 1, "frames_total": len(need)})

        loaded: dict[str, np.ndarray] = {}

        def rgb_frame(fname: str) -> np.ndarray:
            if fname not in loaded:
                loaded.clear()                   # one at a time: a frame is ~36 MB as an array
                local = os.path.join(tmp, "rgb" + os.path.splitext(fname)[1])
                client.fget_object(bucket, raw[fname], local)
                with Image.open(local) as im:
                    loaded[fname] = np.asarray(im.convert("RGB"))
                os.remove(local)
            return loaded[fname]

        sections = PC.run(worker, job_id, client, bucket, others=others, shots=shots, raw=raw, plots=plots,
                          out_prefix=out_prefix, keep=keep, tmp=tmp, safe=_safe, rgb_loader=rgb_frame,
                          run_label=str(p.get("run_label") or "").strip(), merge=bool(p.get("merge")),
                          progress=lambda f, info: worker.report_progress(
                              job_id, 15 + span + int((95 - 15 - span) * f), {"stage": "other_sensors", **info}))
        if worker.is_cancelled(job_id):
            return {"status": "cancelled"}

        manifest = {
            "orthomosaics": orthos, "crs": crs, "frames_per_plot": keep, "sensor": sensor,
            "run_key": run_key or None, "run_label": p.get("run_label") or None,
            "flown_at": _flown_at(shots),
            "companions": sections,
            "ground": sorted({pl["ground_from"] for pl in plots}),
            "plots": [{"plot": pl["plot"], "accession": pl["accession"], "ground_z": round(pl["ground"], 2),
                       "straightened": pl.get("straightened"), "straightened_origin": pl.get("straightened_origin"),
                       "frames": sorted(pl.get("frames", []), key=lambda f: f["rank"]),
                       **({"companions": pl["companions"]} if pl.get("companions") else {})} for pl in plots],
        }
        if p.get("merge"):
            # Some plots only (added ones, or those without images yet): the plots of the earlier
            # run that this one did not redo stay in the manifest (and so in the tables below).
            try:
                old = json.loads(client.get_object(bucket, f"{out_prefix}manifest.json").read())
            except Exception:
                old = {}
            before = len(manifest["plots"])
            manifest["plots"] = merge_by_plot(old.get("plots") or [], manifest["plots"], lambda pl: pl.get("plot"))
            manifest["merged"] = {"kept": len(manifest["plots"]) - before, "redone": before}
        _put_bytes(client, bucket, f"{out_prefix}manifest.json", json.dumps(manifest, indent=1).encode(),
                   "application/json")
        rows = io.StringIO()
        w = csv.writer(rows)
        # Each other sensor: its frame at the same rank, and (best frame) the plot's canopy temperature.
        extra = [s for s, sec in sections.items() if sec.get("plots_seen")]
        w.writerow(["plot", "accession", "rank", "raw_image", "crop", "straightened", "inside", "off_nadir_deg",
                    "center_offset", "gsd_cm"]
                   + [c for s in extra for c in (f"{s}_image", f"{s}_crop", f"{s}_canopy_temp_c")])
        for pl in manifest["plots"]:
            for f in pl["frames"] or [{}]:
                more = []
                for s in extra:
                    e = (pl.get("companions") or {}).get(s) or {}
                    cf = next((x for x in e.get("frames", []) if x["rank"] == f.get("rank")), {})
                    more += [cf.get("image", ""), cf.get("crop", cf.get("crop_preview", "")),
                             (e.get("canopy") or {}).get("canopy_mean_c", "") if f.get("rank") == 1 else ""]
                w.writerow([pl["plot"], pl["accession"], f.get("rank", ""), f.get("image", ""), f.get("crop", ""),
                            pl["straightened"] if f.get("rank") == 1 else "", f.get("inside", ""),
                            f.get("off_nadir_deg", ""), f.get("center_offset", ""), f.get("gsd_cm", "")] + more)
        _put_bytes(client, bucket, f"{out_prefix}manifest.csv", rows.getvalue().encode(), "text/csv")
        for s in extra:
            # One row per plot: what the trait holds, and how it was measured.
            t = io.StringIO()
            tw = csv.writer(t)
            tw.writerow(["plot", "accession", "canopy_temp_mean_c", "canopy_temp_median_c", "canopy_temp_iqr_c",
                         "soil_temp_mean_c", "plant_share", "plant_cells_used", "cover", "frames_pieced",
                         "best_frame", "straightened"])
            for pl in manifest["plots"]:
                e = (pl.get("companions") or {}).get(s) or {}
                ct = e.get("canopy") or {}
                tw.writerow([pl["plot"], pl["accession"], ct.get("canopy_mean_c", ""), ct.get("canopy_median_c", ""),
                             ct.get("canopy_iqr_c", ""), ct.get("soil_mean_c", ""), ct.get("plant_share", ""),
                             ct.get("plant_cells", ""), e.get("cover", ""), e.get("frames_pieced", ""),
                             (e.get("frames") or [{}])[0].get("image", ""), e.get("straightened", "")])
            _put_bytes(client, bucket, f"{sections[s]['prefix']}plots.csv", t.getvalue().encode(), "text/csv")

    unseen = [str(pl["plot"]) for pl in plots if not pl.get("frames")]
    worker.report_progress(job_id, 100, {"stage": "complete"})
    return {"plots_processed": len(plots) - len(unseen), "plots_unseen": unseen[:50],
            "frames_used": len(need), "output_prefix": out_prefix, "source": "frames",
            "companions": {s: {k: v for k, v in sec.items() if k in ("frames", "matched", "plots_seen", "values",
                                                                    "canopy_temperature_plots", "error",
                                                                    "trait_error", "alignment")}
                           for s, sec in sections.items()}}


def merge_by_plot(old: list, new: list, plot_of) -> list:
    """A run of some plots only: the earlier entries of the plots it did not redo, then its own
    (a plot redone replaces its earlier entry). Plots compared as text ("12" = 12)."""
    done = {str(plot_of(x)) for x in new}
    return [x for x in old if str(plot_of(x)) not in done] + list(new)


def _flown_at(shots) -> Optional[str]:
    """When the flight was, from its frames' names (the median capture time), as ISO time."""
    from datetime import datetime

    from .companions import frame_key

    times = sorted(t for t, _ in (frame_key(s.filename) for s in shots) if t is not None)
    return datetime.fromtimestamp(times[len(times) // 2]).isoformat(timespec="seconds") if times else None


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
