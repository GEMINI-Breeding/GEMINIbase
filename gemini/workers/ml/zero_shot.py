"""
Text-prompted ("zero-shot") detection: find objects from a description, with
no training.

Prompts are one class per line, either a bare description or
``name: description``, e.g.::

    pod: one mottled cowpea pod, not a leaf, not a stem
    flower: a single yellow cowpea flower with visible petals

The description goes to the model; the name is the class in the results (and
so the trait). A comma-separated list without line breaks or names is still
read as several short classes ("weed, crop, soil"), as before.

SAM 3 (``facebook/sam3``) runs through the Ultralytics already in the ML
worker (SAM3SemanticPredictor). On cowpea flowers and pods it found the most
of all the open-vocabulary detectors tried (AgVFM prompt study: pod mAP50
0.37 vs 0.09 for OWLv2 / YOLO-World), with masks. Its weights are gated on
Hugging Face: they download once with a token that has accepted the licence,
or are read from ``Models/weights/sam3.pt`` in storage when uploaded there.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SAM3_REPO = "facebook/sam3"
SAM3_FILE = "sam3.pt"
SAM3_STORAGE_PATH = "Models/weights/sam3.pt"

Progress = Callable[[float, str], None]

_BUILD_LOCK = threading.Lock()   # loading a predictor
_RUN_LOCK = threading.Lock()     # one image at a time through a predictor
_PREDICTORS: Dict[str, Any] = {}


def parse_prompts(prompt: Optional[str]) -> List[Tuple[str, str]]:
    """``(class name, description)`` pairs from a prompt text."""
    text = (prompt or "").strip()
    if not text:
        return []
    if "\n" in text or ";" in text or ":" in text:
        parts = [p.strip() for p in text.replace(";", "\n").splitlines()]
    else:
        parts = [p.strip() for p in text.split(",")]
    out: List[Tuple[str, str]] = []
    for p in parts:
        if not p:
            continue
        if ":" in p:
            name, desc = p.split(":", 1)
            name, desc = name.strip(), desc.strip()
            if name and desc:
                out.append((name, desc))
                continue
        out.append((p, p))
    return out


def is_sam3(model_id: Optional[str]) -> bool:
    m = (model_id or "").lower()
    return m.endswith("/sam3") or m in ("sam3", "sam3.pt") or "sam3" in m.split("/")[-1]


def _weights_dir() -> Path:
    base = os.environ.get("GEMINI_MODEL_CACHE_DIR") or os.path.expanduser("~/.cache/gemini-models")
    d = Path(base) / "ultralytics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sam3_weights(token: Optional[str] = None, fetch_from_storage: Optional[Callable[[str, str], bool]] = None,
                 progress: Optional[Progress] = None) -> str:
    """Local path of sam3.pt: cached, else from storage, else from Hugging Face."""
    from gemini.workers.ml.inference_utils import InferenceConfigError

    path = _weights_dir() / SAM3_FILE
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    part = path.with_suffix(".pt.part")
    if fetch_from_storage is not None:
        if progress:
            progress(0.05, "Fetching SAM 3 weights from storage")
        try:
            if fetch_from_storage(SAM3_STORAGE_PATH, str(part)):
                os.replace(part, path)
                return str(path)
        except Exception:  # noqa: BLE001 — not uploaded: try Hugging Face
            pass
    token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if progress:
        progress(0.1, "Downloading SAM 3 weights (about 3.4 GB, once)")
    try:
        from huggingface_hub import hf_hub_download

        got = hf_hub_download(SAM3_REPO, SAM3_FILE, token=token or None, local_dir=str(_weights_dir()))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "401" in msg or "403" in msg or "gated" in msg.lower() or "access" in msg.lower():
            raise InferenceConfigError(
                "SAM 3's weights are gated on Hugging Face. Accept the licence at "
                "huggingface.co/facebook/sam3, then add an access token to this model "
                f"(or upload sam3.pt to {SAM3_STORAGE_PATH})."
            ) from e
        raise InferenceConfigError(f"Could not fetch SAM 3's weights: {msg[:300]}") from e
    if Path(got) != path:
        os.replace(got, path)
    return str(path)


def _sam3_predictor(weights: str):
    with _BUILD_LOCK:
        if weights not in _PREDICTORS:
            from gemini.workers.ml.inference_utils import InferenceConfigError

            try:
                import torch
                from ultralytics.models.sam import SAM3SemanticPredictor
            except ImportError as e:
                raise InferenceConfigError(
                    "SAM 3 needs Ultralytics 8.3.237 or newer in the ML worker "
                    "(on a cluster: gemi-hpc pull ml-deps)."
                ) from e
            overrides = dict(conf=0.25, task="segment", mode="predict", model=weights,
                             half=bool(torch.cuda.is_available()), verbose=False, save=False)
            _PREDICTORS[weights] = SAM3SemanticPredictor(overrides=overrides)
        return _PREDICTORS[weights]


def sam3_predict(image_path: str, pairs: List[Tuple[str, str]], conf: float, weights: str,
                 keep_masks: bool = True) -> List[dict]:
    """Every object matching the descriptions, as app predictions (class = the
    pair's name; ``points`` = mask outline when ``keep_masks``)."""
    from gemini.workers.ml.prompted import _to_predictions

    if not pairs:
        return []
    texts = [d for _, d in pairs]
    names = [n for n, _ in pairs]
    predictor = _sam3_predictor(weights)
    with _RUN_LOCK:
        predictor.args.conf = conf
        predictor.set_image(image_path)
        results = predictor(text=texts)
    preds = _to_predictions(results[0], names, names[0]) if results else []
    if not keep_masks:
        for p in preds:
            p.pop("points", None)
    return [p for p in preds if p.get("confidence", 1.0) >= conf]


def rename(preds: List[dict], pairs: List[Tuple[str, str]]) -> List[dict]:
    """Model labels (the descriptions) → the classes' names."""
    by_desc = {d: n for n, d in pairs}
    for p in preds:
        p["class"] = by_desc.get(p.get("class", ""), p.get("class", ""))
    return preds
