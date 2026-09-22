"""
Per-plot trait extraction kernels, ported from the pre-migration FastAPI
backend (main:backend/app/processing/aerial.py).

The kernels operate on arrays and file paths — no DB, no session, no
emit. The worker is responsible for plumbing the inputs (orthomosaic
path, DEM path, plot-boundary GeoJSON) in and the outputs (GeoJSON with
per-plot trait columns) out through MinIO.

Produced traits:
    - Vegetation_Fraction (0..1): fraction of plot pixels above ExG threshold
    - Height_95p_meters (optional): 95th percentile canopy height from DEM
    - Temp_veg_avg_C (optional): mean canopy temperature from a thermal
      orthomosaic, over the plot's vegetation pixels
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def compute_exg_mask(rgb_arr: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """Excess Green vegetation mask.

    ExG = 2·g − r − b on normalized channels; pixels above ``threshold``
    are vegetation. A 5×5 morphological close fills small gaps in canopy.

    Input: ``(H, W, 3)`` uint8 RGB. Output: ``(H, W)`` uint8 mask (0/255).
    """
    import cv2

    arr = rgb_arr.astype(np.float32)
    total = arr[:, :, 0] + arr[:, :, 1] + arr[:, :, 2]
    total = np.where(total == 0, 1.0, total)
    ratio = arr / total[:, :, np.newaxis]
    exg = 2 * ratio[:, :, 1] - ratio[:, :, 0] - ratio[:, :, 2]
    mask = (exg > threshold).astype(np.uint8) * 255
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def estimate_height_from_dem(
    dem_data: np.ndarray,
    vegetation_mask: np.ndarray,
) -> Optional[float]:
    """Estimate canopy height (metres) from a DEM crop + vegetation mask.

    Ground level = median of bare-soil (non-vegetation) pixels, falling
    back to the 5th percentile of all valid pixels when the canopy is
    dense. Canopy top = 95th percentile of vegetation pixels. Returns
    ``None`` when the DEM has no valid data.
    """
    import cv2

    if dem_data.size == 0:
        return None

    mask = cv2.resize(vegetation_mask, (dem_data.shape[1], dem_data.shape[0]))
    valid_mask = dem_data != 0
    all_valid = dem_data[valid_mask]
    if len(all_valid) == 0:
        return None

    soil_pixels = dem_data[(mask == 0) & valid_mask]
    if len(soil_pixels) >= 10:
        ground = float(np.median(soil_pixels))
    else:
        ground = float(np.percentile(all_valid, 5))

    # Match the old backend's semantics: any vegetation pixels at all are
    # enough to estimate a canopy top. Dropping sparse-canopy plots with a
    # `< 10` threshold would silently change the trait output vs. the old
    # output for the same orthomosaic.
    canopy_pixels = dem_data[(mask > 0) & valid_mask]
    if len(canopy_pixels) == 0:
        return None
    canopy_top = float(np.percentile(canopy_pixels, 95))
    height = canopy_top - ground
    return round(height, 4) if height > 0 else 0.0


def estimate_canopy_temperature(
    thermal_data: np.ndarray,
    vegetation_mask: np.ndarray,
    nodata: Optional[float] = None,
) -> Optional[float]:
    """Mean temperature (°C) of the vegetation pixels in a thermal crop.

    The RGB vegetation mask is resized onto the thermal grid (thermal
    orthos are much coarser). Non-finite and ``nodata`` pixels are
    excluded, so an ortho edge crossing the plot doesn't drag the mean
    toward the fill value. Returns ``None`` when no vegetation pixel has a
    reading. Assumes the raster holds temperatures in °C, as main did.
    """
    import cv2

    if thermal_data.size == 0:
        return None
    mask = cv2.resize(
        vegetation_mask,
        (thermal_data.shape[1], thermal_data.shape[0]),
        interpolation=cv2.INTER_NEAREST,
    )
    data = thermal_data.astype(np.float64)
    valid = np.isfinite(data)
    if nodata is not None and np.isfinite(nodata):
        valid &= data != nodata
    temps = data[(mask > 0) & valid]
    if temps.size == 0:
        return None
    return round(float(np.mean(temps)), 2)


def extract_traits_from_ortho(
    rgb_path: str,
    boundary_geojson_path: str,
    dem_path: Optional[str] = None,
    exg_threshold: float = 0.1,
    thermal_path: Optional[str] = None,
) -> Tuple[List[dict], Any]:
    """Compute per-plot traits and return ``(records, geojson_dict)``.

    ``records`` is a list of ``{plot_index, Vegetation_Fraction,
    Height_95p_meters}`` dicts; ``geojson_dict`` is the boundary GeoJSON
    mutated to include those properties per feature.
    """
    import geopandas as gpd
    import rasterio
    from rasterio.windows import from_bounds as _from_bounds

    gdf = gpd.read_file(boundary_geojson_path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    records: List[dict] = []

    with rasterio.open(rgb_path) as rgb_src:
        gdf_raster = gdf.to_crs(rgb_src.crs) if gdf.crs != rgb_src.crs else gdf
        dem_src = rasterio.open(dem_path) if dem_path else None
        gdf_dem = None
        if dem_src is not None:
            gdf_dem = (
                gdf.to_crs(dem_src.crs)
                if dem_src.crs != rgb_src.crs
                else gdf_raster
            )
        th_src = rasterio.open(thermal_path) if thermal_path else None
        gdf_th = None
        if th_src is not None:
            gdf_th = (
                gdf.to_crs(th_src.crs) if th_src.crs != rgb_src.crs else gdf_raster
            )

        try:
            for i, (_, row) in enumerate(gdf_raster.iterrows()):
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue

                bounds = geom.bounds
                window = _from_bounds(*bounds, rgb_src.transform)
                rgb_data = rgb_src.read(
                    [1, 2, 3], window=window, boundless=True, fill_value=0
                )
                rgb_arr = np.transpose(rgb_data, (1, 2, 0))
                if rgb_arr.size == 0 or rgb_arr.shape[0] == 0 or rgb_arr.shape[1] == 0:
                    continue

                mask = compute_exg_mask(rgb_arr, threshold=exg_threshold)
                vf = round(float(np.sum(mask > 0)) / mask.size, 4)

                height_m: Optional[float] = None
                if dem_src is not None and gdf_dem is not None:
                    dem_row = gdf_dem.iloc[i]
                    dem_window = _from_bounds(
                        *dem_row.geometry.bounds, dem_src.transform
                    )
                    dem_data = dem_src.read(
                        1, window=dem_window, boundless=True, fill_value=0
                    )
                    height_m = estimate_height_from_dem(dem_data, mask)

                temp_c: Optional[float] = None
                if th_src is not None and gdf_th is not None:
                    th_row = gdf_th.iloc[i]
                    th_window = _from_bounds(
                        *th_row.geometry.bounds, th_src.transform
                    )
                    th_data = th_src.read(
                        1, window=th_window, boundless=True, fill_value=np.nan
                    )
                    temp_c = estimate_canopy_temperature(
                        th_data, mask, nodata=th_src.nodata
                    )

                record = {
                    "plot_index": i,
                    "Vegetation_Fraction": vf,
                    "Height_95p_meters": height_m,
                    "Temp_veg_avg_C": temp_c,
                }
                records.append(record)
        finally:
            if dem_src is not None:
                dem_src.close()
            if th_src is not None:
                th_src.close()

    # Merge traits back onto original-CRS GeoJSON so downstream map layers
    # don't have to reason about raster vs. WGS84 CRS.
    gdf_out = gdf.copy()
    gdf_out["Vegetation_Fraction"] = None
    gdf_out["Height_95p_meters"] = None
    gdf_out["Temp_veg_avg_C"] = None
    for rec in records:
        idx = rec["plot_index"]
        gdf_out.at[gdf_out.index[idx], "Vegetation_Fraction"] = rec[
            "Vegetation_Fraction"
        ]
        gdf_out.at[gdf_out.index[idx], "Height_95p_meters"] = rec[
            "Height_95p_meters"
        ]
        gdf_out.at[gdf_out.index[idx], "Temp_veg_avg_C"] = rec["Temp_veg_avg_C"]

    import json as _json

    geojson_dict = _json.loads(gdf_out.to_json())
    return records, geojson_dict
