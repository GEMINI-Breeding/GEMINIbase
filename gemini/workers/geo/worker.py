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
    Convert a GeoTIFF to Cloud Optimized GeoTIFF using rio-cogeo.

    Why rio-cogeo (not a hand-rolled reproject + build_overviews):

    The previous implementation reprojected to EPSG:3857 with bilinear
    resampling and built overviews with `average` over the full RGBA
    stack, with hardcoded levels `[2, 4, 8, 16, 32, 64, 128, 256]`. For
    a 1100×1400 source the deepest level was a 5×6-pixel thumbnail, and
    `average` on RGBA blurred the alpha band into a fractional blob. At
    zoomed-out map views TiTiler picks the deepest pyramid level whose
    pixel size beats the tile request — it would stretch the 5×6 alpha-
    smeared thumbnail to a 256×256 tile, producing both the "swirled"
    appearance and a visibly *different ortho footprint* (the alpha
    averaging dissolved the real outline) at low zooms. Zoom-in fixed
    the render because TiTiler then served finer pyramid levels.

    rio-cogeo (GDAL COG driver under the hood) fixes this for free:
      - `web_optimized=True` warps to Web Mercator and aligns the COG's
        blocks to the Google/Mercator XYZ tile pyramid, so TiTiler can
        read tiles without re-tiling.
      - Overview level is auto-derived from the source size so the
        deepest level is ~256 px on its smaller dimension — no more
        sub-tile thumbnails.
      - The COG driver builds alpha-aware overviews: the alpha mask is
        respected during downsampling instead of being averaged into
        the data, so the rendered outline stays sharp at every zoom.
    """
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    output_profile = cog_profiles.get("deflate")
    output_profile.update(
        dict(
            BIGTIFF="IF_SAFER",
            blockxsize=512,
            blockysize=512,
        )
    )
    # GDAL_TIFF_INTERNAL_MASK=YES tells the COG driver to honor the
    # source's alpha band (colorinterp[-1] == 'alpha') as the mask when
    # downsampling for overviews, instead of averaging alpha into the
    # data bands.
    config = dict(
        GDAL_NUM_THREADS="ALL_CPUS",
        GDAL_TIFF_INTERNAL_MASK=True,
        GDAL_TIFF_OVR_BLOCKSIZE="512",
    )
    cog_translate(
        input_path,
        output_path,
        output_profile,
        config=config,
        web_optimized=True,
        overview_resampling="average",
        in_memory=False,
        quiet=True,
    )


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

        # Find orthomosaic files by listing objects under the date prefix.
        # RUN_ODM writes `odm_orthophoto-{job_id}.tif` per run, so each
        # (platform, sensor) folder may contain several historical versions
        # plus matching `-Pyramid.tif` COGs. Pick the newest source TIF per
        # folder and skip pyramids — splitting always operates on the
        # latest ortho.
        orthomosaics: list[str] = []
        try:
            candidates_by_folder: dict[str, tuple[str, object]] = {}
            objects = client.list_objects(STORAGE_BUCKET, prefix=base_prefix, recursive=True)
            for obj in objects:
                name = obj.object_name
                basename = name.rsplit("/", 1)[-1]
                if not basename.startswith("odm_orthophoto"):
                    continue
                if not (basename.endswith(".tif") or basename.endswith(".tiff")):
                    continue
                if "-Pyramid." in basename:
                    continue
                folder = name.rsplit("/", 1)[0]
                lm = getattr(obj, "last_modified", None)
                existing = candidates_by_folder.get(folder)
                if existing is None:
                    candidates_by_folder[folder] = (name, lm)
                elif lm is not None and (existing[1] is None or lm > existing[1]):
                    candidates_by_folder[folder] = (name, lm)
            orthomosaics = [path for path, _ in candidates_by_folder.values()]
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
