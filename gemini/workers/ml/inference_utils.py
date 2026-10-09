"""
Inference helpers for the ML worker, ported from the pre-migration FastAPI
backend (main:backend/app/processing/inference_utils.py).

Model sources (``ModelSpec.source``):
    roboflow       Roboflow cloud, or a self-hosted Roboflow inference
                   server reached over HTTP (``api_url``).
    local_weights  An Ultralytics checkpoint (``.pt``, or an ``.onnx``
                   exported by Ultralytics) the user uploaded to MinIO; the
                   worker downloads it and passes the local path here.
    huggingface    A Hugging Face Hub model, run in this container with a
                   ``transformers`` pipeline (``hf_mode="local"``) or through
                   HF's hosted inference router (``hf_mode="cloud"``).
                   Zero-shot (prompted) detection/classification models are
                   supported via ``zero_shot`` + ``prompt``.

Task types: detection, segmentation (tiled + NMS-merged, image-level
coordinates) and classification (whole image, no tiling).

Every backend returns the same prediction shape:
    {"class", "confidence", "x"?, "y"?, "width"?, "height"?, "points"?}
with ``x``/``y`` the box centre; classification predictions carry no
geometry.

Public functions:
    crop_image_with_overlap(image_path, crop_size=640, overlap=32)
    apply_nms(predictions, iou_threshold=0.5)
    run_inference_on_image(image_path, api_key, model_id, ..., spec=None)
    run_classification_on_image(image_path, spec, top_k=5)
"""
from __future__ import annotations

import base64
import io
import logging
import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)

CLOUD_API_URL = "https://detect.roboflow.com"
# HF's serverless inference. The old api-inference.huggingface.co host was
# decommissioned; huggingface_hub itself now routes through this URL.
HF_ROUTER_URL = "https://router.huggingface.co/hf-inference/models"

SOURCES = ("roboflow", "local_weights", "huggingface")
TASK_TYPES = ("detection", "segmentation", "classification")
LOCAL_WEIGHTS_SUFFIXES = (".pt", ".onnx")

# task_type -> Ultralytics model.task
_ULTRALYTICS_TASKS = {
    "detection": "detect",
    "segmentation": "segment",
    "classification": "classify",
}
# (task_type, zero_shot) -> transformers pipeline task. There is no standard
# zero-shot segmentation pipeline.
_HF_PIPELINE_TASKS = {
    ("detection", False): "object-detection",
    ("detection", True): "zero-shot-object-detection",
    ("segmentation", False): "image-segmentation",
    ("classification", False): "image-classification",
    ("classification", True): "zero-shot-image-classification",
}


class InferenceConfigError(RuntimeError):
    """Raised when inference fails due to a config problem (bad API key / model ID).

    The worker surfaces this as a FAILED job with a user-readable error message
    rather than a crash loop.
    """


class InferenceFailedError(RuntimeError):
    """Raised when inference on an image did not actually run.

    E.g. the inference server is down so every crop failed, or the
    consecutive-failure abort fired. Distinct from "ran and found nothing":
    callers must not record a detection count of 0 for such an image.
    """


_API_KEY_RE = re.compile(r"(api_key=)[^&\s'\"]+", re.IGNORECASE)
_HF_TOKEN_RE = re.compile(r"\bhf_[A-Za-z0-9]{8,}")


def redact_api_key(text: Any) -> str:
    """Mask ``api_key=...`` query values and HF tokens in an error message.

    The Roboflow API takes the key as a query parameter, and `requests`
    exception messages embed the full URL — so without this the key ends
    up in worker logs and in job.result["errors"].
    """
    return _HF_TOKEN_RE.sub("hf_***", _API_KEY_RE.sub(r"\1***", str(text)))


