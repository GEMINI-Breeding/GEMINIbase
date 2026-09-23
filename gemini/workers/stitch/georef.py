"""
Georeferencing for stitched ground-plot mosaics (ported from GEMINI-App
main, backend/app/processing/geo_utils.py).

A stitched plot has no geotransform of its own. The rover's GPS track over
the plot's frames gives its along-track axis (PCA of the UTM points) and
length; the image is laid along that axis, with the cross-track extent
taken from the GPS spread (at least 1 m).

    georeference_plot(mosaic, gps_df, out_tif)           → bool
    combine_utm_tiffs(utm_tifs, out_utm, out_wgs84)      → bool
    footprint_wgs84(utm_tif)                             → [[lon, lat], …]
"""
from __future__ import annotations

import logging
import math
import shutil
import traceback
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def pick_utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32700 if lat < 0 else 32600) + zone


def fit_angle_pca(x: np.ndarray, y: np.ndarray) -> float:
    pts = np.column_stack([x, y]) - np.column_stack([x, y]).mean(axis=0)
    _, _, v = np.linalg.svd(pts, full_matrices=False)
    vx, vy = v[0]
    return math.atan2(vy, vx)


def compute_axes_extents(xs, ys, theta: float, buffer_frac: float = 0.05):
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    u_vec = np.array([cos_t, sin_t])
    v_vec = np.array([-sin_t, cos_t])
    cx, cy = xs.mean(), ys.mean()
    pts = np.column_stack([xs - cx, ys - cy])
    u_proj = pts @ u_vec
    v_proj = pts @ v_vec
    u_min, u_max = u_proj.min(), u_proj.max()
    v_min, v_max = v_proj.min(), v_proj.max()
    u_len = u_max - u_min
    v_len = v_max - v_min
    u_min -= u_len * buffer_frac * 0.5
    u_max += u_len * buffer_frac * 0.5
    v_min -= v_len * buffer_frac * 0.5
    v_max += v_len * buffer_frac * 0.5
    return u_min, u_max, v_min, v_max, u_max - u_min, v_max - v_min


def build_rotated_affine(u_min, v_max, width_m, height_m, theta, px, py, gps_cx, gps_cy):
    from rasterio.transform import Affine

    tc = theta + math.pi
    cos_t, sin_t = math.cos(tc), math.sin(tc)
    x_offset = u_min * cos_t + v_max * (-sin_t)
    y_offset = u_min * sin_t + v_max * cos_t
    c = gps_cx + x_offset
    f = gps_cy + y_offset
    a = px * cos_t
    d = px * sin_t
    b = py * sin_t
    e = -py * cos_t
    return Affine(a, b, c, d, e, f)


def estimate_cross_track(xs, ys, theta: float, fixed_min: float = 1.0):
    """(height_m, v_min, v_max) — the GPS spread across track, at least fixed_min."""
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    v_vec = np.array([-sin_t, cos_t])
    cx, cy = xs.mean(), ys.mean()
    v_vals = np.column_stack([xs - cx, ys - cy]) @ v_vec
    v_min, v_max = v_vals.min(), v_vals.max()
    height_gps = v_max - v_min
    height_need = max(height_gps, fixed_min)
    if height_need > height_gps:
        v_center = 0.5 * (v_min + v_max)
        v_min = v_center - height_need / 2.0
        v_max = v_center + height_need / 2.0
    return height_need, v_min, v_max


def georeference_plot(mosaic_path: Path, gps_df: Any, out_tif: Path) -> bool:
    """Write out_tif: the mosaic as a UTM GeoTIFF laid along the GPS track.

    gps_df holds this plot's rows of msgs_synced (lat, lon), in capture order.
    """
    import rasterio
    from PIL import Image, ImageFile
    from pyproj import Transformer
    from rasterio.crs import CRS

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    Image.MAX_IMAGE_PIXELS = None

    lats = gps_df["lat"].astype(float).dropna().to_numpy()
    lons = gps_df["lon"].astype(float).dropna().to_numpy()
    if lats.size < 2:
        logger.warning("%s: not enough GPS points (%d)", mosaic_path.name, lats.size)
        return False

    center_lat = (lats.min() + lats.max()) / 2.0
    center_lon = (lons.min() + lons.max()) / 2.0
    utm_epsg = pick_utm_epsg(center_lon, center_lat)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)
    xs, ys = transformer.transform(lons, lats)
    xs, ys = np.asarray(xs), np.asarray(ys)

    with Image.open(mosaic_path) as im:
        img_array = np.array(im.convert("RGB"))
    h, w = img_array.shape[:2]

    theta = fit_angle_pca(xs, ys)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    if (cos_t * xs[-1] + sin_t * ys[-1]) < (cos_t * xs[0] + sin_t * ys[0]):
        theta += math.pi

    # Along-track length from the end-to-end GPS distance (robust to jitter).
    direct_dist = float(np.hypot(xs[-1] - xs[0], ys[-1] - ys[0]))
    width_m = max(direct_dist, 0.5)
    u_min, u_max, _, _, _, _ = compute_axes_extents(xs, ys, theta, buffer_frac=0.0)
    gps_cx, gps_cy = xs.mean(), ys.mean()
    u_center = (u_min + u_max) / 2.0
    u_min = u_center - width_m / 2.0

    height_m, _, v_max = estimate_cross_track(xs, ys, theta, fixed_min=1.0)
    px = width_m / w
    py = height_m / h
    transform = build_rotated_affine(u_min, v_max, width_m, height_m, theta, px, py, gps_cx, gps_cy)

    with rasterio.open(
        str(out_tif), "w",
        driver="GTiff", height=h, width=w, count=3, dtype=img_array.dtype,
        crs=CRS.from_epsg(utm_epsg), transform=transform,
        compress="lzw", tiled=True, blockxsize=512, blockysize=512,
    ) as dst:
        for i in range(3):
            dst.write(img_array[:, :, i], i + 1)
    return True


