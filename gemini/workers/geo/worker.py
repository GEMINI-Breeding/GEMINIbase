"""
Geo processing worker.

Handles geospatial operations:
- CREATE_COG: Convert GeoTIFF to Cloud Optimized GeoTIFF with pyramid overviews
- TIF_TO_PNG: Convert GeoTIFF to PNG for preview
- PROCESS_DRONE_TIFF: Process raw drone GeoTIFF data

Requires: rasterio, GDAL (installed in the worker Docker image).
"""
import logging
import os
import tempfile
from typing import Set

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

# MinIO connection (S3-compatible)
STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")


def _get_minio_client():
    """Create a MinIO client for file access."""
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _create_cog(input_path: str, output_path: str):
    """
    Convert a GeoTIFF to Cloud Optimized GeoTIFF with pyramid overviews.

    Reprojects to Web Mercator (EPSG:3857), creates internal tiles,
    and builds overview pyramids for efficient tile serving.
    """
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.shutil import copy as rio_copy
    from rasterio.warp import calculate_default_transform, reproject

    with rasterio.open(input_path) as src:
        dst_crs = "EPSG:3857"
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=transform,
            width=width,
            height=height,
            driver="GTiff",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            compress="deflate",
            predictor=2 if src.dtypes[0] in ("uint8", "uint16", "int16") else 3,
            bigtiff="YES",
        )

        # Write reprojected data to a temp file, then create COG overviews
        tmp_path = output_path + ".tmp.tif"
        with rasterio.open(tmp_path, "w", **profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                )

        # Build overviews
        overview_levels = [2, 4, 8, 16, 32, 64, 128, 256]
        with rasterio.open(tmp_path, "r+") as dst:
            dst.build_overviews(overview_levels, Resampling.nearest)
            dst.update_tags(ns="rio_overview", resampling="nearest")

        # Copy to COG layout
        rio_copy(tmp_path, output_path, driver="GTiff", copy_src_overviews=True, tiled=True)
        os.remove(tmp_path)


