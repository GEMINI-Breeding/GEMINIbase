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
from typing import Optional, Set

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



def _run_dataset_name(source, output_path, job_id, label=None):
    """The dataset a run's records went into (for the job result), or None."""
    from gemini.workers.ml.trait_ingest import (
        parse_scope_from_output_path,
        run_dataset_name,
    )

    scope = parse_scope_from_output_path(output_path)
    return run_dataset_name(source, scope, job_id, label) if scope else None

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
        """Roboflow cloud inference on one image, or on every plot image.

        Two modes, chosen by which parameter is supplied:

        * ``image_path`` — a single PNG/JPEG. Returns the detections for
          that image.
        * ``images_prefix`` — a MinIO prefix (typically a ``PlotImages/``
          directory written by SPLIT_ORTHOMOSAIC). Every image under it is
          inferred in one job, and the result is keyed by plot number.

        The prefix mode exists because the alternative — the client
        submitting one job per plot — means hundreds of jobs for a single
        field, each paying container + model startup. The old backend
        looped server-side for the same reason.

        Parameters:
            image_path: MinIO object path to a PNG/JPEG (single mode)
            images_prefix: MinIO prefix to infer over (batch mode)
            api_key: Roboflow API key (string)
            model_id: "workspace/model/version" or "workspace/model"
            confidence_threshold: float, default 0.1
            iou_threshold: float, default 0.5
            crop_size: int, default 640
            overlap: int, default 32
            output_predictions_path: MinIO path to write a JSON array of
                predictions (optional; default omits upload and just
                returns the summary). In batch mode this receives the
                per-plot mapping instead.
        """
        from gemini.workers.ml.inference_utils import run_inference_on_image

        if parameters.get("images_prefix") and not parameters.get("image_path"):
            return self._locate_plants_batch(job_id, parameters)

        image_path = parameters["image_path"]
        api_key = parameters["api_key"]
        model_id = parameters["model_id"]
        confidence_threshold = float(parameters.get("confidence_threshold", 0.1))
        iou_threshold = float(parameters.get("iou_threshold", 0.5))
        crop_size = int(parameters.get("crop_size", 640))
        overlap = int(parameters.get("overlap", 32))
        output_predictions_path = parameters.get("output_predictions_path")
        # Self-hosted Roboflow inference server; None = Roboflow cloud.
        api_url = parameters.get("api_url")

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
                api_url=api_url,
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

    def _locate_plants_batch(self, job_id: str, parameters: dict) -> dict:
        """Run inference over every image under ``images_prefix``.

        Keyed by plot number parsed from the SPLIT_ORTHOMOSAIC naming
        scheme (``plot_{n}_accession_{name}.png``). Images whose names
        don't carry a plot number are still inferred, keyed by basename,
        so a non-standard directory degrades rather than silently
        dropping work.

        One bad image must not lose the whole run — a per-image failure is
        recorded against that plot and the loop continues. `errors` in the
        result is how the caller tells "0 detections" from "never ran".
        """
        import re

        from gemini.workers.ml.inference_utils import run_inference_on_image

        images_prefix = parameters["images_prefix"]
        # Optional: the plot boundaries the images were split with. When
        # present, per-plot detection counts are written to trait_records
        # so they reach Analyze. Boundaries (not the filenames) supply the
        # row/col the populate_trait_record_ids trigger needs to resolve a
        # plot — the PNG name only carries the plot number.
        boundaries = parameters.get("boundaries")
        count_label = parameters.get("count_label") or parameters["model_id"]
        api_key = parameters["api_key"]
        model_id = parameters["model_id"]
        confidence_threshold = float(parameters.get("confidence_threshold", 0.1))
        iou_threshold = float(parameters.get("iou_threshold", 0.5))
        crop_size = int(parameters.get("crop_size", 640))
        overlap = int(parameters.get("overlap", 32))
        output_predictions_path = parameters.get("output_predictions_path")
        # Self-hosted Roboflow inference server; None = Roboflow cloud.
        api_url = parameters.get("api_url")

        client = _get_minio_client()
        self.report_progress(job_id, 2, {"stage": "listing", "prefix": images_prefix})

        image_names: list[str] = []
        for obj in client.list_objects(
            STORAGE_BUCKET, prefix=images_prefix, recursive=True
        ):
            name = obj.object_name or ""
            if re.search(r"\.(png|jpe?g)$", name, re.IGNORECASE):
                image_names.append(name)
        image_names.sort()

        if not image_names:
            return {
                "images_prefix": images_prefix,
                "plots_processed": 0,
                "total_detections": 0,
                "error": f"No images found under {images_prefix}",
            }

        def _plot_key(object_name: str) -> str:
            base = object_name.rsplit("/", 1)[-1]
            m = re.match(r"^plot_(\d+)(?:_|\.)", base)
            return m.group(1) if m else base

        by_plot: dict = {}
        counts_by_class: dict = {}
        errors: dict = {}
        total_detections = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, object_name in enumerate(image_names):
                if self.is_cancelled(job_id):
                    return {"status": "cancelled"}

                pct = 5 + int(85 * idx / len(image_names))
                self.report_progress(
                    job_id,
                    pct,
                    {
                        "stage": "inference",
                        "image": idx + 1,
                        "of": len(image_names),
                        "model_id": model_id,
                    },
                )

                key = _plot_key(object_name)
                local_image = os.path.join(tmpdir, f"{idx}_{Path(object_name).name}")
                try:
                    client.fget_object(STORAGE_BUCKET, object_name, local_image)
                    predictions = run_inference_on_image(
                        image_path=local_image,
                        api_key=api_key,
                        model_id=model_id,
                        confidence_threshold=confidence_threshold,
                        iou_threshold=iou_threshold,
                        crop_size=crop_size,
                        overlap=overlap,
                        api_url=api_url,
                    )
                except Exception as e:  # noqa: BLE001 — one plot must not sink the run
                    logger.warning("LOCATE_PLANTS failed for %s: %s", object_name, e)
                    errors[key] = str(e)
                    continue
                finally:
                    if os.path.exists(local_image):
                        os.remove(local_image)

                per_class: dict = {}
                for pred in predictions:
                    cls = pred.get("class", "")
                    per_class[cls] = per_class.get(cls, 0) + 1
                    counts_by_class[cls] = counts_by_class.get(cls, 0) + 1

                total_detections += len(predictions)
                by_plot[key] = {
                    "object_name": object_name,
                    "count": len(predictions),
                    "counts_by_class": per_class,
                    "predictions": predictions,
                }

            # Every image failing is a failed job, not a job that found
            # nothing. Reporting COMPLETED here would show a green tick for
            # a run that inferred nothing at all — e.g. a bad API key fails
            # identically on every image.
            if errors and not by_plot:
                raise RuntimeError(
                    f"LOCATE_PLANTS failed on all {len(image_names)} images "
                    f"under {images_prefix}. First error: "
                    f"{next(iter(errors.values()))}"
                )

            result: dict = {
                "images_prefix": images_prefix,
                "model_id": model_id,
                "plots_processed": len(by_plot),
                "images_found": len(image_names),
                "total_detections": total_detections,
                "counts_by_class": counts_by_class,
                # Per-plot counts always; the detection boxes only when
                # they'd fit in job.result without bloating it.
                "counts_by_plot": {k: v["count"] for k, v in by_plot.items()},
            }
            if errors:
                result["errors"] = errors

            if boundaries and output_predictions_path:
                self.report_progress(job_id, 90, {"stage": "ingesting_counts"})
                result["ingested"] = self._ingest_detection_counts(
                    boundaries=boundaries,
                    by_plot=by_plot,
                    classes=sorted(counts_by_class),
                    label=count_label,
                    output_path=output_predictions_path,
                    run_id=job_id,
                )
                result["dataset_name"] = _run_dataset_name(
                    "LOCATE_PLANTS", output_predictions_path, job_id, count_label
                )

            if output_predictions_path:
                self.report_progress(job_id, 92, {"stage": "uploading"})
                local_out = os.path.join(tmpdir, "predictions_by_plot.json")
                with open(local_out, "w") as f:
                    json.dump(by_plot, f)
                client.fput_object(
                    STORAGE_BUCKET, output_predictions_path, local_out
                )
                result["output_predictions_path"] = output_predictions_path
            elif total_detections <= 500:
                result["predictions_by_plot"] = by_plot

            return result

    def _ingest_detection_counts(
        self,
        *,
        boundaries: dict,
        by_plot: dict,
        classes: list,
        label: str,
        output_path: str,
        run_id: Optional[str] = None,
    ) -> dict:
        """Write per-plot detection counts into trait_records.

        One trait per class (`"<class> count (<label>)"`) plus a total
        (`"detections (<label>)"`). The label disambiguates models: two
        detectors can both emit "plant", and their counts are different
        measurements.

        A plot that was inferred and had no detections gets 0 — that IS a
        measurement. A plot that errored or had no image gets NO record:
        writing 0 there would claim "we looked and found nothing" for a plot
        nobody looked at.
        """
        from gemini.workers.ml.trait_ingest import ingest_trait_features

        total_col = f"detections ({label})"
        class_cols = {c: f"{c} count ({label})" for c in classes if c}

        features = []
        for feat in (boundaries or {}).get("features", []) or []:
            if not isinstance(feat, dict):
                continue
            props = dict(feat.get("properties") or {})
            raw = props.get("plot_number", props.get("plot", props.get("Plot")))
            try:
                key = str(int(float(raw)))
            except (TypeError, ValueError):
                continue
            hit = by_plot.get(key)
            if hit is None:
                continue  # errored or no image — no measurement, no record
            props[total_col] = hit["count"]
            for cls, col in class_cols.items():
                props[col] = hit["counts_by_class"].get(cls, 0)
            features.append({**feat, "properties": props})

        if not features:
            return {}
        return ingest_trait_features(
            self._http,
            output_path=output_path,
            geojson={"type": "FeatureCollection", "features": features},
            trait_columns=[(total_col, "count")]
            + [(col, "count") for col in class_cols.values()],
            source="LOCATE_PLANTS",
            run_id=run_id,
            label=label,
        )

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
            thermal_path: MinIO path to a thermal orthomosaic in °C
                (optional; canopy temperature skipped if absent)
            exg_threshold: float, default 0.1
            output_traits_geojson_path: MinIO path to write the traits
                GeoJSON (required)
        """
        from gemini.workers.ml.trait_extraction import extract_traits_from_ortho

        rgb_path = parameters["orthomosaic_path"]
        boundary_path = parameters["boundary_geojson_path"]
        dem_path = parameters.get("dem_path")
        thermal_path = parameters.get("thermal_path")
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

            local_thermal = None
            if thermal_path:
                local_thermal = os.path.join(tmpdir, "thermal.tif")
                client.fget_object(STORAGE_BUCKET, thermal_path, local_thermal)

            self.report_progress(job_id, 30, {"stage": "extracting traits"})
            records, geojson_dict = extract_traits_from_ortho(
                rgb_path=local_rgb,
                boundary_geojson_path=local_boundary,
                dem_path=local_dem,
                exg_threshold=exg_threshold,
                thermal_path=local_thermal,
            )

            self.report_progress(job_id, 80, {"stage": "uploading"})
            local_out = os.path.join(tmpdir, "traits.geojson")
            with open(local_out, "w") as f:
                json.dump(geojson_dict, f)
            client.fput_object(STORAGE_BUCKET, output_path, local_out)

            # Auto-ingest the per-plot values into `trait_records` so the
            # analyze map (and any downstream consumer) can see them
            # alongside manually-imported traits without a separate "load
            # extracted traits into DB" step. Failures here are non-fatal:
            # the GeoJSON is already in MinIO, so the user can re-run
            # ingest later via the backfill flow. The error is surfaced
            # in the result dict so the UI can call it out.
            self.report_progress(job_id, 92, {"stage": "ingesting"})
            from gemini.workers.ml.trait_ingest import ingest_extracted_traits

            try:
                ingested_counts = ingest_extracted_traits(
                    self._http,
                    output_path=output_path,
                    geojson=geojson_dict,
                    run_id=job_id,
                )
                ingest_error = None
            except Exception as e:
                logger.error(
                    f"Trait ingest raised for job {job_id}: {e}"
                )
                ingested_counts = {}
                ingest_error = str(e)

            return {
                "output_traits_geojson_path": output_path,
                "plot_count": len(records),
                "traits": ["Vegetation_Fraction"]
                + (["Height_95p_meters"] if dem_path else [])
                + (["Temp_veg_avg_C"] if thermal_path else []),
                "ingested_counts": ingested_counts,
                "dataset_name": _run_dataset_name(
                    "EXTRACT_TRAITS", output_path, job_id
                ),
                **({"ingest_error": ingest_error} if ingest_error else {}),
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MlWorker().run()