def combine_utm_tiffs(utm_tifs: List[Path], out_utm: Path, out_wgs84: Path) -> bool:
    """Merge per-plot UTM GeoTIFFs into one mosaic, then reproject to WGS84.

    Areas no plot covers are nodata (0), so a map shows only the plots.
    """
    import rasterio
    import rasterio.shutil
    from rasterio.crs import CRS
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    if not utm_tifs:
        return False
    if len(utm_tifs) == 1:
        shutil.copy2(utm_tifs[0], out_utm)
    else:
        srcs = [rasterio.open(str(f)) for f in utm_tifs]
        try:
            bl = [s.bounds for s in srcs]
            min_x = min(b[0] for b in bl)
            min_y = min(b[1] for b in bl)
            max_x = max(b[2] for b in bl)
            max_y = max(b[3] for b in bl)
            pixel_sizes = []
            for s in srcs:
                ps_x = abs(s.transform.a) if abs(s.transform.a) > 1e-10 else (max_x - min_x) / s.width
                ps_y = abs(s.transform.e) if abs(s.transform.e) > 1e-10 else (max_y - min_y) / s.height
                pixel_sizes.append(min(ps_x, ps_y))
            output_px = min(pixel_sizes)
            out_w = int((max_x - min_x) / output_px)
            out_h = int((max_y - min_y) / output_px)
            if out_w > 5000 or out_h > 5000:  # main's safety cap
                output_px = max((max_x - min_x) / 5000, (max_y - min_y) / 5000)
                out_w = int((max_x - min_x) / output_px)
                out_h = int((max_y - min_y) / output_px)
            out_transform = rasterio.transform.from_bounds(min_x, min_y, max_x, max_y, out_w, out_h)
            mosaic = np.zeros((3, out_h, out_w), dtype=np.uint8)
            for src in srcs:
                tmp = np.zeros((3, out_h, out_w), dtype=np.uint8)
                for band in range(3):
                    reproject(
                        source=rasterio.band(src, band + 1),
                        destination=tmp[band],
                        src_transform=src.transform, src_crs=src.crs,
                        dst_transform=out_transform, dst_crs=src.crs,
                        resampling=Resampling.bilinear, dst_nodata=0,
                    )
                covered = tmp.any(axis=0)
                mosaic[:, covered] = tmp[:, covered]
            meta = srcs[0].meta.copy()
            meta.update(
                driver="GTiff", height=out_h, width=out_w, transform=out_transform,
                crs=srcs[0].crs, compress="lzw", tiled=True, blockxsize=512,
                blockysize=512, count=3, dtype="uint8", nodata=0,
            )
            with rasterio.open(str(out_utm), "w", **meta) as dst:
                dst.write(mosaic)
        except Exception:
            logger.error("Mosaic creation failed:\n%s", traceback.format_exc())
            return False
        finally:
            for s in srcs:
                s.close()

    # WGS84, then a Cloud-Optimized GeoTIFF (with overviews) so TiTiler can
    # serve it as a map underlay at any zoom.
    plain = out_wgs84.with_name(out_wgs84.stem + ".plain.tif")
    try:
        with rasterio.open(str(out_utm)) as src:
            dst_crs = CRS.from_epsg(4326)
            transform, w, h = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            meta = src.meta.copy()
            meta.update(crs=dst_crs, transform=transform, width=w, height=h, nodata=0)
            with rasterio.open(str(plain), "w", **meta) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform, src_crs=src.crs,
                        dst_transform=transform, dst_crs=dst_crs,
                        resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0,
                    )
        rasterio.shutil.copy(
            str(plain), str(out_wgs84), driver="COG",
            compress="DEFLATE", overview_resampling="average",
        )
    except Exception:
        logger.error("WGS84 reproject failed:\n%s", traceback.format_exc())
        return False
    finally:
        plain.unlink(missing_ok=True)
    return True


def footprint_wgs84(utm_tif: Path) -> Optional[list]:
    """The plot's (rotated) footprint as a closed WGS84 ring, [[lon, lat], …]."""
    import rasterio
    from pyproj import Transformer

    with rasterio.open(str(utm_tif)) as src:
        w, h, t = src.width, src.height, src.transform
        epsg = src.crs.to_epsg()
    corners = [t @ (0, 0), t @ (w, 0), t @ (w, h), t @ (0, h)]
    tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    ring = [list(tr.transform(x, y)) for x, y in corners]
    ring.append(ring[0])
    return ring


def center_wgs84(utm_tif: Path) -> tuple:
    """(lon, lat) of the plot mosaic's centre."""
    import rasterio
    from pyproj import Transformer

    with rasterio.open(str(utm_tif)) as src:
        cx, cy = src.transform @ (src.width / 2, src.height / 2)
        epsg = src.crs.to_epsg()
    tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    return tr.transform(cx, cy)
