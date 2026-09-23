"""RUN_STITCH planning: plot frame ranges, crop-rule choice, AgRowStitch config."""
import pandas as pd
import pytest

from gemini.workers.stitch import plan


def msgs(n=10, direction="South"):
    return pd.DataFrame({
        "/top/rgb_file": [f"/top/rgb-{1000 + i}.jpg" for i in range(n)],
        "lat": [38.5 - i * 1e-6 for i in range(n)],
        "lon": [-121.7] * n,
        "direction": [direction] * n,
    })


def test_basenames_strip_the_camera_folder():
    names = plan.basenames(msgs(3))
    assert list(names) == ["rgb-1000.jpg", "rgb-1001.jpg", "rgb-1002.jpg"]


def test_basenames_need_an_image_column():
    with pytest.raises(ValueError, match="no image column"):
        plan.basenames(pd.DataFrame({"lat": [1.0], "lon": [2.0]}))


def test_plot_rows_is_inclusive_and_order_independent():
    df = msgs()
    names = plan.basenames(df)
    rows = plan.plot_rows(df, names, "rgb-1002.jpg", "rgb-1005.jpg")
    assert list(plan.basenames(rows)) == [f"rgb-{i}.jpg" for i in range(1002, 1006)]
    swapped = plan.plot_rows(df, names, "rgb-1005.jpg", "rgb-1002.jpg")
    assert list(swapped.index) == list(rows.index)


def test_plot_rows_reports_a_frame_from_another_track():
    df = msgs()
    with pytest.raises(ValueError, match="rgb-9999.jpg"):
        plan.plot_rows(df, plan.basenames(df), "rgb-1001.jpg", "rgb-9999.jpg")


def test_dominant_heading():
    df = msgs(5)
    df.loc[0, "direction"] = "East"
    assert plan.dominant_heading(df) == "south"
    assert plan.dominant_heading(df.drop(columns="direction")) == ""


RULES = [
    {"filterMode": "heading", "headings": ["North"], "mask_left": 10},
    {"filterMode": "direction", "directions": ["left"], "mask_top": 20},
    {"filterMode": "heading", "headings": [], "mask_bottom": 5},
]


def test_crop_rule_by_heading():
    assert plan.choose_crop_mask(RULES, "down", "north") == [10, 0, 0, 0]


def test_crop_rule_by_marked_direction():
    assert plan.choose_crop_mask(RULES, "left", "south") == [0, 0, 20, 0]


def test_crop_rule_catch_all_and_none():
    assert plan.choose_crop_mask(RULES, "up", "south") == [0, 0, 0, 5]
    assert plan.choose_crop_mask(RULES[:2], "up", "south") is None
    assert plan.choose_crop_mask(None, "up", "south") is None


DEFAULTS = {"device": "cuda", "forward_limit": 8, "mask": [0, 0, 0, 0], "min_inliers": 20}


def test_base_config_layers_settings_then_custom():
    cfg, dropped = plan.build_base_config(
        DEFAULTS,
        {"forward_limit": 4, "min_inliers": None,
         "crop_rules": [{"directions": [], "mask_left": 7, "mask_right": 3}]},
        {"min_inliers": 30},
    )
    assert cfg["forward_limit"] == 4
    assert cfg["min_inliers"] == 30
    assert cfg["mask"] == [7, 3, 0, 0]
    assert dropped == []


def test_base_config_legacy_flat_mask():
    cfg, _ = plan.build_base_config(DEFAULTS, {"mask_top": 12})
    assert cfg["mask"] == [0, 0, 12, 0]


def test_base_config_drops_keys_agrowstitch_would_crash_on():
    # AgRowStitch.load_config raises KeyError on any key it doesn't know;
    # num_cpu is a run() argument, not a config key.
    cfg, dropped = plan.build_base_config(DEFAULTS, {}, {"num_cpu": 4, "bogus": 1})
    assert dropped == ["bogus", "num_cpu"]
    assert "num_cpu" not in cfg and "bogus" not in cfg


def test_direction_map_covers_the_ui_values():
    for ui, expected in [("down", "DOWN"), ("up", "UP"), ("left", "LEFT"), ("right", "RIGHT")]:
        assert plan.DIRECTION_MAP[ui] == expected