class GeoWorker(BaseWorker):
    """Worker for geospatial processing tasks."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.CREATE_COG, JobType.TIF_TO_PNG, JobType.PROCESS_DRONE_TIFF, JobType.SPLIT_ORTHOMOSAIC}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.CREATE_COG.value:
            return self._create_cog_job(job_id, parameters)
        elif job_type == JobType.TIF_TO_PNG.value:
            return self._tif_to_png_job(job_id, parameters)
        elif job_type == JobType.PROCESS_DRONE_TIFF.value:
            return self._process_drone_tiff_job(job_id, parameters)
        elif job_type == JobType.SPLIT_ORTHOMOSAIC.value:
            return self._split_orthomosaic_job(job_id, parameters)
        else:
            raise ValueError(f"Unsupported job type: {job_type}")

    def _create_cog_job(self, job_id: str, parameters: dict) -> dict:
        """
        Convert a GeoTIFF in MinIO to a Cloud Optimized GeoTIFF.

        Parameters:
            input_path: MinIO object path (e.g. "Processed/2024/exp1/.../ortho.tif")
            output_path: MinIO object path for COG output (optional, defaults to input with -COG suffix)
        """
        input_path = parameters["input_path"]
        output_path = parameters.get("output_path")
        if not output_path:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}-Pyramid{ext}"

        client = _get_minio_client()

        self.report_progress(job_id, 10, {"stage": "downloading"})
        with tempfile.TemporaryDirectory() as tmpdir:
            local_input = os.path.join(tmpdir, "input.tif")
            local_output = os.path.join(tmpdir, "output.tif")

            # Download from MinIO
            client.fget_object(STORAGE_BUCKET, input_path, local_input)

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            self.report_progress(job_id, 30, {"stage": "creating_cog"})
            _create_cog(local_input, local_output)

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            self.report_progress(job_id, 80, {"stage": "uploading"})
            client.fput_object(STORAGE_BUCKET, output_path, local_output)

        return {"output_path": output_path}

    def _tif_to_png_job(self, job_id: str, parameters: dict) -> dict:
        """
        Convert a GeoTIFF to PNG for preview/thumbnail.

        Parameters:
            input_path: MinIO object path
            output_path: MinIO object path for PNG output
        """
        input_path = parameters["input_path"]
        output_path = parameters.get("output_path")
        if not output_path:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}.png"

        client = _get_minio_client()

        self.report_progress(job_id, 10, {"stage": "downloading"})
        with tempfile.TemporaryDirectory() as tmpdir:
            local_input = os.path.join(tmpdir, "input.tif")
            local_output = os.path.join(tmpdir, "output.png")

            client.fget_object(STORAGE_BUCKET, input_path, local_input)

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            self.report_progress(job_id, 50, {"stage": "converting"})

            import rasterio
            from PIL import Image
            import numpy as np

            with rasterio.open(local_input) as src:
                # Read first 3 bands (RGB) or single band
                if src.count >= 3:
                    data = src.read([1, 2, 3])
                    img = np.moveaxis(data, 0, -1)
                else:
                    img = src.read(1)

                # Normalize to 0-255
                if img.dtype != np.uint8:
                    img = ((img - img.min()) / (img.max() - img.min() + 1e-10) * 255).astype(np.uint8)

            Image.fromarray(img).save(local_output)

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            self.report_progress(job_id, 80, {"stage": "uploading"})
            client.fput_object(STORAGE_BUCKET, output_path, local_output, content_type="image/png")

        return {"output_path": output_path}

    def _process_drone_tiff_job(self, job_id: str, parameters: dict) -> dict:
        """
        Process raw drone GeoTIFF: create COG + PNG preview.

        Parameters:
            input_path: MinIO object path to raw drone GeoTIFF
        """
        input_path = parameters["input_path"]
        base, ext = os.path.splitext(input_path)
        cog_path = f"{base}-Pyramid{ext}"
        png_path = f"{base}.png"

        # Create COG
        self.report_progress(job_id, 5, {"stage": "creating_cog"})
        cog_result = self._create_cog_job(job_id, {
            "input_path": input_path,
            "output_path": cog_path,
        })

        if self.is_cancelled(job_id):
            return {"status": "cancelled"}

        # Create PNG preview
        self.report_progress(job_id, 85, {"stage": "creating_preview"})
        png_result = self._tif_to_png_job(job_id, {
            "input_path": input_path,
            "output_path": png_path,
        })

        return {
            "cog_path": cog_result.get("output_path"),
            "png_path": png_result.get("output_path"),
        }


    def _split_orthomosaic_job(self, job_id: str, parameters: dict) -> dict:
        """
        Split an orthomosaic into individual plot images based on GeoJSON boundaries.

        Parameters:
            year, experiment, location, population, date: Path components
            boundaries: GeoJSON FeatureCollection with plot polygons (WGS84)
        """
        import json
        import numpy as np
        import rasterio
        from rasterio.mask import mask as rio_mask
        from rasterio.warp import transform_geom
        from PIL import Image

        year = parameters["year"]
        experiment = parameters["experiment"]
        location = parameters["location"]
        population = parameters["population"]
        date = parameters["date"]
        boundaries = parameters["boundaries"]

        features = boundaries.get("features", [])
        if not features:
            return {"plots_processed": 0, "error": "No plot boundaries provided"}

        client = _get_minio_client()
        base_prefix = f"Processed/{year}/{experiment}/{location}/{population}/{date}/"

        self.report_progress(job_id, 5, {"stage": "discovering_orthomosaics"})

        # Find orthomosaic files by listing objects under the date prefix
        orthomosaics = []
        try:
            objects = client.list_objects(STORAGE_BUCKET, prefix=base_prefix, recursive=True)
            for obj in objects:
                if obj.object_name.endswith("odm_orthophoto.tif"):
                    orthomosaics.append(obj.object_name)
        except Exception as e:
            logger.error(f"Error listing objects: {e}")
            return {"plots_processed": 0, "error": str(e)}

        if not orthomosaics:
            return {"plots_processed": 0, "error": "No orthomosaics found"}

        logger.info(f"Found {len(orthomosaics)} orthomosaic(s): {orthomosaics}")
        self.report_progress(job_id, 10, {"stage": "downloading", "orthomosaics": len(orthomosaics)})

        total_plots = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            for ortho_idx, ortho_path in enumerate(orthomosaics):
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

                # Extract platform/sensor from path
                # Path: Processed/year/exp/loc/pop/date/platform/sensor/odm_orthophoto.tif
                parts = ortho_path.split("/")
                platform = parts[-3]
                sensor = parts[-2]
                output_prefix = f"Processed/{year}/{experiment}/{location}/{population}/{date}/{platform}/{sensor}/PlotImages/"

                # Download orthomosaic
                local_ortho = os.path.join(tmpdir, f"ortho_{ortho_idx}.tif")
                client.fget_object(STORAGE_BUCKET, ortho_path, local_ortho)

                base_progress = 10 + (ortho_idx / max(len(orthomosaics), 1)) * 80
                self.report_progress(job_id, int(base_progress), {
                    "stage": "processing",
                    "orthomosaic": f"{platform}/{sensor}",
                })

                with rasterio.open(local_ortho) as src:
                    raster_crs = src.crs
                    nodata = src.nodata

                    for feat_idx, feature in enumerate(features):
                        if self.is_cancelled(job_id):
                            return {"status": "cancelled"}

                        props = feature.get("properties", {})
                        plot_num = props.get("plot", props.get("Plot", feat_idx + 1))
                        accession = props.get("accession", props.get("Accession",
                                     props.get("Label", props.get("label", f"unknown"))))

                        # Transform geometry from WGS84 to raster CRS
                        try:
                            transformed_geom = transform_geom(
                                "EPSG:4326", raster_crs, feature["geometry"]
                            )
                        except Exception as e:
                            logger.warning(f"Failed to transform geometry for plot {plot_num}: {e}")
                            continue

                        # Mask the raster with the plot polygon
                        try:
                            out_image, out_transform = rio_mask(
                                src, [transformed_geom], crop=True, nodata=0
                            )
                        except Exception as e:
                            logger.warning(f"Failed to mask plot {plot_num}: {e}")
                            continue

                        # Convert to RGB PNG
                        if out_image.shape[0] >= 3:
                            rgb = np.moveaxis(out_image[:3], 0, -1)
                        else:
                            rgb = np.moveaxis(np.stack([out_image[0]] * 3), 0, -1)

                        if rgb.dtype != np.uint8:
                            rgb = ((rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-10) * 255).astype(np.uint8)

                        # Save as PNG
                        safe_accession = str(accession).replace("/", "_").replace(" ", "_")
                        filename = f"plot_{plot_num}_accession_{safe_accession}.png"
                        local_png = os.path.join(tmpdir, filename)
                        Image.fromarray(rgb).save(local_png)

                        # Upload to MinIO
                        object_name = f"{output_prefix}{filename}"
                        client.fput_object(
                            STORAGE_BUCKET, object_name, local_png,
                            content_type="image/png",
                        )
                        total_plots += 1

                        # Report per-plot progress
                        plot_progress = base_progress + ((feat_idx + 1) / len(features)) * (80 / max(len(orthomosaics), 1))
                        self.report_progress(job_id, min(int(plot_progress), 95), {
                            "stage": "processing",
                            "plot": plot_num,
                            "plots_done": total_plots,
                            "total_features": len(features),
                        })

                        logger.info(f"Extracted plot {plot_num} ({accession}) -> {object_name}")

                # Clean up downloaded ortho
                os.remove(local_ortho)

        self.report_progress(job_id, 100, {"stage": "complete"})
        return {"plots_processed": total_plots, "output_prefix": output_prefix if orthomosaics else ""}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = GeoWorker()
    worker.run()
