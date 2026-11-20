"""
TRAIN_MODEL: fine-tune an Ultralytics YOLO model on a labelled set.

Input (job parameters):
    coco_path       storage path of the labelled set as COCO JSON; each
                    image's ``file_name`` is its storage object path (as the
                    app's labelling export writes it)
    name            what to call the model (file name and default trait)
    base            a starting checkpoint: "yolo11n" | "yolo11s" | "yolo11m"
                    (detection) or "yolo11n-seg" | "yolo11s-seg" (outlines)
    base_weights_path  instead of ``base``: an Ultralytics .pt in storage
                    (an agricultural model to start from, or an earlier run)
    preset          "few" (a handful of labelled images: early layers frozen,
                    strong augmentation, more patience) | "standard" | "quick"
    epochs, imgsz, freeze, val_fraction   override the preset

Large plot images are cut into ``imgsz`` tiles (with the same overlap the
inference uses), so training sees objects at the scale inference does. The
split into training and validation is by image, not by tile, so the two never
share a picture; with fewer than 5 images all are used for both (the scores
are then optimistic, and the result says so).

Output: best weights uploaded to ``Models/weights/<time>-<name>.pt`` (the
folder the app lists uploaded weights from) and the run's metrics.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

BASES: Dict[str, Tuple[str, str]] = {
    "yolo11n": ("yolo11n.pt", "detect"),
    "yolo11s": ("yolo11s.pt", "detect"),
    "yolo11m": ("yolo11m.pt", "detect"),
    "yolo11n-seg": ("yolo11n-seg.pt", "segment"),
    "yolo11s-seg": ("yolo11s-seg.pt", "segment"),
}

# Few labels: keep the pretrained backbone (freeze the first 10 layers),
# augment hard and give it time; many labels: train everything.
PRESETS: Dict[str, dict] = {
    "few": dict(epochs=150, patience=50, freeze=10, lr0=0.002, flipud=0.5, fliplr=0.5,
                degrees=10.0, scale=0.5, mosaic=1.0, close_mosaic=20),
    "standard": dict(epochs=100, patience=30, freeze=0),
    "quick": dict(epochs=30, patience=10, freeze=10),
}

Fetch = Callable[[str, str], None]           # (storage path, local path)
Upload = Callable[[str, str], None]          # (local path, storage path)
Progress = Callable[[float, dict], None]     # (0..100, detail)


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "model"


def _tiles(w: int, h: int, size: int, overlap: int = 32) -> List[Tuple[int, int, int, int]]:
    """Tile windows (x0, y0, x1, y1) covering the image; one window if it is small."""
    if w <= size * 1.5 and h <= size * 1.5:
        return [(0, 0, w, h)]
    step = max(1, size - overlap)

    def starts(n: int) -> List[int]:
        if n <= size:
            return [0]
        s = list(range(0, n - size, step)) + [n - size]
        return sorted(set(s))

    return [(x, y, min(x + size, w), min(y + size, h)) for y in starts(h) for x in starts(w)]


def _yolo_lines(anns: List[dict], win: Tuple[int, int, int, int], cat_index: Dict[int, int],
                task: str) -> List[str]:
    """YOLO label lines for the annotations whose centre is in the window."""
    x0, y0, x1, y1 = win
    tw, th = x1 - x0, y1 - y0
    out: List[str] = []
    for a in anns:
        bx, by, bw, bh = a["bbox"]
        cx, cy = bx + bw / 2, by + bh / 2
        if not (x0 <= cx < x1 and y0 <= cy < y1):
            continue
        k = cat_index.get(a["category_id"])
        if k is None:
            continue
        clip = lambda v, lo, hi: min(max(v, lo), hi)  # noqa: E731
        if task == "segment":
            seg = a.get("segmentation") or []
            poly = seg[0] if seg and isinstance(seg[0], list) and len(seg[0]) >= 6 else \
                [bx, by, bx + bw, by, bx + bw, by + bh, bx, by + bh]
            pts = []
            for i in range(0, len(poly) - 1, 2):
                pts += [clip((poly[i] - x0) / tw, 0, 1), clip((poly[i + 1] - y0) / th, 0, 1)]
            out.append(" ".join([str(k)] + [f"{v:.6f}" for v in pts]))
        else:
            l, t = clip(bx, x0, x1), clip(by, y0, y1)
            r, b = clip(bx + bw, x0, x1), clip(by + bh, y0, y1)
            if r - l < 1 or b - t < 1:
                continue
            out.append(f"{k} {((l + r) / 2 - x0) / tw:.6f} {((t + b) / 2 - y0) / th:.6f} "
                       f"{(r - l) / tw:.6f} {(b - t) / th:.6f}")
    return out


def build_dataset(coco: dict, fetch: Fetch, root: Path, task: str, imgsz: int = 640,
                  val_fraction: float = 0.2, seed: int = 0) -> Tuple[Path, dict]:
    """Write a YOLO dataset (tiles + labels + data.yaml) from COCO; returns
    the yaml path and counts."""
    from PIL import Image

    cats = sorted(coco.get("categories") or [], key=lambda c: c["id"])
    names = [c["name"] for c in cats]
    cat_index = {c["id"]: i for i, c in enumerate(cats)}
    anns_by_image: Dict[int, List[dict]] = {}
    for a in coco.get("annotations") or []:
        anns_by_image.setdefault(a["image_id"], []).append(a)
    images = [im for im in coco.get("images") or [] if anns_by_image.get(im["id"])]
    if not images:
        raise ValueError("The labelled set has no saved images with kept objects.")
    if not names:
        raise ValueError("The labelled set has no classes.")

    rng = random.Random(seed)
    order = images[:]
    rng.shuffle(order)
    n_val = 0 if len(order) < 5 else max(1, round(len(order) * val_fraction))
    val_ids = {im["id"] for im in order[:n_val]}
    shared = n_val == 0

    src = root / "src"
    src.mkdir(parents=True, exist_ok=True)
    counts = {"images_train": 0, "images_val": 0, "tiles_train": 0, "tiles_val": 0, "objects": 0}
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    for n, im in enumerate(images):
        local = src / f"{n}{Path(im['file_name']).suffix or '.png'}"
        fetch(im["file_name"], str(local))
        anns = anns_by_image[im["id"]]
        counts["objects"] += len(anns)
        splits = ["train", "val"] if shared else (["val"] if im["id"] in val_ids else ["train"])
        with Image.open(local) as pic:
            pic = pic.convert("RGB")
            w, h = pic.size
            windows = _tiles(w, h, imgsz)
            empty_kept = 0
            for t, win in enumerate(windows):
                lines = _yolo_lines(anns, win, cat_index, task)
                # Some empty tiles teach "nothing here"; not all of them.
                if not lines:
                    if empty_kept >= max(1, len(windows) // 4):
                        continue
                    empty_kept += 1
                crop = pic.crop(win)
                for split in splits:
                    stem = f"{n}_{t}"
                    crop.save(root / "images" / split / f"{stem}.jpg", quality=95)
                    (root / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
                    counts[f"tiles_{split}"] += 1
        for split in splits:
            counts[f"images_{split}"] += 1
        local.unlink(missing_ok=True)

    yaml_path = root / "data.yaml"
    yaml_path.write_text(json.dumps({
        "path": str(root), "train": "images/train", "val": "images/val",
        "names": {i: n for i, n in enumerate(names)},
    }))
    counts["classes"] = names
    counts["validation_is_training"] = shared
    return yaml_path, counts


def _metrics(results_dict: dict) -> dict:
    keys = {"metrics/mAP50(B)": "map50", "metrics/mAP50-95(B)": "map50_95",
            "metrics/precision(B)": "precision", "metrics/recall(B)": "recall",
            "metrics/mAP50(M)": "mask_map50", "metrics/mAP50-95(M)": "mask_map50_95"}
    return {v: round(float(results_dict[k]), 4) for k, v in keys.items() if k in (results_dict or {})}


def train(params: dict, fetch: Fetch, upload: Upload, progress: Progress, workdir: Path,
          base_weights: Callable[[str], str], job_id: str = "") -> dict:
    """Run one training job; returns the job result."""
    import torch
    from ultralytics import YOLO, settings

    settings.update({"sync": False})
    name = str(params.get("name") or "trained model")
    preset = dict(PRESETS.get(params.get("preset") or "standard", PRESETS["standard"]))
    for k in ("epochs", "freeze", "patience"):
        if params.get(k) is not None:
            preset[k] = int(params[k])
    imgsz = int(params.get("imgsz") or 640)

    # Starting point: an app checkpoint, or weights from storage.
    if params.get("base_weights_path"):
        local_base = workdir / "base.pt"
        fetch(params["base_weights_path"], str(local_base))
        base_label = Path(params["base_weights_path"]).name
    else:
        key = params.get("base") or "yolo11n"
        if key not in BASES:
            raise ValueError(f"Unknown starting model '{key}'. Use one of: {', '.join(BASES)}.")
        local_base = Path(base_weights(BASES[key][0]))
        base_label = key
    model = YOLO(str(local_base))
    task = model.task if model.task in ("detect", "segment") else "detect"

    progress(5, {"stage": "preparing the labelled images"})
    coco_local = workdir / "coco.json"
    fetch(params["coco_path"], str(coco_local))
    coco = json.loads(coco_local.read_text())
    data_yaml, counts = build_dataset(coco, fetch, workdir / "data", task, imgsz=imgsz,
                                      val_fraction=float(params.get("val_fraction", 0.2)))

    cuda = torch.cuda.is_available()
    epochs = int(preset.pop("epochs"))
    if not cuda:
        epochs = min(epochs, 40)   # a CPU run: keep it to hours, not days

    def on_epoch(trainer) -> None:
        e = int(getattr(trainer, "epoch", 0)) + 1
        m = _metrics(getattr(trainer, "metrics", {}) or {})
        progress(10 + 85 * e / max(epochs, 1), {"stage": f"training: epoch {e} of {epochs}", **m})

    model.add_callback("on_fit_epoch_end", on_epoch)
    progress(10, {"stage": f"training on {'GPU' if cuda else 'CPU'}",
                  "tiles": counts["tiles_train"]})
    results = model.train(
        data=str(data_yaml), epochs=epochs, imgsz=imgsz, device=0 if cuda else "cpu",
        batch=16 if cuda else 4, workers=2, project=str(workdir / "runs"), name="run",
        exist_ok=True, plots=False, verbose=False, seed=0, **preset,
    )
    save_dir = Path(getattr(model.trainer, "save_dir", workdir / "runs" / "run"))
    best = save_dir / "weights" / "best.pt"
    if not best.exists():
        best = save_dir / "weights" / "last.pt"

    import time

    weights_path = f"Models/weights/{int(time.time() * 1000)}-{_safe(name)}.pt"
    progress(96, {"stage": "saving the model"})
    upload(str(best), weights_path)
    results_csv = save_dir / "results.csv"
    log_path = None
    if results_csv.exists() and job_id:
        log_path = f"Models/training/{job_id}/results.csv"
        upload(str(results_csv), log_path)
    shutil.rmtree(workdir / "data", ignore_errors=True)

    return {
        "weights_path": weights_path,
        "weights_name": f"{_safe(name)}.pt",
        "name": name,
        "task_type": "segmentation" if task == "segment" else "detection",
        "base": base_label,
        "preset": params.get("preset") or "standard",
        "epochs": epochs,
        "epochs_run": int(getattr(model.trainer, "epoch", epochs - 1)) + 1,
        "device": "GPU" if cuda else "CPU",
        "metrics": _metrics(getattr(results, "results_dict", {}) or {}),
        "results_csv": log_path,
        **{k: counts[k] for k in ("images_train", "images_val", "tiles_train", "tiles_val",
                                  "objects", "classes", "validation_is_training")},
    }
