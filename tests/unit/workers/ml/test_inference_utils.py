"""Unit tests for the ml worker's inference helpers."""
from pathlib import Path

import pytest

# Pillow is used by crop_image_with_overlap; it's the only worker-specific
# dep these tests touch. Skip cleanly if it isn't installed (e.g. running
# pytest inside the backend's top-level poetry venv, which doesn't pull
# worker deps).
pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from gemini.workers.ml.inference_utils import (  # noqa: E402
    apply_nms,
    crop_image_with_overlap,
)


# ---------------------------------------------------------------------------
# apply_nms
# ---------------------------------------------------------------------------


def _box(cls, conf, x, y, w=10, h=10):
    return {"class": cls, "confidence": conf, "x": x, "y": y, "width": w, "height": h}


def test_apply_nms_empty_returns_empty():
    assert apply_nms([]) == []


def test_apply_nms_keeps_single_box():
    preds = [_box("plant", 0.9, 50, 50)]
    kept = apply_nms(preds)
    assert len(kept) == 1
    assert kept[0]["x"] == 50


def test_apply_nms_drops_overlap_keeps_highest_confidence():
    preds = [
        _box("plant", 0.8, 50, 50),
        _box("plant", 0.95, 51, 50),
        _box("plant", 0.85, 200, 200),
    ]
    kept = apply_nms(preds, iou_threshold=0.3)
    assert len(kept) == 2
    confidences = sorted(p["confidence"] for p in kept)
    assert confidences == [0.85, 0.95]


def test_apply_nms_is_per_class():
    preds = [
        _box("plant", 0.9, 50, 50),
        _box("weed", 0.8, 51, 50),
    ]
    kept = apply_nms(preds, iou_threshold=0.3)
    assert len(kept) == 2
    assert {p["class"] for p in kept} == {"plant", "weed"}


# ---------------------------------------------------------------------------
# crop_image_with_overlap
# ---------------------------------------------------------------------------


def _make_image(tmp_path: Path, width: int, height: int) -> Path:
    p = tmp_path / "img.png"
    Image.new("RGB", (width, height), (255, 0, 0)).save(p)
    return p


def test_crop_small_image_returns_single_padded_crop(tmp_path: Path):
    img = _make_image(tmp_path, width=100, height=100)
    crops = crop_image_with_overlap(img, crop_size=640, overlap=32)
    assert len(crops) == 1
    crop = crops[0]
    assert crop["x_offset"] == 0
    assert crop["y_offset"] == 0
    w, h = Image.open(crop["crop_path"]).size
    assert (w, h) == (640, 640)


def test_crop_image_equals_crop_size(tmp_path: Path):
    img = _make_image(tmp_path, width=640, height=640)
    crops = crop_image_with_overlap(img, crop_size=640, overlap=32)
    assert len(crops) == 1
    assert crops[0]["x_offset"] == 0
    assert crops[0]["y_offset"] == 0


def test_crop_large_image_tiles_cover_the_whole_width(tmp_path: Path):
    img = _make_image(tmp_path, width=1300, height=600)
    crops = crop_image_with_overlap(img, crop_size=640, overlap=32)
    for c in crops:
        w, h = Image.open(c["crop_path"]).size
        assert (w, h) == (640, 640)
    x_edges = sorted({c["x_offset"] + c["width"] for c in crops})
    assert x_edges[-1] == 1300, f"final tile doesn't cover right edge: {x_edges}"


def test_crop_temp_dir_is_shared_across_crops(tmp_path: Path):
    img = _make_image(tmp_path, width=1300, height=600)
    crops = crop_image_with_overlap(img, crop_size=640, overlap=32)
    temp_dirs = {c["temp_dir"] for c in crops}
    assert len(temp_dirs) == 1
