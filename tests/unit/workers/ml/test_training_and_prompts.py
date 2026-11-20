"""Zero-shot prompt parsing and the training dataset build (no models needed)."""
import json
from pathlib import Path

from PIL import Image

from gemini.workers.ml import training
from gemini.workers.ml.inference_utils import ModelSpec, _rename_zero_shot
from gemini.workers.ml.zero_shot import is_sam3, parse_prompts


def test_prompts_one_class_per_line_with_names():
    pairs = parse_prompts("pod: one mottled cowpea pod, not a leaf, not a stem\nflower: a single yellow cowpea flower")
    assert pairs == [
        ("pod", "one mottled cowpea pod, not a leaf, not a stem"),
        ("flower", "a single yellow cowpea flower"),
    ]


def test_old_comma_lists_still_mean_several_classes():
    assert parse_prompts("weed, crop, soil") == [("weed", "weed"), ("crop", "crop"), ("soil", "soil")]


def test_zero_shot_labels_get_the_class_names():
    spec = ModelSpec(source="huggingface", model_id="google/owlv2-base-patch16-ensemble",
                     zero_shot=True, prompt="pod: green cowpea pod, not a stem")
    assert spec.labels == ["green cowpea pod, not a stem"]
    out = _rename_zero_shot([{"class": "green cowpea pod, not a stem"}], spec)
    assert out[0]["class"] == "pod"


def test_sam3_is_recognised_and_allows_outlines():
    spec = ModelSpec(source="huggingface", task_type="segmentation", model_id="facebook/sam3",
                     zero_shot=True, prompt="pod: one cowpea pod")
    assert is_sam3("facebook/sam3") and spec.is_sam3
    spec.validate()  # zero-shot segmentation is allowed for SAM 3


def test_tiles_cover_a_long_strip():
    wins = training._tiles(3000, 500, 640)
    assert wins[0][0] == 0 and wins[-1][2] == 3000
    assert all(w[3] == 500 for w in wins)
    assert training._tiles(700, 600, 640) == [(0, 0, 700, 600)]


def test_dataset_from_coco(tmp_path: Path):
    src = tmp_path / "store"
    src.mkdir()
    images = []
    annotations = []
    for i in range(6):
        p = src / f"plot_{i}.png"
        Image.new("RGB", (1600, 400), (40, 120, 40)).save(p)
        images.append({"id": i + 1, "file_name": f"Processed/x/PlotImages/plot_{i}.png", "width": 1600, "height": 400})
        annotations.append({"id": i + 1, "image_id": i + 1, "category_id": 1,
                            "bbox": [100 + 200 * i, 100, 40, 30], "segmentation": []})
    coco = {"images": images, "annotations": annotations, "categories": [{"id": 1, "name": "pod"}]}

    def fetch(path: str, dest: str) -> None:
        Image.open(src / Path(path).name).save(dest)

    yaml_path, counts = training.build_dataset(coco, fetch, tmp_path / "ds", "detect", imgsz=640)
    data = json.loads(yaml_path.read_text())
    assert data["names"] == {"0": "pod"} or data["names"] == {0: "pod"}
    assert counts["images_train"] == 5 and counts["images_val"] == 1
    assert not counts["validation_is_training"]
    labels = list((tmp_path / "ds" / "labels" / "train").glob("*.txt"))
    lines = [l for f in labels for l in f.read_text().splitlines() if l]
    assert lines and all(l.startswith("0 ") and len(l.split()) == 5 for l in lines)
    # Every value is normalised to the tile.
    assert all(0 <= float(v) <= 1 for l in lines for v in l.split()[1:])


def test_few_images_use_all_for_both(tmp_path: Path):
    Image.new("RGB", (500, 500)).save(tmp_path / "a.png")
    coco = {"images": [{"id": 1, "file_name": "a.png", "width": 500, "height": 500}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 3, "bbox": [10, 10, 50, 50],
                             "segmentation": [[10, 10, 60, 10, 60, 60, 10, 60]]}],
            "categories": [{"id": 3, "name": "flower"}]}
    _, counts = training.build_dataset(coco, lambda p, d: Image.open(tmp_path / p).save(d),
                                       tmp_path / "ds", "segment")
    assert counts["validation_is_training"] and counts["tiles_train"] == counts["tiles_val"] == 1
    seg = (tmp_path / "ds" / "labels" / "train" / "0_0.txt").read_text().split()
    assert seg[0] == "0" and len(seg) == 9


def test_short_query_fits_a_16_token_window():
    from gemini.workers.ml.zero_shot import short_query

    def fits(t: str) -> bool:          # one token per word, 16 at most (OWLv2)
        return len(t.split()) <= 16

    long = "a single small white or pale purple cowpea flower, not a leaf, not a pod"
    assert short_query("cowpea pod", fits) == "cowpea pod"
    assert short_query(long, lambda t: len(t.split()) <= 9) == "a single small white or pale purple cowpea flower"
    assert len(short_query(long, lambda t: len(t.split()) <= 4).split()) == 4
    assert fits(short_query(long, fits))