@dataclass
class ModelSpec:
    """Which model to run and how — one entry of a pipeline's model list.

    ``model_id`` is the Roboflow model ("workspace/model/version") or the HF
    repo id; ``api_key`` is the Roboflow key or the HF token. For
    ``local_weights``, ``weights_path`` is a local file path (the worker
    downloads the uploaded object first).
    """

    source: str = "roboflow"
    task_type: str = "detection"
    model_id: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    weights_path: Optional[str] = None
    hf_mode: str = "local"
    zero_shot: bool = False
    prompt: Optional[str] = None

    @property
    def labels(self) -> List[str]:
        """Candidate labels for zero-shot models, from the comma-separated prompt."""
        return [s.strip() for s in (self.prompt or "").split(",") if s.strip()]

    @property
    def display_id(self) -> str:
        if self.source == "local_weights":
            return Path(self.weights_path or "weights").name
        return self.model_id or self.source

    def validate(self) -> None:
        """Raise InferenceConfigError for a spec that can't run."""
        if self.source not in SOURCES:
            raise InferenceConfigError(
                f"Unknown model source '{self.source}'. Use one of: {', '.join(SOURCES)}."
            )
        if self.task_type not in TASK_TYPES:
            raise InferenceConfigError(
                f"Unknown task type '{self.task_type}'. Use one of: {', '.join(TASK_TYPES)}."
            )
        if self.source == "roboflow":
            if not self.model_id or not self.api_key:
                raise InferenceConfigError("A Roboflow model needs a model ID and an API key.")
            if self.task_type == "classification":
                raise InferenceConfigError(
                    "Classification isn't supported for Roboflow models yet — "
                    "use a Hugging Face or local-weights classifier."
                )
        elif self.source == "local_weights":
            if not self.weights_path:
                raise InferenceConfigError("A local-weights model needs a weights file.")
            if not self.weights_path.lower().endswith(LOCAL_WEIGHTS_SUFFIXES):
                raise InferenceConfigError(
                    f"Unsupported weights file '{Path(self.weights_path).name}'. "
                    "Use an Ultralytics .pt checkpoint or an .onnx file exported "
                    "by Ultralytics."
                )
        else:  # huggingface
            if not self.model_id:
                raise InferenceConfigError("A Hugging Face model needs a model ID (e.g. facebook/detr-resnet-50).")
            if self.hf_mode not in ("local", "cloud"):
                raise InferenceConfigError("Hugging Face mode must be 'local' or 'cloud'.")
            if (self.task_type, self.zero_shot) not in _HF_PIPELINE_TASKS:
                raise InferenceConfigError(
                    "Zero-shot segmentation isn't supported — Hugging Face has no "
                    "standard zero-shot segmentation pipeline."
                )
            if self.zero_shot and not self.labels:
                raise InferenceConfigError(
                    "A zero-shot model needs a prompt: comma-separated labels, "
                    "e.g. 'weed, crop, soil'."
                )
            if self.hf_mode == "cloud" and not self.api_key:
                raise InferenceConfigError(
                    "Hugging Face cloud inference needs an access token (hf_...)."
                )

    @classmethod
    def from_params(cls, parameters: dict) -> "ModelSpec":
        """Build a spec from LOCATE_PLANTS job parameters.

        Jobs from before multi-source support only carry Roboflow keys
        (`api_key`, `model_id`, `api_url`), so `source` defaults to roboflow.
        For local weights, `weights_path` is still the MinIO object path
        here; the worker swaps in the downloaded file's path.
        """
        source = (parameters.get("source") or "roboflow").strip()
        hf = source == "huggingface"
        return cls(
            source=source,
            task_type=(parameters.get("task_type") or "detection").strip(),
            model_id=(parameters.get("hf_model_id") if hf else parameters.get("model_id")),
            api_key=(
                parameters.get("hf_token") or os.environ.get("HF_TOKEN") or None
                if hf
                else parameters.get("api_key")
            ),
            api_url=parameters.get("api_url") if source == "roboflow" else None,
            weights_path=parameters.get("weights_path"),
            hf_mode=(parameters.get("hf_mode") or "local").strip(),
            zero_shot=bool(parameters.get("hf_zero_shot")),
            prompt=parameters.get("hf_prompt"),
        )


