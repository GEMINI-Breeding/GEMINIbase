"""ModelSpec parsing/validation and the prediction converters for the
Hugging Face and Ultralytics backends (no model downloads)."""
import pytest

pytest.importorskip("PIL")

from gemini.workers.ml.inference_utils import (  # noqa: E402
    InferenceConfigError,
    ModelSpec,
    _hf_outputs_to_predictions,
    redact_api_key,
    run_inference_on_image,
)


def test_legacy_roboflow_params_default_to_roboflow_detection():
    spec = ModelSpec.from_params({"api_key": "k", "model_id": "ws/m/1", "api_url": "http://x"})
    assert (spec.source, spec.task_type, spec.model_id, spec.api_key, spec.api_url) == (
        "roboflow", "detection", "ws/m/1", "k", "http://x",
    )
    spec.validate()


def test_huggingface_params_use_hf_fields_and_env_token(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_fromenvironment123")
    spec = ModelSpec.from_params(
        {
            "source": "huggingface",
            "hf_model_id": "google/owlvit-base-patch32",
            "hf_mode": "cloud",
            "hf_zero_shot": True,
            "hf_prompt": " weed, crop ,, soil ",
            # Roboflow fields must not leak into an HF spec.
            "api_key": "rf_key",
            "api_url": "http://localhost:9002",
        }
    )
    assert spec.model_id == "google/owlvit-base-patch32"
    assert spec.api_key == "hf_fromenvironment123"
    assert spec.api_url is None
    assert spec.labels == ["weed", "crop", "soil"]
    spec.validate()


@pytest.mark.parametrize(
    "params, message",
    [
        ({"source": "nope"}, "Unknown model source"),
        ({"source": "roboflow", "model_id": "m"}, "API key"),
        ({"source": "roboflow", "api_key": "k", "model_id": "m", "task_type": "classification"}, "Classification"),
        ({"source": "local_weights"}, "weights file"),
        ({"source": "local_weights", "weights_path": "Models/w.h5"}, "Unsupported weights"),
        ({"source": "huggingface"}, "model ID"),
        ({"source": "huggingface", "hf_model_id": "a/b", "hf_zero_shot": True}, "prompt"),
        ({"source": "huggingface", "hf_model_id": "a/b", "hf_zero_shot": True, "hf_prompt": "x", "task_type": "segmentation"}, "Zero-shot segmentation"),
        ({"source": "huggingface", "hf_model_id": "a/b", "hf_mode": "cloud"}, "access token"),
    ],
)
def test_invalid_specs_raise_config_errors(params, message, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(InferenceConfigError, match=message):
        ModelSpec.from_params(params).validate()


def test_classification_spec_is_refused_by_the_tiled_path():
    spec = ModelSpec(source="local_weights", task_type="classification", weights_path="w.pt")
    with pytest.raises(InferenceConfigError, match="whole image"):
        run_inference_on_image("unused.png", spec=spec)


def test_hf_detection_boxes_become_centre_coordinates():
    preds = _hf_outputs_to_predictions(
        [{"score": 0.9, "label": "plant", "box": {"xmin": 10, "ymin": 20, "xmax": 30, "ymax": 60}}],
        "detection",
    )
    assert preds == [
        {"class": "plant", "confidence": 0.9, "x": 20.0, "y": 40.0, "width": 20.0, "height": 40.0}
    ]


def test_hf_segmentation_mask_becomes_polygon_with_box():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from PIL import Image

    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[10:20, 5:25] = 255
    preds = _hf_outputs_to_predictions(
        [{"score": None, "label": "leaf", "mask": Image.fromarray(mask)}], "segmentation"
    )
    assert len(preds) == 1
    p = preds[0]
    assert p["class"] == "leaf" and p["confidence"] == 1.0  # semantic seg has no score
    assert (p["x"], p["y"], p["width"], p["height"]) == (14.5, 14.5, 19.0, 9.0)
    assert len(p["points"]) >= 4


def test_hf_tokens_are_redacted_from_errors():
    assert redact_api_key("401 for token hf_abcdefghijklmnop") == "401 for token hf_***"
