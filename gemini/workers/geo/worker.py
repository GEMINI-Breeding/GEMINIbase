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
        return {JobType.CREATE_COG, JobType.TIF_TO_PNG, JobType.PROCESS_DRONE_TIFF,
                JobType.SPLIT_ORTHOMOSAIC, JobType.DATA_SYNC, JobType.IMPORT_LEGACY}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.CREATE_COG.value:
            return self._create_cog_job(job_id, parameters)
        elif job_type == JobType.TIF_TO_PNG.value:
            return self._tif_to_png_job(job_id, parameters)
        elif job_type == JobType.PROCESS_DRONE_TIFF.value:
            return self._process_drone_tiff_job(job_id, parameters)
        elif job_type == JobType.SPLIT_ORTHOMOSAIC.value:
            return self._split_orthomosaic_job(job_id, parameters)
        elif job_type == JobType.DATA_SYNC.value:
            return self._data_sync_job(job_id, parameters)
        elif job_type == JobType.IMPORT_LEGACY.value:
            return self._import_legacy_job(job_id, parameters)
        else:
            raise ValueError(f"Unsupported job type: {job_type}")

    def _data_sync_job(self, job_id: str, p: dict) -> dict:
        """Give every image of the run a capture time and position (see
        gemini/workers/geo/sync.py for the rules; main's run_data_sync /
        run_cross_sensor_sync).

        Parameters
            scope_prefix        Raw/…/{sensor}/ — searched for platform logs
                                under any Metadata/ folder; geo.txt goes here
            images_prefixes     the run's image folders (…/Images/)
            mode                "own_metadata" | "cross_sensor"
            source_track_path   cross_sensor: the reference msgs_synced.csv
            max_extrapolation_sec  cross_sensor clamp window (default 30)
            write_geo_txt       write {scope}geo.txt for ODM

        Writes {dataset}/Metadata/msgs_synced.csv per image folder (image,
        timestamp, lat, lon, alt, gps_source, direction). A folder that
        already has a track it didn't write — an Amiga extraction's or an
        uploaded one — keeps it: own_metadata uses it as is, cross_sensor
        refuses rather than overwrite it.
        """
        import io as _io

        import pandas as pd

        from gemini.workers.amiga.headings import add_direction_columns
        from gemini.workers.geo import sync

        scope = p["scope_prefix"].rstrip("/") + "/"
        prefixes = [x.rstrip("/") + "/" for x in p.get("images_prefixes") or []]
        mode = p.get("mode") or "own_metadata"
        if not prefixes:
            raise ValueError("No image folders to sync.")
        client = _get_minio_client()

        def read_csv(obj: str) -> pd.DataFrame:
            r = client.get_object(STORAGE_BUCKET, obj)
            try:
                return pd.read_csv(_io.BytesIO(r.read()), on_bad_lines="skip")
            finally:
                r.close()
                r.release_conn()

        def put(obj: str, text: str, ctype: str) -> None:
            data = text.encode()
            client.put_object(STORAGE_BUCKET, obj, _io.BytesIO(data), len(data), content_type=ctype)

        ref = None
        if mode == "cross_sensor":
            src = p.get("source_track_path")
            if not src:
                raise ValueError("Cross-sensor sync needs a source track.")
            ref = sync.reference_track(read_csv(src))
        max_ext = float(p.get("max_extrapolation_sec", 30))

        # Platform logs anywhere under the scope's Metadata/ folders.
        log_df = pd.DataFrame()
        if mode == "own_metadata":
            logs = [
                o.object_name for o in client.list_objects(STORAGE_BUCKET, scope, recursive=True)
                if "/Metadata/" in o.object_name and o.object_name.lower().endswith(sync.LOG_EXTS)
            ]
            frames = []
            with tempfile.TemporaryDirectory() as tmp:
                for i, obj in enumerate(logs):
                    self.report_progress(job_id, 5, {"stage": f"Reading platform log {i + 1}/{len(logs)}"})
                    local = os.path.join(tmp, os.path.basename(obj))
                    client.fget_object(STORAGE_BUCKET, obj, local)
                    try:
                        frames.append(sync.parse_platform_log(local))
                    except Exception as exc:
                        logger.warning("Couldn't parse platform log %s: %s", obj, exc)
            frames = [f for f in frames if not f.empty]
            if frames:
                log_df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
                put(scope + "drone_msgs.csv", log_df.to_csv(index=False), "text/csv")

        summary, geo_rows = {}, []
        for n, prefix in enumerate(prefixes):
            root = prefix[: prefix.rfind("Images/")] if "Images/" in prefix else prefix
            track_path = root + "Metadata/msgs_synced.csv"
            existing = None
            try:
                existing = read_csv(track_path)
            except Exception:
                pass
            if existing is not None and "gps_source" not in existing.columns:
                if mode == "cross_sensor":
                    raise ValueError(
                        f"{track_path} already holds this data's own track; "
                        "cross-sensor sync won't overwrite it."
                    )
                df = sync.normalise_columns(existing)
                df["image"] = df["image_path"].astype(str).str.split("/").str[-1]
                summary[prefix] = {"bundled": int(df["lat"].notna().sum()), "images": len(df)}
                geo_rows.append(df)
                continue

            names = [
                o.object_name for o in client.list_objects(STORAGE_BUCKET, prefix)
                if o.object_name.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
            ]
            rows = []
            for i, obj in enumerate(names):
                if i % 25 == 0:
                    self.report_progress(
                        job_id, 10 + 80 * (n + i / max(len(names), 1)) / len(prefixes),
                        {"stage": f"Reading image metadata {i + 1}/{len(names)}"},
                    )
                # EXIF sits in the first few KB; don't pull whole images.
                r = client.get_object(STORAGE_BUCKET, obj, offset=0, length=256 * 1024)
                try:
                    rec = sync.exif_record(r.read())
                finally:
                    r.close()
                    r.release_conn()
                rows.append({"image": obj.rsplit("/", 1)[-1], **rec,
                             "gps_source": "exif" if rec["lat"] is not None else "none"})
            df = pd.DataFrame(rows, columns=["image", "timestamp", "lat", "lon", "alt", "gps_source"])
            df = df.sort_values(["timestamp", "image"], na_position="last").reset_index(drop=True)
            if mode == "cross_sensor":
                df = sync.cross_sensor(df, ref, max_ext)
            elif not log_df.empty:
                df = sync.merge_log_gps(df, log_df)
            if df["lat"].notna().sum() >= 2:
                add_direction_columns(df)
            df, _ = sync.fill_missing_altitude(df)
            put(track_path, df.to_csv(index=False), "text/csv")
            summary[prefix] = {"images": len(df), **df["gps_source"].value_counts().to_dict()}
            geo_rows.append(df)

        # Across folders too: a folder with no altitude at all must not sit
        # at 0 m beside one that has it.
        geo_all, _ = sync.fill_missing_altitude(pd.concat(geo_rows, ignore_index=True))
        if p.get("write_geo_txt"):
            put(scope + "geo.txt", sync.geo_txt(geo_all), "text/plain")
        located_rows = geo_all["lat"].notna() & geo_all["lon"].notna()
        altitude = {
            "estimated": int((geo_all["alt_estimated"] == True).sum()),  # noqa: E712
            "missing": int((located_rows & geo_all["alt"].isna()).sum()),
        }
        total = sum(v.get("images", 0) for v in summary.values())
        located = sum(int(df["lat"].notna().sum()) for df in geo_rows)
        if located == 0:
            raise RuntimeError(
                f"None of the {total} images has a position: no EXIF GPS"
                + (", and none fell inside the source track's time span" if mode == "cross_sensor" else "")
                + "."
            )
        return {"mode": mode, "datasets": summary, "images": total, "located": located,
                "platform_log_fixes": int(len(log_df)), "altitude": altitude}

    def _import_legacy_job(self, job_id: str, p: dict) -> dict:
        """Import the previous GEMI desktop app's uploads (tier 1; see
        gemini/importers/gemi_legacy). The old install is mounted read-only
        at GEMINI_LEGACY_APP_DIR / GEMINI_LEGACY_DATA_DIR. Re-running
        resumes: what's already imported is found and skipped."""
        from gemini.importers.gemi_legacy.plan import plan_import
        from gemini.importers.gemi_legacy.reader import LegacyDatabase
        from gemini.importers.gemi_legacy.run import run_import
        from gemini.importers.gemi_legacy.source import legacy_data_dir, legacy_database

        db_path = legacy_database()
        if db_path is None:
            raise RuntimeError("No previous GEMI install is available to import.")
        self.report_progress(job_id, 0, {"stage": "Reading the previous GEMI install"})
        with LegacyDatabase(db_path) as db:
            plan = plan_import(db, legacy_data_dir())
        result = run_import(
            plan, legacy_data_dir(), self._http, _get_minio_client(), STORAGE_BUCKET,
            progress=lambda pct, msg: self.report_progress(job_id, pct, {"stage": msg}),
            cancelled=lambda: self.is_cancelled(job_id),
        )
        if result["failed"] and not result["imported"]:
            raise RuntimeError(
                "Nothing could be imported: " + "; ".join(f"{f['path']}: {f['error']}" for f in result["failed"])
            )
        return result

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
        year = parameters["year"]
        experiment = parameters["experiment"]
        location = parameters["location"]
        population = parameters["population"]
        date = parameters["date"]
        boundaries = parameters["boundaries"]

        features = boundaries.get("features", [])
        if not features:
            # Fail, don't "succeed" with nothing done: the step would turn
            # green and the user would find no plot images later.
            raise ValueError("No plot boundaries provided")

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
        explicit = parameters.get("orthomosaic_path")
        if explicit:
            # The run's chosen ortho — required for imported orthos, which
            # live under Raw/…/Orthomosaic/ where discovery never looks.
            orthomosaics = [explicit]
        else:
            try:
                candidates_by_folder: dict[str, tuple[str, object]] = {}
                objects = client.list_objects(
                    STORAGE_BUCKET, prefix=base_prefix, recursive=True
                )
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
                raise

        if not orthomosaics:
            raise FileNotFoundError(
                f"No orthomosaic found under {base_prefix} — run the "
                "orthomosaic step or import one first"
            )

        logger.info(f"Found {len(orthomosaics)} orthomosaic(s): {orthomosaics}")
        self.report_progress(job_id, 10, {"stage": "downloading", "orthomosaics": len(orthomosaics)})

        # Heavy imports only once there is work to do.
        import json
        import numpy as np
        import rasterio
        from rasterio.mask import mask as rio_mask
        from rasterio.warp import transform_geom
        from PIL import Image

        total_plots = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            for ortho_idx, ortho_path in enumerate(orthomosaics):
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

                # {Processed|Raw}/year/exp/loc/pop/date/platform/sensor/…
                # Positional, so both an ODM output (…/sensor/odm_…tif) and
                # an imported ortho (…/sensor/Orthomosaic/x.tif) resolve.
                parts = ortho_path.split("/")
                platform = parts[6]
                sensor = parts[7]
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
