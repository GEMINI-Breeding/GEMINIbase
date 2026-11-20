"""Plot images from a flight's other camera (SPLIT_ORTHOMOSAIC source="frames").

After the RGB frames are cut (plot_frames.py), each other sensor uploaded for
the same date and platform (a drone's thermal camera, say) is matched to the
RGB frames by capture time, lined up with them (companions.py), and cut the
same way:

  {Sensor}/crops/plot_{n}_accession_{a}_frame{rank}_{frame}.tif   the plot in each of its best
                                                                  frames, the sensor's values
                                                                  (°C for a thermal camera)
  {Sensor}/crops/….jpg                                            the same, coloured, to look at
  {Sensor}/straightened/plot_{n}_accession_{a}.tif / .png         top-down view of the best frame
  {Sensor}/traits.geojson                                         per plot: canopy temperature

The frames are ranked again for this camera: a thermal camera sees a smaller
part of the ground than the wide camera beside it, so the RGB frame that shows
a plot best may show it only in part here.

A plot's view is pieced together from several frames (the best first, the
others filling what it missed): a thermal camera sees much less ground than the
wide camera beside it, often not a whole plot. Each filling frame is levelled to
the better ones where both saw the plot (uncooled thermal cameras drift a
little between frames).

Canopy temperature (thermal frames that hold °C): the mean over the thermal
pixels that are (nearly) all plant, each pixel's plant share taken from the RGB
view of the same ground at its full resolution (excess green); a pixel that is
part soil reads warmer and is left out.
Stored as the trait Temp_veg_avg_C, as EXTRACT_TRAITS does from a thermal
orthomosaic.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Optional

import numpy as np

from . import companions as C
from . import frames as F

logger = logging.getLogger(__name__)

IMAGE_EXT = (".jpg", ".jpeg", ".tif", ".tiff", ".png")
PAIRS_TO_LINE_UP = 10        # frame pairs the flight's alignment is measured on
COMPOSITE_FRAMES = 6         # frames a plot's view is pieced together from (this camera sees less ground)
MAX_LEVEL_C = 3.0            # a filling frame further off than this (°C) is left out, not levelled
CROP_MARGIN = 0.12
TRAIT = ("Temp_veg_avg_C", "°C")


def sensors_beside(client, bucket: str, platform_prefix: str, sensor: str,
                   wanted: Optional[list[str]] = None) -> dict[str, dict[str, str]]:
    """Other sensors' frames for the same date and platform: {sensor: {frame name: object}}.
    Of two files of one frame (the thermal worker's coloured preview .jpg beside the
    radiometric .tif), the .tif."""
    found: dict[str, dict[str, str]] = defaultdict(dict)
    for obj in client.list_objects(bucket, prefix=platform_prefix, recursive=True):
        rest = obj.object_name[len(platform_prefix):]
        other = rest.split("/", 1)[0]
        name = rest.rsplit("/", 1)[-1]
        if (other == sensor or "/" not in rest or not name.lower().endswith(IMAGE_EXT)
                or "/Orthomosaic" in rest or "/RawThermal/" in rest):
            continue
        if wanted is not None and other.lower() not in {w.lower() for w in wanted}:
            continue
        stem = os.path.splitext(name)[0]
        have = found[other].get(stem)
        if have is None or name.lower().endswith((".tif", ".tiff")):
            found[other][stem] = obj.object_name
    return {s: {v.rsplit("/", 1)[-1]: v for v in files.values()} for s, files in found.items() if files}


def _keys(client, bucket: str, names: dict[str, str]) -> dict[str, tuple[Optional[float], Optional[int]]]:
    """Capture time and sequence number of each frame: from its name, else its EXIF."""
    out = {}
    for name, obj in names.items():
        t, seq = C.frame_key(name)
        if t is None:
            try:
                t = C.exif_time(client.get_object(bucket, obj, offset=0, length=65536).read())
            except Exception:
                t = None
        out[name] = (t, seq)
    return out


def _load(client, bucket: str, obj: str, tmp: str) -> np.ndarray:
    """A frame as an array: float values for a single-band image (°C from a converted
    thermal frame), (H, W, 3) uint8 for a colour one."""
    from PIL import Image

    local = os.path.join(tmp, "companion" + os.path.splitext(obj)[1])
    client.fget_object(bucket, obj, local)
    try:
        with Image.open(local) as im:
            if im.mode in ("F", "I", "I;16", "I;16B", "I;16L", "L"):
                return np.asarray(im, dtype=np.float32)
            return np.asarray(im.convert("RGB"))
    finally:
        os.remove(local)


def _signal(a: np.ndarray) -> np.ndarray:
    """What lines up with RGB greenness: plants are cooler (and darker in a coloured
    thermal preview) than soil."""
    return -(a.astype(np.float32) if a.ndim == 2 else a.astype(np.float32).mean(axis=2))


def _is_temperature(a: np.ndarray) -> bool:
    if a.ndim != 2 or a.dtype.kind != "f":
        return False
    v = a[np.isfinite(a)]
    return v.size > 0 and -60 < float(np.median(v)) < 120


def _put(client, bucket, name, data: bytes, ctype: str) -> None:
    client.put_object(bucket, name, io.BytesIO(data), len(data), content_type=ctype)


def _put_tif(client, bucket, name, arr: np.ndarray) -> None:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(arr.astype(np.float32))).save(buf, "TIFF")
    _put(client, bucket, name, buf.getvalue(), "image/tiff")


def _put_preview(client, bucket, name, arr: np.ndarray, window: tuple[float, float], valid=None) -> None:
    from PIL import Image

    from gemini.workers.thermal.calibration import apply_palette

    if arr.ndim == 3:
        rgb = arr.astype(np.uint8)
    else:
        v = arr.astype(np.float32).copy()
        if valid is not None:
            v[~valid] = np.nan
        rgb = apply_palette(v, vmin=window[0], vmax=window[1])
    buf = io.BytesIO()
    fmt = "PNG" if name.endswith(".png") else "JPEG"
    Image.fromarray(np.ascontiguousarray(rgb)).save(buf, fmt, **({"quality": 92} if fmt == "JPEG" else {}))
    _put(client, bucket, name, buf.getvalue(), "image/png" if fmt == "PNG" else "image/jpeg")


def plant_mask(flat: np.ndarray) -> np.ndarray:
    """Plant cells of a straightened RGB view (excess green, as EXTRACT_TRAITS); outside the plot is not."""
    return (C.greenness(flat) > C.EXG_PLANT) & (flat.reshape(flat.shape[0], flat.shape[1], -1).sum(axis=2) > 0)


def run(worker, job_id: str, client, bucket: str, *, others: dict[str, dict[str, str]], shots: list[F.Shot],
        raw: dict[str, str], plots: list[dict], out_prefix: str, keep: int, tmp: str,
        progress: Callable[[float, dict], None], safe: Callable[[Any], str],
        rgb_loader: Callable[[str], np.ndarray], run_label: str = "", merge: bool = False) -> dict[str, dict]:
    """Every other sensor of the flight (``others``, from sensors_beside), cut per plot.
    Returns {sensor: manifest section}; each plot dict gains plot["companions"][sensor]. A
    sensor that cannot be matched or lined up is reported in its section ("error") and
    skipped: the RGB plot images stand either way."""
    if not others:
        return {}
    by_name = {s.filename: s for s in shots}
    primary = _keys(client, bucket, {s.filename: raw[s.filename] for s in shots})
    out: dict[str, dict] = {}
    for si, (other, files) in enumerate(sorted(others.items())):
        def step(frac: float, info: dict, si=si) -> None:
            progress((si + frac) / len(others), {"sensor": other, **info})

        section: dict[str, Any] = {"frames": len(files)}
        out[other] = section
        try:
            _one_sensor(client, bucket, other, files, by_name, primary, raw, plots, out_prefix, keep, tmp,
                        section, step, safe, rgb_loader, worker, job_id, run_label, merge)
        except Exception as e:                       # one sensor's trouble does not lose the RGB plot images
            logger.exception("companion sensor %s", other)
            section["error"] = str(e)[:400]
    return out


def _one_sensor(client, bucket, other, files, by_name, primary, raw, plots, out_prefix, keep, tmp, section,
                step, safe, rgb_loader, worker, job_id, run_label: str = "", merge: bool = False) -> None:
    step(0.0, {"stage": "matching_frames"})
    comp_keys = _keys(client, bucket, files)
    pairs = C.pair(primary, comp_keys)
    section.update({"matched": len(pairs), "of_rgb_frames": len(primary),
                    "max_seconds_apart": round(max((abs(dt) for _, dt in pairs.values()), default=0.0), 2)})
    if not pairs:
        raise ValueError(f"none of the {len(files)} {other} frames was taken within 2 s of an RGB frame "
                         "(their names or EXIF give no capture time, or they are from another flight)")

    # The flight's alignment, measured on frames over the plots (spread through the flight).
    used = sorted({c.shot.filename for pl in plots for c in pl.get("candidates", []) if c.shot.filename in pairs})
    sample = (used or sorted(pairs))[:: max(1, len(used or pairs) // PAIRS_TO_LINE_UP)][:PAIRS_TO_LINE_UP]
    found, is_temp, size = [], None, None
    for i, name in enumerate(sample):
        step(0.05 + 0.25 * i / max(1, len(sample)), {"stage": "lining_up", "pairs_done": i, "pairs_total": len(sample)})
        comp = _load(client, bucket, files[pairs[name][0]], tmp)
        rgb = rgb_loader(name)
        is_temp = _is_temperature(comp) if is_temp is None else is_temp
        size = comp.shape[1], comp.shape[0]
        found.append(C.register(C.greenness(rgb), _signal(comp)))
    align = C.flight_alignment(found)
    section["alignment"] = {**align, "rgb_px_per_px": align["k"]}
    section["values"] = "temperature (°C)" if is_temp else "image (no temperatures)"

    # Each RGB frame's pose, with this camera's lens.
    lenses: dict[int, F.Lens] = {}
    comp_shots, rgb_of = [], {}
    for rgb_name, (comp_name, _dt) in pairs.items():
        s = by_name[rgb_name]
        lens = lenses.get(id(s.lens))
        if lens is None:
            lens = lenses[id(s.lens)] = C.companion_lens(s.lens, size[0], size[1], align["k"], align["x0"],
                                                         align["y0"])
        comp_shots.append(F.Shot(comp_name, s.center, s.rotation, lens))
        rgb_of[comp_name] = s
    need: dict[str, list] = defaultdict(list)
    for pl in plots:
        # More frames than the RGB pass keeps: this camera sees less ground, so a plot's view is
        # pieced together from several of them (the best one first, the others filling its gaps).
        cands = F.rank(comp_shots, pl["ring"], pl["ground"], keep=max(keep, COMPOSITE_FRAMES))
        if cands:
            pl["_grid_gsd"] = cands[0].gsd_m
        for r, c in enumerate(cands, 1):
            need[c.shot.filename].append((pl, r, c))

    sub = f"{out_prefix}{safe(other)}/"
    crops: list[tuple[str, np.ndarray]] = []
    for n, (comp_name, uses) in enumerate(need.items()):
        if worker.is_cancelled(job_id):
            return
        img = _load(client, bucket, files[comp_name], tmp)
        rgb_shot = rgb_of[comp_name]
        rgb_img = rgb_loader(rgb_shot.filename)
        # This frame's own alignment, near the flight's (the two cameras do not fire at quite
        # the same instant on a moving drone); the flight's where nothing lines up.
        own = C.refine(C.greenness(rgb_img), _signal(img), align)
        aligned = {"by": "flight", "score": None}
        if own is not None:
            shot = F.Shot(comp_name, rgb_shot.center, rgb_shot.rotation,
                          C.companion_lens(rgb_shot.lens, size[0], size[1], own.k, own.x0, own.y0))
            redone = []
            for pl, r, c in uses:
                got = F.rank([shot], pl["ring"], pl["ground"], keep=1)
                redone.append((pl, r, got[0] if got else c))
            uses = redone
            aligned = {"by": "frame", "score": round(own.score, 3),
                       "shift_px": round(math.hypot(own.x0 - align["x0"], own.y0 - align["y0"]), 1)}
        section["frames_aligned_on_their_own"] = section.get("frames_aligned_on_their_own", 0) + (own is not None)
        # The frame's values plus a channel of ones: where it is 1 after straightening, this frame saw the cell.
        planes = img.astype(np.float32)[..., None] if img.ndim == 2 else img.astype(np.float32)
        withseen = np.concatenate([planes, np.ones(img.shape[:2] + (1,), np.float32)], axis=2)
        for pl, r, c in uses:
            entry = pl.setdefault("companions", {}).setdefault(other, {"frames": []})
            if r <= keep:
                base = f"plot_{pl['plot']}_accession_{safe(pl['accession'])}"
                x0, y0, x1, y1 = c.bbox
                mx, my = int((x1 - x0) * CROP_MARGIN), int((y1 - y0) * CROP_MARGIN)
                H, W = img.shape[:2]
                box = (max(0, x0 - mx), max(0, y0 - my), min(W, x1 + mx), min(H, y1 + my))
                crop = img[box[1]:box[3], box[0]:box[2]]
                stem = f"{sub}crops/{base}_frame{r}_{os.path.splitext(comp_name)[0]}"
                frame = {"rank": r, "image": files[comp_name], "rgb_frame": raw[rgb_shot.filename],
                         "seconds_from_rgb": pairs[rgb_shot.filename][1], "inside": round(c.inside, 3),
                         "off_nadir_deg": round(c.off_nadir_deg, 2), "bbox": list(c.bbox),
                         "gsd_cm": round(c.gsd_m * 100, 2), "crop_preview": stem + ".jpg", "aligned": aligned}
                if img.ndim == 2:
                    frame["crop"] = stem + ".tif"
                    _put_tif(client, bucket, frame["crop"], crop)
                crops.append((frame["crop_preview"], crop))
                entry["frames"].append(frame)
            # This frame's view of the plot, on the plot's grid; it fills the cells no better frame saw.
            view, origin = F.straighten(withseen, c.shot, pl["ring"], pl["ground"], pl["_grid_gsd"])
            seen = view[..., -1] >= 0.999
            acc = pl.setdefault("_views", {}).get(other)
            if acc is None:
                acc = pl["_views"][other] = {"values": np.full(view.shape[:2] + (view.shape[2] - 1,), np.nan,
                                                               np.float32),
                                             "rank": np.full(view.shape[:2], 99, np.int16), "origin": origin}
            values = view[..., :-1]
            if values.shape[2] == 1 and is_temp:
                # Uncooled thermal cameras drift a little from frame to frame (a degree or so):
                # level this frame to the better ones where both saw the plot, so no seam shows.
                both = seen & (acc["rank"] < r)
                if both.sum() >= 50:
                    shift = float(np.nanmedian(acc["values"][..., 0][both] - values[..., 0][both]))
                    if abs(shift) > MAX_LEVEL_C:
                        # Far more than drift: this frame does not line up with the better ones.
                        acc.setdefault("left_out_c", []).append(round(shift, 2))
                        continue
                    values = values + shift
                    acc.setdefault("levelled_c", []).append(round(shift, 2))
            better = seen & (r < acc["rank"])
            acc["values"][better] = values[better]
            acc["rank"][better] = r
        step(0.3 + 0.6 * (n + 1) / max(1, len(need)), {"stage": "cutting", "frames_done": n + 1,
                                                        "frames_total": len(need)})

    # Each plot's pieced-together view, and what it says.
    flats: list[tuple[dict, np.ndarray, np.ndarray]] = []
    for pl in plots:
        acc = (pl.get("_views") or {}).pop(other, None)
        entry = (pl.get("companions") or {}).get(other)
        if acc is None or entry is None:
            continue
        base = f"plot_{pl['plot']}_accession_{safe(pl['accession'])}"
        x_min, y_max, gsd = acc["origin"]
        values = acc["values"][..., 0] if acc["values"].shape[2] == 1 else acc["values"]
        seen = acc["rank"] < 99
        h, w = seen.shape
        ys, xs = np.mgrid[0:h, 0:w]
        in_plot = F.points_in_polygon(np.column_stack([(x_min + (xs + 0.5) * gsd).ravel(),
                                                       (y_max - (ys + 0.5) * gsd).ravel()]),
                                      pl["ring"]).reshape(h, w)
        entry["cover"] = round(float((seen & in_plot).sum()) / max(1, int(in_plot.sum())), 3)
        entry["frames_pieced"] = int(len(np.unique(acc["rank"][seen])))
        if acc.get("levelled_c"):
            entry["levelled_c"] = acc["levelled_c"]   # each filling frame's offset to the best one
        if acc.get("left_out_c"):
            entry["left_out_c"] = acc["left_out_c"]   # frames too far off to piece in
        entry["straightened_preview"] = f"{sub}straightened/{base}.png"
        entry["straightened_origin"] = {"x_min": x_min, "y_max": y_max, "gsd_m": gsd}
        if values.ndim == 2:
            entry["straightened"] = f"{sub}straightened/{base}.tif"
            _put_tif(client, bucket, entry["straightened"], np.where(seen, values, np.nan))
            if is_temp and pl.get("_plant") is not None:
                frac = C.plant_fraction(pl["_plant"], (w, h))
                entry["canopy"] = C.canopy_from_fraction(values, frac, seen & in_plot)
        flats.append((entry, values, seen))

    # Colour every preview on one scale, so plots compare by eye.
    vals = np.concatenate([f[v].ravel() for _, f, v in flats if f.ndim == 2 and v.any()] or [np.zeros(0)])
    vals = vals[np.isfinite(vals)]
    window = (float(np.percentile(vals, 2)), float(np.percentile(vals, 98))) if vals.size else (0.0, 1.0)
    section["preview_window"] = [round(window[0], 2), round(window[1], 2)]
    for name, crop in crops:
        _put_preview(client, bucket, name, crop, window)
    for entry, flat, valid in flats:
        _put_preview(client, bucket, entry["straightened_preview"], flat, window, valid if flat.ndim == 2 else None)
    for pl in plots:
        e = (pl.get("companions") or {}).get(other)
        if e:
            e["frames"].sort(key=lambda f: f["rank"])
    covers = [e["cover"] for pl in plots for e in [(pl.get("companions") or {}).get(other)] if e and "cover" in e]
    if covers:
        section["plot_cover_median"] = round(float(np.median(covers)), 3)
    section["plots_seen"] = sum(1 for pl in plots if (pl.get("companions") or {}).get(other))
    section["prefix"] = sub

    if is_temp:
        feats = []
        for pl in plots:
            ct = ((pl.get("companions") or {}).get(other) or {}).get("canopy") or {}
            if "canopy_mean_c" not in ct:
                continue
            props = dict(pl["feature"].get("properties") or {})
            props.update({TRAIT[0]: ct["canopy_mean_c"], "Temp_veg_median_C": ct.get("canopy_median_c"),
                          "Temp_soil_avg_C": ct.get("soil_mean_c"), "plant_share": ct.get("plant_share")})
            feats.append({"type": "Feature", "geometry": pl["feature"]["geometry"], "properties": props})
        if merge:
            # Some plots only (added ones, or those without images yet): the earlier run's other
            # plots are kept, so the file and the stored trait still hold every plot (storing it
            # replaces the earlier run's records).
            from .plot_frames import merge_by_plot

            try:
                old = json.loads(client.get_object(bucket, f"{sub}traits.geojson").read())
            except Exception:
                old = {}
            feats = merge_by_plot(old.get("features") or [], feats,
                                  lambda f: (f.get("properties") or {}).get("plot"))
        section["canopy_temperature_plots"] = len(feats)
        if feats:
            path = f"{sub}traits.geojson"
            gj = {"type": "FeatureCollection", "features": feats}
            _put(client, bucket, path, json.dumps(gj).encode(), "application/geo+json")
            section["traits"] = path
            step(0.97, {"stage": "saving_traits"})
            from gemini.workers.ml.trait_ingest import ingest_trait_features

            # Each run of the day its own dataset (a later run must not replace an earlier one's
            # values), stamped with when it was flown: diurnal runs compare by time of day.
            times = sorted(t for t, _ in primary.values() if t is not None)
            # The camera's own clock, as in the frame names (local time, no zone): kept as it reads.
            flown = datetime.fromtimestamp(times[len(times) // 2]) if times else None
            label = f"{other} frames" + (f" · {run_label}" if run_label else "")
            section["trait_dataset_label"] = label
            try:
                section["trait_records"] = ingest_trait_features(
                    worker._http, output_path=path, geojson=gj, trait_columns=(TRAIT,), source="PLOT_FRAMES",
                    run_id=job_id, label=label, timestamp=flown)
            except Exception as e:
                # The values are in traits.geojson and the manifest; only keeping them as a trait failed.
                logger.exception("canopy temperature not stored as a trait")
                section["trait_error"] = str(e)[:300]
