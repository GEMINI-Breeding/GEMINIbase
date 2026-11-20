"""
ML / trait-extraction worker.

Dispatches on job_type:
    - LOCATE_PLANTS  → detection / segmentation / classification on a single
                       image or every plot image, with a Roboflow, Hugging
                       Face or uploaded local-weights model (see
                       inference_utils.ModelSpec). Returns per-detection
                       lists + per-class counts.
    - EXTRACT_TRAITS → ExG vegetation fraction + canopy height per plot,
                       from an orthomosaic (and optional DEM) against a
                       plot-boundary GeoJSON.
    - TRAIN_MODEL    → fine-tune an Ultralytics YOLO model on a labelled set
                       (COCO JSON in storage), from an app checkpoint or
                       uploaded weights (training.py). Fast on a GPU worker;
                       on a CPU it is capped at 40 epochs.

Inputs/outputs are exchanged via MinIO: the caller submits MinIO object
paths in ``parameters``; the worker downloads, processes, uploads
result artifacts, and returns the result paths on the job record.
"""
from __future__ import annotations
from gemini.workers.plot_ids import normalize_plot_number

import hashlib
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
# Persistent volume for downloaded models (uploaded weights; HF Hub models
# go to HF_HOME, which the image points inside it too).
MODEL_CACHE_DIR = os.environ.get("GEMINI_MODEL_CACHE_DIR", "/models")


