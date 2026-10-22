"""
Prompted segmentation for labelling in the app (LOCATE_PLANTS with
``prompted``): the person shows one example and the models do the rest.

    mode "similar": YOLOE with visual prompts. Given example box(es) of an
        object — on this image, or on an earlier one (``refer_image``) — it
        returns every similar object in the image, with box and mask.
    mode "segment": SAM 2. Turns boxes or clicked points into exact masks.
    mode "warmup": fetch and load both, so the first real prompt is quick.

Both run through the Ultralytics already in the ML worker. The weights are
fetched on first use into the worker's model folder (GEMINI_MODEL_CACHE_DIR,
which outlives the worker; its working directory does not), with progress
reported on the job. Models stay loaded between jobs, so the next prompt
answers in about a second.

Predictions use the app's shape: {class, confidence, x, y, width, height}
(centre + size in image pixels) plus ``points`` (the mask outline) when a
mask exists.
"""
from __future__ import annotations

import os
import threading
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_MODELS: Dict[str, Any] = {}
_LOCK = threading.Lock()

YOLOE_WEIGHTS = "yoloe-11s-seg.pt"
SAM_WEIGHTS = "sam2.1_b.pt"
_RELEASE = "https://github.com/ultralytics/assets/releases/download/v8.3.0/"
_LABELS = {YOLOE_WEIGHTS: "YOLOE (find similar)", SAM_WEIGHTS: "SAM 2 (outlines)"}

# progress(fraction 0..1, stage text)
Progress = Callable[[float, str], None]


def _weights_dir() -> Path:
    base = os.environ.get("GEMINI_MODEL_CACHE_DIR") or os.path.expanduser("~/.cache/gemini-models")
    d = Path(base) / "ultralytics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_weights(name: str, progress: Optional[Progress] = None) -> str:
    """Local path of a weights file, downloaded once (with progress) into
    the model folder."""
    path = _weights_dir() / name
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    label = _LABELS.get(name, name)
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(_RELEASE + name, timeout=60) as r, open(tmp, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        done, last = 0, -1.0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress and total and done / total - last >= 0.05:
                last = done / total
                progress(last, f"Downloading {label} weights: {done >> 20} of {total >> 20} MB")
    tmp.replace(path)
    return str(path)


def _model(kind: str, weights: str, progress: Optional[Progress] = None):
    with _LOCK:
        if weights not in _MODELS:
            local = ensure_weights(weights, progress)
            if progress:
                progress(1.0, f"Loading {_LABELS.get(weights, weights)}")
            if kind == "yoloe":
                from ultralytics import YOLOE

                _MODELS[weights] = YOLOE(local)
            else:
                from ultralytics import SAM

                _MODELS[weights] = SAM(local)
        return _MODELS[weights]


def warmup(progress: Optional[Progress] = None) -> dict:
    """Fetch and load both models (YOLOE first: it is the smaller)."""
    def part(lo: float, hi: float) -> Optional[Progress]:
        return (lambda f, stage: progress(lo + (hi - lo) * f, stage)) if progress else None

    _model("yoloe", YOLOE_WEIGHTS, part(0.0, 0.2))
    _model("sam", SAM_WEIGHTS, part(0.2, 1.0))
    return {"ready": True, "models": [YOLOE_WEIGHTS, SAM_WEIGHTS]}


def _to_predictions(result: Any, names: List[str], default_class: str) -> List[dict]:
    out: List[dict] = []
    boxes = getattr(result, "boxes", None)
    masks = getattr(result, "masks", None)
    polys = list(masks.xy) if masks is not None else []
    if boxes is None:
        return out
    xyxy = boxes.xyxy.tolist()
    conf = boxes.conf.tolist() if getattr(boxes, "conf", None) is not None else [1.0] * len(xyxy)
    cls = boxes.cls.tolist() if getattr(boxes, "cls", None) is not None else [0] * len(xyxy)
    for i, (x1, y1, x2, y2) in enumerate(xyxy):
        k = int(cls[i]) if i < len(cls) else 0
        p: dict = {
            "class": names[k] if 0 <= k < len(names) else default_class,
            "confidence": float(conf[i]) if i < len(conf) else 1.0,
            "x": (x1 + x2) / 2.0,
            "y": (y1 + y2) / 2.0,
            "width": x2 - x1,
            "height": y2 - y1,
        }
        if i < len(polys) and len(polys[i]) >= 3:
            p["points"] = [{"x": float(px), "y": float(py)} for px, py in polys[i]]
        out.append(p)
    return out


def similar(image: str, boxes: List[List[float]], classes: List[str],
            refer_image: Optional[str] = None, conf: float = 0.25,
            weights: str = YOLOE_WEIGHTS) -> List[dict]:
    """Every object like the example boxes ([x1, y1, x2, y2], image pixels;
    on ``refer_image`` when given, else on ``image``)."""
    import numpy as np
    from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor

    names = list(dict.fromkeys(classes)) or ["object"]
    prompts = {
        "bboxes": np.array(boxes, dtype=float),
        "cls": np.array([names.index(c) for c in classes] or [0]),
    }
    kwargs: Dict[str, Any] = {"visual_prompts": prompts, "predictor": YOLOEVPSegPredictor,
                              "conf": conf, "verbose": False}
    if refer_image:
        kwargs["refer_image"] = refer_image
    results = _model("yoloe", weights).predict(image, **kwargs)
    return _to_predictions(results[0], names, names[0]) if results else []


def segment(image: str, boxes: Optional[List[List[float]]] = None,
            points: Optional[List[List[float]]] = None,
            point_labels: Optional[List[int]] = None, label: str = "object",
            weights: str = SAM_WEIGHTS) -> List[dict]:
    """Exact masks for boxes, or for clicked points (label 1 = on the
    object, 0 = not on it)."""
    kwargs: Dict[str, Any] = {"verbose": False}
    if boxes:
        kwargs["bboxes"] = boxes
    if points:
        kwargs["points"] = points
        kwargs["labels"] = point_labels or [1] * len(points)
    results = _model("sam", weights)(image, **kwargs)
    return _to_predictions(results[0], [label], label) if results else []


def run(image: str, prompted: dict, refer_local: Optional[str] = None,
        progress: Optional[Progress] = None) -> List[dict]:
    """The ``prompted`` job parameter → predictions."""
    mode = prompted.get("mode")
    # Fetch/load the model first, so a first use reports its download.
    if mode == "similar":
        _model("yoloe", YOLOE_WEIGHTS, progress)
    elif mode == "segment":
        _model("sam", SAM_WEIGHTS, progress)
    if mode == "similar":
        return similar(image, prompted.get("boxes") or [], prompted.get("classes") or [],
                       refer_image=refer_local, conf=float(prompted.get("conf", 0.25)))
    if mode == "segment":
        return segment(image, boxes=prompted.get("boxes"), points=prompted.get("points"),
                       point_labels=prompted.get("point_labels"), label=str(prompted.get("label") or "object"))
    raise ValueError("prompted.mode must be 'similar' or 'segment'")
