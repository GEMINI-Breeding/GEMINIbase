"""
ML / trait-extraction worker.

Dispatches on job_type:
    - LOCATE_PLANTS  → Roboflow cloud inference on a single image, returns
                       per-detection list + per-class counts.
    - EXTRACT_TRAITS → ExG vegetation fraction + canopy height per plot,
                       from an orthomosaic (and optional DEM) against a
                       plot-boundary GeoJSON.
    - TRAIN_MODEL    → not implemented (raises); TRAIN_MODEL requires a
                       training framework + GPU scheduling that belongs in
                       its own worker with elastic resources.

Inputs/outputs are exchanged via MinIO: the caller submits MinIO object
paths in ``parameters``; the worker downloads, processes, uploads
result artifacts, and returns the result paths on the job record.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Set

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")


def _get_minio_client():
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


class MlWorker(BaseWorker):
    """Worker for ML + trait-extraction tasks."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {
            JobType.LOCATE_PLANTS,
            JobType.EXTRACT_TRAITS,
            JobType.TRAIN_MODEL,
        }

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.LOCATE_PLANTS.value:
            return self._locate_plants_job(job_id, parameters)
        if job_type == JobType.EXTRACT_TRAITS.value:
            return self._extract_traits_job(job_id, parameters)
        if job_type == JobType.TRAIN_MODEL.value:
            # Deferred to a future worker rev (requires GPU scheduling +
            # a training framework we haven't provisioned yet).
            raise NotImplementedError(
                "TRAIN_MODEL is not yet implemented in this worker. "
                "Submit TRAIN_MODEL jobs only once the ml worker has the "
                "training framework + GPU scheduling support."
            )
        raise ValueError(f"Unsupported job type: {job_type}")

    # ------------------------------------------------------------------
    # LOCATE_PLANTS
    # ------------------------------------------------------------------

    def _locate_plants_job(self, job_id: str, parameters: dict) -> dict:
        """Roboflow cloud inference on a single image.

        Parameters:
            image_path: MinIO object path to a PNG/JPEG
            api_key: Roboflow API key (string)
            model_id: "workspace/model/version" or "workspace/model"
            confidence_threshold: float, default 0.1
            iou_threshold: float, default 0.5
            crop_size: int, default 640
            overlap: int, default 32
            output_predictions_path: MinIO path to write a JSON array of
                predictions (optional; default omits upload and just
                returns the summary).
        """
        from gemini.workers.ml.inference_utils import run_inference_on_image

        image_path = parameters["image_path"]
        api_key = parameters["api_key"]
        model_id = parameters["model_id"]
        confidence_threshold = float(parameters.get("confidence_threshold", 0.1))
        iou_threshold = float(parameters.get("iou_threshold", 0.5))
        crop_size = int(parameters.get("crop_size", 640))
        overlap = int(parameters.get("overlap", 32))
        output_predictions_path = parameters.get("output_predictions_path")

        self.report_progress(job_id, 5, {"stage": "downloading"})
        client = _get_minio_client()
        with tempfile.TemporaryDirectory() as tmpdir:
            local_image = os.path.join(tmpdir, Path(image_path).name)
            client.fget_object(STORAGE_BUCKET, image_path, local_image)

            self.report_progress(
                job_id, 20, {"stage": "inference", "model_id": model_id}
            )
            predictions = run_inference_on_image(
                image_path=local_image,
                api_key=api_key,
                model_id=model_id,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
                crop_size=crop_size,
                overlap=overlap,
            )

            counts_by_class: dict = {}
            for p in predictions:
                cls = p.get("class", "")
                counts_by_class[cls] = counts_by_class.get(cls, 0) + 1

            result: dict = {
                "total_detections": len(predictions),
                "counts_by_class": counts_by_class,
                "model_id": model_id,
            }

            if output_predictions_path:
                self.report_progress(job_id, 90, {"stage": "uploading"})
                local_out = os.path.join(tmpdir, "predictions.json")
                with open(local_out, "w") as f:
                    json.dump(predictions, f)
                client.fput_object(
                    STORAGE_BUCKET, output_predictions_path, local_out
                )
                result["output_predictions_path"] = output_predictions_path
            else:
                # Inline predictions only if small — don't blow up job.result
                # with thousands of detection rows.
                if len(predictions) <= 500:
                    result["predictions"] = predictions

            return result

    # ------------------------------------------------------------------
    # EXTRACT_TRAITS
    # ------------------------------------------------------------------

    def _extract_traits_job(self, job_id: str, parameters: dict) -> dict:
        """Per-plot vegetation-fraction + canopy-height extraction.

        Parameters:
            orthomosaic_path: MinIO path to the RGB GeoTIFF
            boundary_geojson_path: MinIO path to plot-boundary GeoJSON
            dem_path: MinIO path to DEM GeoTIFF (optional; height skipped
                if absent)
            exg_threshold: float, default 0.1
            output_traits_geojson_path: MinIO path to write the traits
                GeoJSON (required)
        """
        from gemini.workers.ml.trait_extraction import extract_traits_from_ortho

        rgb_path = parameters["orthomosaic_path"]
        boundary_path = parameters["boundary_geojson_path"]
        dem_path = parameters.get("dem_path")
        exg_threshold = float(parameters.get("exg_threshold", 0.1))
        output_path = parameters["output_traits_geojson_path"]

        client = _get_minio_client()
        with tempfile.TemporaryDirectory() as tmpdir:
            self.report_progress(job_id, 5, {"stage": "downloading"})
            local_rgb = os.path.join(tmpdir, "ortho.tif")
            local_boundary = os.path.join(tmpdir, "boundary.geojson")
            client.fget_object(STORAGE_BUCKET, rgb_path, local_rgb)
            client.fget_object(STORAGE_BUCKET, boundary_path, local_boundary)

            local_dem = None
            if dem_path:
                local_dem = os.path.join(tmpdir, "dem.tif")
                client.fget_object(STORAGE_BUCKET, dem_path, local_dem)

            self.report_progress(job_id, 30, {"stage": "extracting traits"})
            records, geojson_dict = extract_traits_from_ortho(
                rgb_path=local_rgb,
                boundary_geojson_path=local_boundary,
                dem_path=local_dem,
                exg_threshold=exg_threshold,
            )

            self.report_progress(job_id, 90, {"stage": "uploading"})
            local_out = os.path.join(tmpdir, "traits.geojson")
            with open(local_out, "w") as f:
                json.dump(geojson_dict, f)
            client.fput_object(STORAGE_BUCKET, output_path, local_out)

            return {
                "output_traits_geojson_path": output_path,
                "plot_count": len(records),
                "traits": ["Vegetation_Fraction", "Height_95p_meters"]
                if dem_path
                else ["Vegetation_Fraction"],
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MlWorker().run()