def _download_weights(client, object_path: str) -> str:
    """Local path of an uploaded weights file, downloading it once.

    Cached under the object's ETag, so re-uploading different weights to
    the same path is picked up, while repeat runs skip the download.
    """
    from gemini.workers.ml.inference_utils import InferenceConfigError

    try:
        stat = client.stat_object(STORAGE_BUCKET, object_path)
    except Exception as e:  # noqa: BLE001 — minio raises S3Error for a missing key
        raise InferenceConfigError(
            f"Weights file '{object_path}' wasn't found in storage. Upload it "
            "again from the pipeline's model settings."
        ) from e
    etag = (stat.etag or "noetag").strip('"')
    key = hashlib.sha1(object_path.encode()).hexdigest()[:16]
    dest_dir = Path(MODEL_CACHE_DIR) / "weights" / key / etag[:16]
    dest = dest_dir / Path(object_path).name
    if dest.exists():
        return str(dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    client.fget_object(STORAGE_BUCKET, object_path, str(part))
    os.replace(part, dest)
    return str(dest)


def _resolve_model_spec(client, parameters: dict):
    """ModelSpec for a LOCATE_PLANTS job, with uploaded weights downloaded."""
    from gemini.workers.ml.inference_utils import ModelSpec

    spec = ModelSpec.from_params(parameters)
    spec.validate()  # fail on bad config before downloading anything
    if spec.source == "local_weights":
        spec.weights_path = _download_weights(client, spec.weights_path)
    elif spec.is_sam3:
        spec.weights_path = _sam3_weights(client, spec.api_key)
    return spec


def _sam3_weights(client, token=None, progress=None) -> str:
    """SAM 3's weights: cached, or uploaded to storage, or from Hugging Face."""
    from gemini.workers.ml import zero_shot

    def fetch(object_path: str, dest: str) -> bool:
        client.stat_object(STORAGE_BUCKET, object_path)
        client.fget_object(STORAGE_BUCKET, object_path, dest)
        return True

    return zero_shot.sam3_weights(token, fetch, progress)


def _predict(spec, image_path: str, parameters: dict) -> list:
    """Run the job's model on one local image."""
    from gemini.workers.ml.inference_utils import (
        run_classification_on_image,
        run_inference_on_image,
    )

    if spec.task_type == "classification":
        return run_classification_on_image(
            image_path, spec, top_k=int(parameters.get("top_k", 5))
        )
    return run_inference_on_image(
        image_path=image_path,
        confidence_threshold=float(parameters.get("confidence_threshold", 0.1)),
        iou_threshold=float(parameters.get("iou_threshold", 0.5)),
        crop_size=int(parameters.get("crop_size", 640)),
        overlap=int(parameters.get("overlap", 32)),
        spec=spec,
    )


def _class_counts(predictions: list, task_type: str) -> dict:
    """Per-class counts. A classification result counts its top class once."""
    if task_type == "classification":
        top = predictions[0]["class"] if predictions else None
        return {top: 1} if top is not None else {}
    counts: dict = {}
    for p in predictions:
        cls = p.get("class", "")
        counts[cls] = counts.get(cls, 0) + 1
    return counts


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
            return self._train_model_job(job_id, parameters)
        raise ValueError(f"Unsupported job type: {job_type}")

    # ------------------------------------------------------------------
    # LOCATE_PLANTS
    # ------------------------------------------------------------------

    def _locate_plants_job(self, job_id: str, parameters: dict) -> dict:
        """Model inference on one image, or on every plot image.

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
            source: "roboflow" (default) | "huggingface" | "local_weights"
            task_type: "detection" (default) | "segmentation" | "classification"
            api_key: Roboflow API key (roboflow)
            model_id: "workspace/model/version" or "workspace/model" (roboflow)
            api_url: self-hosted Roboflow inference server (roboflow, optional)
            weights_path: MinIO path of an uploaded .pt/.onnx (local_weights)
            hf_model_id: Hub repo id, e.g. "facebook/detr-resnet-50" (huggingface)
            hf_token: HF access token (huggingface; required for cloud mode,
                needed locally only for gated models). Falls back to the
                worker's HF_TOKEN environment variable.
            hf_mode: "local" (in this worker, default) | "cloud" (HF router)
            hf_zero_shot / hf_prompt: zero-shot detection/classification with
                comma-separated candidate labels
            top_k: classification results kept per image, default 5
            confidence_threshold: float, default 0.1
            iou_threshold: float, default 0.5
            crop_size: int, default 640
            overlap: int, default 32
            output_predictions_path: MinIO path to write a JSON array of
                predictions (optional; default omits upload and just
                returns the summary). In batch mode this receives the
                per-plot mapping instead.
        """
        if parameters.get("recount"):
            return self._recount_batch(job_id, parameters)
        if parameters.get("images_prefix") and not parameters.get("image_path"):
            return self._locate_plants_batch(job_id, parameters)

        image_path = parameters.get("image_path")
        output_predictions_path = parameters.get("output_predictions_path")

        # Labelling in the app: an example box/point → objects and masks
        # (see prompted.py). No model spec; the predictions come back inline.
        if parameters.get("prompted"):
            from gemini.workers.ml import prompted as prompted_models

            p = dict(parameters["prompted"])

            def progress(frac: float, stage: str) -> None:
                self.report_progress(job_id, round(5 + 85 * frac, 1), {"stage": stage})

            if p.get("mode") == "warmup":
                self.report_progress(job_id, 2, {"stage": "Worker started; checking models"})
                return {"prompted": "warmup", **prompted_models.warmup(progress)}

            client = _get_minio_client()
            if p.get("mode") == "describe":
                return self._describe(job_id, client, image_path, p, progress)
            with tempfile.TemporaryDirectory() as tmpdir:
                local_image = os.path.join(tmpdir, Path(image_path).name)
                client.fget_object(STORAGE_BUCKET, image_path, local_image)
                refer_local = None
                if p.get("refer_image") and p["refer_image"] != image_path:
                    refer_local = os.path.join(tmpdir, "refer_" + Path(p["refer_image"]).name)
                    client.fget_object(STORAGE_BUCKET, p["refer_image"], refer_local)
                self.report_progress(job_id, 30, {"stage": f"prompted {p.get('mode')}"})
                predictions = prompted_models.run(local_image, p, refer_local, progress)
            return {"prompted": p.get("mode"), "total_detections": len(predictions),
                    "predictions": predictions}

        self.report_progress(job_id, 5, {"stage": "downloading"})
        client = _get_minio_client()
        spec = _resolve_model_spec(client, parameters)
        with tempfile.TemporaryDirectory() as tmpdir:
            local_image = os.path.join(tmpdir, Path(image_path).name)
            client.fget_object(STORAGE_BUCKET, image_path, local_image)

            self.report_progress(
                job_id, 20, {"stage": "inference", "model_id": spec.display_id}
            )
            predictions = _predict(spec, local_image, parameters)
            counts_by_class = _class_counts(predictions, spec.task_type)

            result: dict = {
                "total_detections": len(predictions),
                "counts_by_class": counts_by_class,
                "model_id": spec.display_id,
                "source": spec.source,
                "task_type": spec.task_type,
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

    def _train_model_job(self, job_id: str, parameters: dict) -> dict:
        from gemini.workers.ml import prompted, training

        if not parameters.get("coco_path"):
            raise ValueError("TRAIN_MODEL needs coco_path: the labelled set as COCO JSON in storage.")
        client = _get_minio_client()

        def fetch(object_path: str, dest: str) -> None:
            client.fget_object(STORAGE_BUCKET, object_path, dest)

        def upload(local: str, object_path: str) -> None:
            client.fput_object(STORAGE_BUCKET, object_path, local)

        def progress(pct: float, detail: dict) -> None:
            self.report_progress(job_id, round(pct, 1), detail)

        workdir = Path(tempfile.mkdtemp(prefix="gemi-train-"))
        try:
            return training.train(parameters, fetch, upload, progress, workdir,
                                  base_weights=prompted.ensure_weights, job_id=job_id)
        finally:
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)

    def _describe(self, job_id: str, client, image_path: str, p: dict, progress) -> dict:
        """Labelling: every object matching a description on one image, as
        proposals (SAM 3 with outlines by default; OWLv2 without a token).

        ``p``: prompt (one class per line, ``name: description``), model
        ("sam3" | "owlv2" | a Hugging Face id), conf, hf_token."""
        from gemini.workers.ml.inference_utils import ModelSpec, run_inference_on_image

        model = (p.get("model") or "sam3").strip()
        model_id = {"sam3": "facebook/sam3", "owlv2": "google/owlv2-base-patch16-ensemble"}.get(model, model)
        spec = ModelSpec(source="huggingface", task_type="segmentation" if "sam3" in model_id else "detection",
                         model_id=model_id, api_key=p.get("hf_token") or os.environ.get("HF_TOKEN") or None,
                         zero_shot=True, prompt=p.get("prompt") or "")
        spec.validate()
        if spec.is_sam3:
            spec.weights_path = _sam3_weights(client, spec.api_key, progress)
        conf = float(p.get("conf", 0.3 if spec.is_sam3 else 0.1))
        with tempfile.TemporaryDirectory() as tmpdir:
            local_image = os.path.join(tmpdir, Path(image_path).name)
            client.fget_object(STORAGE_BUCKET, image_path, local_image)
            self.report_progress(job_id, 40, {"stage": f"finding: {model}"})
            predictions = run_inference_on_image(local_image, confidence_threshold=conf,
                                                 crop_size=int(p.get("crop_size", 1008 if spec.is_sam3 else 640)),
                                                 spec=spec)
        return {"prompted": "describe", "model_id": model_id, "total_detections": len(predictions),
                "predictions": predictions}

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

        from gemini.workers.ml.inference_utils import (
            InferenceConfigError,
            redact_api_key,
        )

        images_prefix = parameters["images_prefix"]
        # Optional: the plot boundaries the images were split with. When
        # present, per-plot detection counts are written to trait_records
        # so they reach Analyze. Boundaries (not the filenames) supply the
        # row/col the populate_trait_record_ids trigger needs to resolve a
        # plot — the PNG name only carries the plot number.
        boundaries = parameters.get("boundaries")
        output_predictions_path = parameters.get("output_predictions_path")

        client = _get_minio_client()
        spec = _resolve_model_spec(client, parameters)
        model_id = spec.display_id
        count_label = parameters.get("count_label") or model_id
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
            # plot_12_accession_X.png → "12"; plot_KD18_accession_X.png → "KD18".
            m = re.match(r"^plot_(.+?)(?:_accession_.*)?\.[A-Za-z0-9]+$", base)
            return m.group(1) if m else base

        by_plot: dict = {}
        counts_by_class: dict = {}
        errors: dict = {}
        total_detections = 0
        # A ground track's raw frames (…/PlotFrames/tiles/): several frames
        # per plot that do not overlap, so the plot's count is their sum.
        # Elsewhere several images of a plot are views of the same ground
        # (the raw frames' crops), and the first one counts.
        sum_per_plot = bool(parameters.get("sum_per_plot")) or "/PlotFrames/tiles/" in images_prefix

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
                # Several images of one plot (the raw frames' crops, best
                # frame first in name order): the first that infers counts —
                # unless they are tiles of a ground track, which add up.
                if key in by_plot and not (sum_per_plot and spec.task_type != "classification"):
                    continue
                local_image = os.path.join(tmpdir, f"{idx}_{Path(object_name).name}")
                try:
                    client.fget_object(STORAGE_BUCKET, object_name, local_image)
                    predictions = _predict(spec, local_image, parameters)
                except InferenceConfigError:
                    # Bad key / model / weights fails every image the same
                    # way — stop now instead of repeating it per plot.
                    raise
                except Exception as e:  # noqa: BLE001 — one plot must not sink the run
                    # A failed image goes to `errors`, never to by_plot, so
                    # no count (let alone 0) is recorded for it.
                    err = redact_api_key(e)
                    logger.warning("LOCATE_PLANTS failed for %s: %s", object_name, err)
                    errors[key] = err
                    continue
                finally:
                    if os.path.exists(local_image):
                        os.remove(local_image)

                per_class = _class_counts(predictions, spec.task_type)
                for cls, n in per_class.items():
                    counts_by_class[cls] = counts_by_class.get(cls, 0) + n

                total_detections += len(predictions)
                if key in by_plot:
                    # Another tile of the same plot: add its detections.
                    hit = by_plot[key]
                    hit["count"] += len(predictions)
                    for cls, n in per_class.items():
                        hit["counts_by_class"][cls] = hit["counts_by_class"].get(cls, 0) + n
                    hit["predictions"].extend({**pr, "image": object_name} for pr in predictions)
                    hit["images"] += 1
                    continue
                by_plot[key] = {
                    "object_name": object_name,
                    "count": len(predictions),
                    "counts_by_class": dict(per_class),
                    "predictions": [{**pr, "image": object_name} for pr in predictions]
                    if sum_per_plot else predictions,
                    "images": 1,
                }
                if spec.task_type == "classification":
                    by_plot[key]["top_class"] = (
                        predictions[0]["class"] if predictions else None
                    )
                    by_plot[key]["scores"] = {
                        p["class"]: p["confidence"] for p in predictions
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
                "source": spec.source,
                "task_type": spec.task_type,
                "plots_processed": len(by_plot),
                "images_found": len(image_names),
                "total_detections": total_detections,
                "counts_by_class": counts_by_class,
                # Per-plot counts always; the detection boxes only when
                # they'd fit in job.result without bloating it.
                "counts_by_plot": {k: v["count"] for k, v in by_plot.items()},
            }
            if sum_per_plot:
                result["summed_over_tiles"] = {k: v["images"] for k, v in by_plot.items()}
            if errors:
                result["errors"] = errors

            if boundaries and output_predictions_path:
                self.report_progress(job_id, 90, {"stage": "ingesting_counts"})
                if spec.task_type == "classification":
                    classes = sorted(
                        {c for hit in by_plot.values() for c in hit.get("scores", {})}
                    )
                    result["ingested"] = self._ingest_class_scores(
                        boundaries=boundaries,
                        by_plot=by_plot,
                        classes=classes,
                        label=count_label,
                        output_path=output_predictions_path,
                        run_id=job_id,
                    )
                else:
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

    def _recount_batch(self, job_id: str, parameters: dict) -> dict:
        """Count a finished run's detections again at another confidence
        threshold, and put those counts in Analyze in place of the run's.

        No model runs: the run's predictions file (``output_predictions_path``)
        already holds every detection at or above the threshold it ran with,
        so a higher threshold only drops some. The trait names stay the run's
        (the classes come from all its detections, not just the kept ones),
        and ingesting replaces the earlier records of that flight and model.

        Parameters: ``output_predictions_path``, ``boundaries``,
        ``confidence_threshold``, ``count_label``, ``task_type``.
        """
        path = parameters.get("output_predictions_path")
        boundaries = parameters.get("boundaries")
        label = parameters.get("count_label")
        if not path or not boundaries or not label:
            raise ValueError(
                "A recount needs the run's output_predictions_path, "
                "boundaries and count_label."
            )
        task_type = parameters.get("task_type") or "detection"
        if task_type == "classification":
            raise ValueError("Classification results have no count to redo.")
        threshold = float(parameters.get("confidence_threshold") or 0)

        client = _get_minio_client()
        self.report_progress(job_id, 10, {"stage": "reading predictions"})
        resp = client.get_object(STORAGE_BUCKET, path)
        try:
            saved = json.loads(resp.read())
        finally:
            resp.close()
            resp.release_conn()
        if not isinstance(saved, dict):
            raise ValueError(f"{path} isn't a per-plot predictions file.")

        classes: set = set()
        by_plot: dict = {}
        counts_by_class: dict = {}
        total = 0
        for key, hit in saved.items():
            preds = (hit or {}).get("predictions") or []
            classes.update(p.get("class", "") for p in preds)
            kept = [p for p in preds if float(p.get("confidence", 0)) >= threshold]
            per_class = _class_counts(kept, task_type)
            for cls, n in per_class.items():
                counts_by_class[cls] = counts_by_class.get(cls, 0) + n
            total += len(kept)
            by_plot[key] = {"count": len(kept), "counts_by_class": per_class}

        self.report_progress(job_id, 60, {"stage": "ingesting_counts"})
        ingested = self._ingest_detection_counts(
            boundaries=boundaries,
            by_plot=by_plot,
            classes=sorted(classes),
            label=label,
            output_path=path,
            run_id=job_id,
        )
        return {
            "recount": True,
            "recount_of": parameters.get("recount_of"),
            "confidence_threshold": threshold,
            "model_id": parameters.get("model_id") or label,
            "task_type": task_type,
            "plots_processed": len(by_plot),
            "total_detections": total,
            "counts_by_class": counts_by_class,
            "counts_by_plot": {k: v["count"] for k, v in by_plot.items()},
            "output_predictions_path": path,
            "ingested": ingested,
            "dataset_name": _run_dataset_name("LOCATE_PLANTS", path, job_id, label),
        }

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

        With a single class the total and that class's count are the same
        number; writing both made two traits that always agree (a perfect,
        meaningless correlation in Analyze), so only the class count is
        written. The total is kept when there are several classes, or none
        (nothing detected anywhere, so no class to name).
        """
        from gemini.workers.ml.trait_ingest import ingest_trait_features

        class_cols = {c: f"{c} count ({label})" for c in classes if c}
        total_col = None if len(class_cols) == 1 else f"detections ({label})"

        features = []
        for feat in (boundaries or {}).get("features", []) or []:
            if not isinstance(feat, dict):
                continue
            props = dict(feat.get("properties") or {})
            raw = props.get("plot_number", props.get("plot", props.get("Plot")))
            n = normalize_plot_number(raw)   # 12, or a named plot ("KW1")
            if n is None:
                continue
            key = str(n)
            hit = by_plot.get(key)
            if hit is None:
                continue  # errored or no image — no measurement, no record
            if total_col:
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
            trait_columns=([(total_col, "count")] if total_col else [])
            + [(col, "count") for col in class_cols.values()],
            source="LOCATE_PLANTS",
            run_id=run_id,
            label=label,
        )

    def _ingest_class_scores(
        self,
        *,
        boundaries: dict,
        by_plot: dict,
        classes: list,
        label: str,
        output_path: str,
        run_id: Optional[str] = None,
    ) -> dict:
        """Write per-plot classification scores into trait_records.

        One trait per class (`"<class> score (<label>)"`), the model's
        confidence for that class on the plot image. Only the top-k classes
        come back per image, so a class outside a plot's top-k gets no
        record — its score is unknown, not 0.
        """
        from gemini.workers.ml.trait_ingest import ingest_trait_features

        class_cols = {c: f"{c} score ({label})" for c in classes if c}

        features = []
        for feat in (boundaries or {}).get("features", []) or []:
            if not isinstance(feat, dict):
                continue
            props = dict(feat.get("properties") or {})
            raw = props.get("plot_number", props.get("plot", props.get("Plot")))
            n = normalize_plot_number(raw)   # 12, or a named plot ("KW1")
            if n is None:
                continue
            key = str(n)
            hit = by_plot.get(key)
            if hit is None:
                continue
            for cls, col in class_cols.items():
                if cls in hit.get("scores", {}):
                    props[col] = hit["scores"][cls]
            features.append({**feat, "properties": props})

        if not features or not class_cols:
            return {}
        return ingest_trait_features(
            self._http,
            output_path=output_path,
            geojson={"type": "FeatureCollection", "features": features},
            trait_columns=[(col, "score") for col in class_cols.values()],
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
        # Cancelled from the app: stop at the next stage, and never save the
        # records of a run the person called off.
        stopped = {"status": "cancelled", "output_traits_geojson_path": output_path}
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

            if self.is_cancelled(job_id):
                return stopped
            self.report_progress(job_id, 30, {"stage": "extracting traits"})
            records, geojson_dict = extract_traits_from_ortho(
                rgb_path=local_rgb,
                boundary_geojson_path=local_boundary,
                dem_path=local_dem,
                exg_threshold=exg_threshold,
                thermal_path=local_thermal,
            )

            if self.is_cancelled(job_id):
                return stopped
            self.report_progress(job_id, 80, {"stage": "uploading"})
            local_out = os.path.join(tmpdir, "traits.geojson")
            with open(local_out, "w") as f:
                json.dump(geojson_dict, f)
            client.fput_object(STORAGE_BUCKET, output_path, local_out)

            # Auto-ingest the per-plot values into `trait_records` so the
            # analyze map (and any downstream consumer) can see them
            # alongside manually-imported traits without a separate "load
            # extracted traits into DB" step. A failure fails the job: it
            # used to be swallowed into result["ingest_error"], which no UI
            # reads, so a run that saved nothing showed as COMPLETED.
            if self.is_cancelled(job_id):
                return stopped
            self.report_progress(job_id, 92, {"stage": "ingesting"})
            from gemini.workers.ml.trait_ingest import ingest_extracted_traits

            ingested_counts = ingest_extracted_traits(
                self._http,
                output_path=output_path,
                geojson=geojson_dict,
                run_id=job_id,
                label=parameters.get("dataset_label"),
            )

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
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MlWorker().run()
