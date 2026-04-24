"""
Roboflow inference helpers, ported from the pre-migration FastAPI backend
(main:backend/app/processing/inference_utils.py) and pared down to cloud-
only mode. The local inference-server path is deferred: it requires
docker-in-docker which the GEMINIbase worker containers don't have.

Three public functions:
    crop_image_with_overlap(image_path, crop_size=640, overlap=32)
    apply_nms(predictions, iou_threshold=0.5)
    run_inference_on_image(image_path, api_key, model_id, ...)
"""
from __future__ import annotations

import base64
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, List, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)

CLOUD_API_URL = "https://detect.roboflow.com"


class InferenceConfigError(RuntimeError):
    """Raised when inference fails due to a config problem (bad API key / model ID).

    The worker surfaces this as a FAILED job with a user-readable error message
    rather than a crash loop.
    """


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


def _infer_cloud(
    api_key: str, model_id: str, confidence_threshold: float
) -> Callable[[str], List[dict]]:
    endpoint = f"{CLOUD_API_URL}/{model_id}"

    def _call(crop_path: str) -> List[dict]:
        with open(crop_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
        resp = requests.post(
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


def run_inference_on_image(
    image_path: Path | str,
    api_key: str,
    model_id: str,
    confidence_threshold: float = 0.1,
    iou_threshold: float = 0.5,
    crop_size: int = 640,
    overlap: int = 32,
    on_warning: Optional[Callable[[str], None]] = None,
) -> List[dict]:
    """Run Roboflow cloud inference on one image, tiled + NMS-merged.

    Returns a list of prediction dicts with image-level ``(x, y, width,
    height)`` coordinates.
    """
    infer_fn = _infer_cloud(
        api_key=api_key,
        model_id=model_id,
        confidence_threshold=confidence_threshold,
    )

    crops = crop_image_with_overlap(
        image_path, crop_size=crop_size, overlap=overlap
    )
    if not crops:
        return []

    all_predictions: List[dict] = []
    crop_errors = 0
    consecutive_failures = 0
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
                msg = (
                    f"Crop {crop_info['crop_id']}/{len(crops)} failed: {exc}"
                )
                logger.warning(msg)
                if on_warning:
                    on_warning(msg)
                if consecutive_failures >= 5:
                    logger.warning(
                        "5 consecutive crop failures on %s — aborting.",
                        Path(image_path).name,
                    )
                    break
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

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