def crop_image_with_overlap(
    image_path: Path | str,
    crop_size: int = 640,
    overlap: int = 32,
) -> List[dict]:
    """Tile a large image into overlapping ``crop_size × crop_size`` patches.

    Returns a list of dicts: ``{crop_id, x_offset, y_offset, width, height,
    crop_path, temp_dir}``. The caller is responsible for deleting
    ``temp_dir``.
    """
    image = Image.open(str(image_path))
    img_w, img_h = image.size

    stride = crop_size - overlap

    def _positions(length: int) -> List[int]:
        pos = list(range(0, length - crop_size + 1, stride))
        if pos and pos[-1] + crop_size < length:
            pos.append(length - crop_size)
        return pos or [0]

    x_positions = _positions(img_w)
    y_positions = _positions(img_h)

    temp_dir = tempfile.mkdtemp(prefix="gemi_crops_")
    crops: List[dict] = []
    crop_id = 0

    for y in y_positions:
        for x in x_positions:
            actual_x = min(x, img_w - crop_size) if img_w >= crop_size else 0
            actual_y = min(y, img_h - crop_size) if img_h >= crop_size else 0
            actual_w = min(crop_size, img_w - actual_x)
            actual_h = min(crop_size, img_h - actual_y)

            crop = image.crop(
                (actual_x, actual_y, actual_x + actual_w, actual_y + actual_h)
            )
            if actual_w < crop_size or actual_h < crop_size:
                padded = Image.new("RGB", (crop_size, crop_size), (255, 255, 255))
                padded.paste(crop, (0, 0))
                crop = padded

            crop_path = str(Path(temp_dir) / f"crop_{crop_id}.jpg")
            crop.save(crop_path, format="JPEG", quality=85)
            crops.append(
                {
                    "crop_id": crop_id,
                    "x_offset": actual_x,
                    "y_offset": actual_y,
                    "width": actual_w,
                    "height": actual_h,
                    "crop_path": crop_path,
                    "temp_dir": temp_dir,
                }
            )
            crop_id += 1

    return crops


def _transform_to_image_coords(predictions: List[dict], crop_info: dict) -> List[dict]:
    result: List[dict] = []
    for p in predictions:
        transformed = {
            "class": p.get("class", ""),
            "confidence": p.get("confidence", 0.0),
            "x": p.get("x", 0) + crop_info["x_offset"],
            "y": p.get("y", 0) + crop_info["y_offset"],
            "width": p.get("width", 0),
            "height": p.get("height", 0),
            "crop_id": crop_info["crop_id"],
        }
        raw_points = p.get("points", [])
        if raw_points:
            transformed["points"] = [
                {"x": pt["x"] + crop_info["x_offset"], "y": pt["y"] + crop_info["y_offset"]}
                for pt in raw_points
            ]
        result.append(transformed)
    return result


def _iou(a: dict, b: dict) -> float:
    ax0, ay0 = a["x"] - a["width"] / 2, a["y"] - a["height"] / 2
    ax1, ay1 = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    bx0, by0 = b["x"] - b["width"] / 2, b["y"] - b["height"] / 2
    bx1, by1 = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union > 0 else 0.0


def apply_nms(predictions: List[dict], iou_threshold: float = 0.5) -> List[dict]:
    if not predictions:
        return []
    by_class: dict[str, List[dict]] = {}
    for p in predictions:
        by_class.setdefault(p["class"], []).append(p)
    kept: List[dict] = []
    for preds in by_class.values():
        preds.sort(key=lambda x: x["confidence"], reverse=True)
        while preds:
            best = preds.pop(0)
            kept.append(best)
            preds = [p for p in preds if _iou(best, p) < iou_threshold]
    return kept


def resolve_inference_api_url(api_url: Optional[str]) -> str:
    """Base URL for the Roboflow-compatible inference API.

    Empty means Roboflow cloud. Otherwise it's a self-hosted Roboflow
    inference server, which serves the same `POST /{model_id}` API.

    `localhost` / `127.0.0.1` are rewritten to `host.docker.internal`.
    The URL is entered by a user thinking of *their* machine ("I started
    the inference server on port 9002"), but this code runs inside the ML
    worker container, where `localhost` is the container itself — so the
    literal URL would always be refused. host.docker.internal is the
    container's name for the host (Docker Desktop provides it; on Linux the
    compose service maps it via extra_hosts: host-gateway).
    """
    if not api_url or not str(api_url).strip():
        return CLOUD_API_URL
    url = str(api_url).strip().rstrip("/")
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    if parts.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
        netloc = "host.docker.internal" + (f":{parts.port}" if parts.port else "")
        url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return url


