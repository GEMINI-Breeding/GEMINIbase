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


# ---------------------------------------------------------------------------
# run_inference_on_image failure handling
# ---------------------------------------------------------------------------


def _patch_infer(monkeypatch, fn):
    import gemini.workers.ml.inference_utils as iu

    monkeypatch.setattr(iu, "_infer_cloud", lambda **kwargs: fn)


def test_inference_all_crops_failing_raises(tmp_path: Path, monkeypatch):
    """A down inference server must fail the image, not return [] (which
    would be recorded as a count of 0)."""
    from gemini.workers.ml.inference_utils import (
        InferenceFailedError,
        run_inference_on_image,
    )

    def _down(crop_path):
        raise ConnectionError("Connection refused")

    _patch_infer(monkeypatch, _down)
    img = _make_image(tmp_path, width=100, height=100)  # single crop

    with pytest.raises(InferenceFailedError, match="all 1 crops"):
        run_inference_on_image(img, api_key="k", model_id="w/m/1")


def test_inference_consecutive_failure_abort_raises(tmp_path: Path, monkeypatch):
    from gemini.workers.ml.inference_utils import (
        InferenceFailedError,
        run_inference_on_image,
    )

    calls = {"n": 0}

    def _flaky(crop_path):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"class": "plant", "confidence": 0.9, "x": 5, "y": 5,
                     "width": 2, "height": 2}]
        raise ConnectionError("Connection refused")

    _patch_infer(monkeypatch, _flaky)
    img = _make_image(tmp_path, width=3000, height=3000)  # many crops

    with pytest.raises(InferenceFailedError, match="5 consecutive"):
        run_inference_on_image(img, api_key="k", model_id="w/m/1")
    assert calls["n"] == 6


def test_inference_isolated_crop_failure_still_returns(tmp_path: Path, monkeypatch):
    from gemini.workers.ml.inference_utils import run_inference_on_image

    calls = {"n": 0}

    def _one_bad(crop_path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("blip")
        return []

    _patch_infer(monkeypatch, _one_bad)
    img = _make_image(tmp_path, width=1300, height=600)

    assert run_inference_on_image(img, api_key="k", model_id="w/m/1") == []


def test_crop_error_messages_redact_api_key(tmp_path: Path, monkeypatch):
    from gemini.workers.ml.inference_utils import (
        InferenceFailedError,
        run_inference_on_image,
    )

    def _down(crop_path):
        raise ConnectionError(
            "HTTPSConnectionPool(host='detect.roboflow.com', port=443): Max "
            "retries exceeded with url: /w/m/1?api_key=SECRET123&confidence=0.1"
        )

    _patch_infer(monkeypatch, _down)
    img = _make_image(tmp_path, width=100, height=100)
    warnings: list[str] = []

    with pytest.raises(InferenceFailedError) as excinfo:
        run_inference_on_image(img, api_key="SECRET123", model_id="w/m/1",
                               on_warning=warnings.append)
    assert "SECRET123" not in str(excinfo.value)
    assert warnings and all("SECRET123" not in w for w in warnings)
    assert "api_key=***" in str(excinfo.value)


def test_redact_api_key():
    from gemini.workers.ml.inference_utils import redact_api_key

    assert redact_api_key("url: /m?api_key=abc&x=1") == "url: /m?api_key=***&x=1"
    assert redact_api_key("no key here") == "no key here"