def _infer_cloud(
    api_key: str,
    model_id: str,
    confidence_threshold: float,
    api_url: Optional[str] = None,
) -> Callable[[str], List[dict]]:
    base = resolve_inference_api_url(api_url)
    endpoint = f"{base}/{model_id}"
    # Reuse a single TLS connection across all crops — a 10k-crop image
    # otherwise triggers 10k handshakes and dominates wall-clock time.
    session = requests.Session()

    def _call(crop_path: str) -> List[dict]:
        with open(crop_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
        resp = session.post(
            endpoint,
            params={"api_key": api_key, "confidence": confidence_threshold},
            data=img_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code == 401:
            raise InferenceConfigError(
                f"Roboflow API returned 401 Unauthorized for model '{model_id}'. "
                "Check your API key."
            )
        if resp.status_code == 404:
            raise InferenceConfigError(
                f"Roboflow model '{model_id}' not found (404). Check the model ID."
            )
        if not resp.ok:
            raise InferenceConfigError(
                f"Roboflow API returned {resp.status_code} for model "
                f"'{model_id}': {resp.text[:200]}"
            )
        if not resp.text:
            raise RuntimeError(
                f"Roboflow returned an empty body (status {resp.status_code})."
            )
        body = resp.json()
        return body.get("predictions", [])

    return _call


# ---------------------------------------------------------------------------
# Model caches — loading a model per image would dominate run time.
# ---------------------------------------------------------------------------

_model_cache: dict = {}
_model_cache_lock = threading.Lock()


def _cached(key: tuple, load: Callable[[], Any]) -> Any:
    with _model_cache_lock:
        if key not in _model_cache:
            _model_cache[key] = load()
        return _model_cache[key]


def _box_from_corners(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"x": (x0 + x1) / 2, "y": (y0 + y1) / 2, "width": x1 - x0, "height": y1 - y0}


def _mask_to_polygon(mask: Any) -> List[dict]:
    """Largest outer contour of a binary mask as [{x, y}, ...] pixel points."""
    import cv2
    import numpy as np

    arr = np.array(mask)
    if arr.ndim == 3:
        arr = arr[..., 0]
    binary = (arr > 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    largest = max(contours, key=cv2.contourArea)
    return [{"x": float(p[0][0]), "y": float(p[0][1])} for p in largest]


def _with_polygon_box(pred: dict, points: List[dict]) -> dict:
    """Attach a polygon and the bounding box NMS needs."""
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return {**pred, **_box_from_corners(min(xs), min(ys), max(xs), max(ys)), "points": points}


# ---------------------------------------------------------------------------
# Local Ultralytics weights (.pt / Ultralytics-exported .onnx)
# ---------------------------------------------------------------------------


def _load_local_weights(weights_path: str, task_type: str) -> Any:
    expected = _ULTRALYTICS_TASKS[task_type]

    def _load():
        try:
            from ultralytics import YOLO, settings
        except ImportError as e:  # pragma: no cover — image always has it
            raise InferenceConfigError(
                "Local weights need the 'ultralytics' package in the ML worker image."
            ) from e
        settings.update({"sync": False})  # no telemetry; the app runs offline
        try:
            # .onnx carries no reliable task metadata; tell Ultralytics.
            model = (
                YOLO(weights_path, task=expected)
                if weights_path.lower().endswith(".onnx")
                else YOLO(weights_path)
            )
        except Exception as e:  # noqa: BLE001
            raise InferenceConfigError(
                f"Could not load weights '{Path(weights_path).name}': {e}. Only "
                "Ultralytics checkpoints (.pt) and .onnx files exported by "
                "Ultralytics are supported."
            ) from e
        if model.task != expected:
            raise InferenceConfigError(
                f"Weights '{Path(weights_path).name}' are a '{model.task}' model, "
                f"but this model is configured for {task_type}. Change the task "
                "type or pick matching weights."
            )
        return model

    return _cached(("local_weights", weights_path, task_type), _load)


def _ultralytics_results_to_predictions(result: Any, task_type: str, top_k: int = 5) -> List[dict]:
    names = result.names or {}
    if task_type == "classification":
        probs = result.probs
        if probs is None:
            return []
        return [
            {"class": str(names.get(int(i), i)), "confidence": float(c)}
            for i, c in zip(probs.top5[:top_k], probs.top5conf.tolist()[:top_k])
        ]
    preds: List[dict] = []
    boxes = result.boxes
    if boxes is None:
        return preds
    polygons = (
        result.masks.xy if task_type == "segmentation" and result.masks is not None else None
    )
    for i, (xywh, cls, conf) in enumerate(
        zip(boxes.xywh.tolist(), boxes.cls.tolist(), boxes.conf.tolist())
    ):
        pred = {
            "class": str(names.get(int(cls), int(cls))),
            "confidence": float(conf),
            "x": float(xywh[0]),
            "y": float(xywh[1]),
            "width": float(xywh[2]),
            "height": float(xywh[3]),
        }
        if polygons is not None and i < len(polygons) and len(polygons[i]):
            pred["points"] = [{"x": float(x), "y": float(y)} for x, y in polygons[i]]
        preds.append(pred)
    return preds


def _infer_local_weights(spec: ModelSpec, confidence_threshold: float) -> Callable[[str], List[dict]]:
    model = _load_local_weights(spec.weights_path, spec.task_type)

    def _call(crop_path: str) -> List[dict]:
        results = model.predict(crop_path, conf=confidence_threshold, verbose=False)
        return _ultralytics_results_to_predictions(results[0], spec.task_type)

    return _call


# ---------------------------------------------------------------------------
# Hugging Face — local transformers pipeline or the hosted router
# ---------------------------------------------------------------------------


def _hf_task(spec: ModelSpec) -> str:
    return _HF_PIPELINE_TASKS[(spec.task_type, spec.zero_shot)]


def _load_hf_pipeline(spec: ModelSpec) -> Any:
    task = _hf_task(spec)

    def _load():
        try:
            from transformers import pipeline
        except ImportError as e:  # pragma: no cover — image always has it
            raise InferenceConfigError(
                "Hugging Face models need the 'transformers' package in the ML worker image."
            ) from e
        try:
            return pipeline(task=task, model=spec.model_id, token=spec.api_key or None, device=-1)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            hint = ""
            if "401" in msg or "gated" in msg.lower() or "403" in msg:
                hint = " The model may be gated — add a Hugging Face token that has access."
            elif "not a valid model identifier" in msg or "404" in msg:
                hint = " Check the model ID."
            raise InferenceConfigError(
                f"Could not load Hugging Face model '{spec.model_id}' as {task}: "
                f"{redact_api_key(msg)[:300]}.{hint}"
            ) from e

    return _cached(("huggingface", spec.model_id, task), _load)


def _hf_outputs_to_predictions(outputs: Any, task_type: str, mask_decoder: Callable[[Any], Any] = None) -> List[dict]:
    """Convert transformers/router outputs to the prediction shape.

    Detection: [{score, label, box: {xmin, ymin, xmax, ymax}}]
    Segmentation: [{score, label, mask}] (PIL image locally, base64 PNG from the router)
    Classification: [{score, label}]
    Zero-shot pipelines return the same shapes as their plain counterparts.
    """
    if isinstance(outputs, dict):
        outputs = [outputs]
    preds: List[dict] = []
    for o in outputs or []:
        label = str(o.get("label", ""))
        score = o.get("score")
        confidence = float(score) if score is not None else 1.0  # semantic seg has no score
        if task_type == "classification":
            preds.append({"class": label, "confidence": confidence})
        elif task_type == "detection":
            b = o.get("box") or {}
            preds.append(
                {
                    "class": label,
                    "confidence": confidence,
                    **_box_from_corners(
                        float(b.get("xmin", 0)), float(b.get("ymin", 0)),
                        float(b.get("xmax", 0)), float(b.get("ymax", 0)),
                    ),
                }
            )
        else:  # segmentation
            mask = o.get("mask")
            if mask_decoder is not None:
                mask = mask_decoder(mask)
            points = _mask_to_polygon(mask) if mask is not None else []
            if len(points) >= 3:
                preds.append(_with_polygon_box({"class": label, "confidence": confidence}, points))
    return preds


def _infer_hf_local(spec: ModelSpec, confidence_threshold: float, top_k: int = 5) -> Callable[[str], List[dict]]:
    pipe = _load_hf_pipeline(spec)

    def _call(image_path: str) -> List[dict]:
        image = Image.open(image_path).convert("RGB")
        if spec.task_type == "classification":
            out = (
                pipe(image, candidate_labels=spec.labels)
                if spec.zero_shot
                else pipe(image, top_k=top_k)
            )
            return _hf_outputs_to_predictions(out, "classification")[:top_k]
        if spec.task_type == "detection":
            out = (
                pipe(image, candidate_labels=spec.labels, threshold=confidence_threshold)
                if spec.zero_shot
                else pipe(image, threshold=confidence_threshold)
            )
            return _hf_outputs_to_predictions(out, "detection")
        out = pipe(image)
        preds = _hf_outputs_to_predictions(out, "segmentation")
        return [p for p in preds if p["confidence"] >= confidence_threshold]

    return _call


def _decode_b64_mask(mask: Any) -> Any:
    if isinstance(mask, str):
        return Image.open(io.BytesIO(base64.b64decode(mask)))
    return mask


def _infer_hf_cloud(spec: ModelSpec, confidence_threshold: float, top_k: int = 5) -> Callable[[str], List[dict]]:
    endpoint = f"{HF_ROUTER_URL}/{spec.model_id}"
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {spec.api_key}"

    def _post(image_path: str) -> Any:
        with open(image_path, "rb") as f:
            raw = f.read()
        for attempt in range(4):
            if spec.zero_shot:
                resp = session.post(
                    endpoint,
                    json={
                        "inputs": base64.b64encode(raw).decode("ascii"),
                        "parameters": {"candidate_labels": spec.labels},
                    },
                    timeout=60,
                )
            else:
                resp = session.post(
                    endpoint, data=raw, headers={"Content-Type": "image/jpeg"}, timeout=60
                )
            if resp.status_code == 503 and attempt < 3:
                # Model is being loaded on HF's side; it reports how long.
                try:
                    wait = float(resp.json().get("estimated_time", 10))
                except ValueError:
                    wait = 10.0
                time.sleep(min(max(wait, 2.0), 30.0))
                continue
            break
        if resp.status_code in (401, 403):
            raise InferenceConfigError(
                f"Hugging Face returned {resp.status_code} for '{spec.model_id}'. "
                "Check the access token and that it can use this model."
            )
        if resp.status_code == 404:
            raise InferenceConfigError(
                f"Hugging Face model '{spec.model_id}' isn't available for hosted "
                "inference (404). Check the model ID, or run it locally instead."
            )
        if not resp.ok:
            raise RuntimeError(
                f"Hugging Face returned {resp.status_code} for '{spec.model_id}': {resp.text[:200]}"
            )
        return resp.json()

    def _call(image_path: str) -> List[dict]:
        out = _post(image_path)
        if spec.task_type == "segmentation":
            preds = _hf_outputs_to_predictions(out, "segmentation", _decode_b64_mask)
        else:
            preds = _hf_outputs_to_predictions(out, spec.task_type)
        if spec.task_type == "classification":
            preds.sort(key=lambda p: p["confidence"], reverse=True)
            return preds[:top_k]
        return [p for p in preds if p["confidence"] >= confidence_threshold]

    return _call


def _make_infer_fn(spec: ModelSpec, confidence_threshold: float) -> Callable[[str], List[dict]]:
    spec.validate()
    if spec.source == "local_weights":
        return _infer_local_weights(spec, confidence_threshold)
    if spec.source == "huggingface":
        if spec.hf_mode == "cloud":
            return _infer_hf_cloud(spec, confidence_threshold)
        return _infer_hf_local(spec, confidence_threshold)
    return _infer_cloud(
        api_key=spec.api_key,
        model_id=spec.model_id,
        confidence_threshold=confidence_threshold,
        api_url=spec.api_url,
    )


def run_classification_on_image(
    image_path: Path | str,
    spec: ModelSpec,
    top_k: int = 5,
) -> List[dict]:
    """Classify a whole image (no tiling, no NMS).

    Returns up to ``top_k`` ``{"class", "confidence"}`` dicts, best first.
    """
    spec.validate()
    if spec.task_type != "classification":
        raise InferenceConfigError("run_classification_on_image needs a classification model.")
    if spec.source == "local_weights":
        model = _load_local_weights(spec.weights_path, "classification")
        results = model.predict(str(image_path), verbose=False)
        return _ultralytics_results_to_predictions(results[0], "classification", top_k)
    if spec.hf_mode == "cloud":
        return _infer_hf_cloud(spec, 0.0, top_k)(str(image_path))
    return _infer_hf_local(spec, 0.0, top_k)(str(image_path))


def run_inference_on_image(
    image_path: Path | str,
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    confidence_threshold: float = 0.1,
    iou_threshold: float = 0.5,
    crop_size: int = 640,
    overlap: int = 32,
    on_warning: Optional[Callable[[str], None]] = None,
    api_url: Optional[str] = None,
    spec: Optional[ModelSpec] = None,
) -> List[dict]:
    """Run detection/segmentation on one image, tiled + NMS-merged.

    ``spec`` picks the model source; without it this is a Roboflow model
    from ``api_key``/``model_id``/``api_url`` (``api_url`` selects a
    self-hosted inference server — see `resolve_inference_api_url`).

    Returns a list of prediction dicts with image-level ``(x, y, width,
    height)`` coordinates.
    """
    if spec is None:
        spec = ModelSpec(source="roboflow", model_id=model_id, api_key=api_key, api_url=api_url)
    if spec.task_type == "classification":
        raise InferenceConfigError(
            "Classification models label the whole image; use run_classification_on_image."
        )
    infer_fn = _make_infer_fn(spec, confidence_threshold)

    crops = crop_image_with_overlap(
        image_path, crop_size=crop_size, overlap=overlap
    )
    if not crops:
        return []

    all_predictions: List[dict] = []
    crop_errors = 0
    consecutive_failures = 0
    last_error = ""
    temp_dir = crops[0]["temp_dir"]

    try:
        for idx, crop_info in enumerate(crops):
            try:
                raw = infer_fn(crop_info["crop_path"])
                all_predictions.extend(
                    _transform_to_image_coords(raw, crop_info)
                )
                consecutive_failures = 0
            except InferenceConfigError:
                raise
            except Exception as exc:
                crop_errors += 1
                consecutive_failures += 1
                last_error = redact_api_key(exc)
                msg = (
                    f"Crop {crop_info['crop_id']}/{len(crops)} failed: {last_error}"
                )
                logger.warning(msg)
                if on_warning:
                    on_warning(msg)
                if consecutive_failures >= 5:
                    # Partial results would be recorded as a (too low)
                    # detection count — fail the image instead.
                    raise InferenceFailedError(
                        f"Inference aborted on {Path(image_path).name} after "
                        f"5 consecutive crop failures ({idx + 1}/{len(crops)} "
                        f"crops attempted). Last error: {last_error}"
                    )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    if crop_errors and crop_errors == len(crops):
        raise InferenceFailedError(
            f"Inference failed on all {len(crops)} crops of "
            f"{Path(image_path).name}. Last error: {last_error}"
        )

    after_nms = apply_nms(all_predictions, iou_threshold=iou_threshold)
    logger.info(
        "%s: %d crops → %d raw → %d after NMS%s",
        Path(image_path).name,
        len(crops),
        len(all_predictions),
        len(after_nms),
        f" ({crop_errors} crop errors)" if crop_errors else "",
    )
    return after_nms
