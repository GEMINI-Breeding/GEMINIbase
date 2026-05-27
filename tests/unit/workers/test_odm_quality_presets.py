"""
Unit tests for the ODM worker's reconstruction-quality preset handling.

Pre-this-commit, the OrthomosaicTool form exposed a 6-value
"Reconstruction quality" dropdown (Default / Lowest / Low / Medium /
High / Ultra) but the worker ignored every value — DEFAULT_OPTIONS was
used regardless. The user only noticed when memory-tuning custom flags
were also being silently dropped (a separate bug).

These tests pin the new behavior so the dropdown can never silently
go decorative again:
  - `_apply_quality_preset(name)` returns DEFAULT_OPTIONS merged with
    the named preset's overrides; preset values win on key collision.
  - Unknown / empty / "Default" / "Custom" yield DEFAULT_OPTIONS verbatim.
  - The mutation safety guarantee: callers may freely mutate the
    returned list without affecting module state.

These are pure-function tests — no NodeODM or HTTP needed.
"""
from gemini.workers.odm.worker import (
    DEFAULT_OPTIONS,
    QUALITY_PRESETS,
    _apply_quality_preset,
)


def _opt(name: str, options: list[dict]):
    """Return the value of the option with the given name, or None."""
    for o in options:
        if o["name"] == name:
            return o["value"]
    return None


def test_default_options_contain_baseline_keys():
    """DEFAULT_OPTIONS must always carry ortho/dem resolution + dsm flag.
    Without these, the worker would emit ODM jobs that can't produce
    the artifacts downstream code (CREATE_COG, EXTRACT_TRAITS) expects.
    """
    keys = {o["name"] for o in DEFAULT_OPTIONS}
    assert "orthophoto-resolution" in keys
    assert "dem-resolution" in keys
    assert "dsm" in keys


def test_legacy_default_quality_returns_defaults():
    """The pre-rename "Default" label (and any other legacy string)
    falls through to DEFAULT_OPTIONS unchanged. Saved pipeline configs
    from before the Draft/Standard/High Quality/Ultra rename can still
    submit jobs — the legacy migration runs frontend-side, but the
    worker must not blow up if a stale string slips through.
    """
    out = _apply_quality_preset("Default")
    assert out == DEFAULT_OPTIONS


def test_custom_quality_returns_defaults():
    """'Custom' is a sentinel meaning 'read custom_options instead'.
    The preset application path should leave it untouched (caller's
    branch handles the textbox).
    """
    out = _apply_quality_preset("Custom")
    assert out == DEFAULT_OPTIONS


def test_none_quality_returns_defaults():
    out = _apply_quality_preset(None)
    assert out == DEFAULT_OPTIONS


def test_unknown_quality_returns_defaults():
    out = _apply_quality_preset("Quantum")
    assert out == DEFAULT_OPTIONS


def test_preset_table_matches_main():
    """The Draft/Standard/High Quality/Ultra preset values are a 1:1 port
    of main's ODM_PRESETS table (frontend ProcessingPipeline.tsx +
    backend run_orthomosaic defaults). Pin the exact values so any
    drift from main is caught — silent divergence is what produced
    the bug chain that motivated this rewrite.
    """
    expected = {
        "Draft": {
            "feature-quality": "low",
            "pc-quality": "lowest",
            "orthophoto-resolution": 5,
            "dem-resolution": 5,
        },
        "Standard": {
            "feature-quality": "high",
            "pc-quality": "medium",
            "orthophoto-resolution": 3,
            "dem-resolution": 3,
        },
        "High Quality": {
            "feature-quality": "ultra",
            "pc-quality": "high",
            "orthophoto-resolution": 2,
            "dem-resolution": 2,
        },
        "Ultra": {
            "feature-quality": "ultra",
            "pc-quality": "ultra",
            "orthophoto-resolution": 1,
            "dem-resolution": 1,
        },
    }
    for name, knobs in expected.items():
        out = _apply_quality_preset(name)
        for k, v in knobs.items():
            assert _opt(k, out) == v, (
                f"preset {name!r} drifted from main: expected {k}={v!r}, "
                f"got {_opt(k, out)!r}"
            )


def test_preset_set_matches_main_exactly():
    """We ship exactly the four presets main has — no extra tiers, no
    missing ones. Drift either direction is a regression."""
    assert set(QUALITY_PRESETS.keys()) == {"Draft", "Standard", "High Quality", "Ultra"}


def test_preset_carries_orthophoto_and_dem_resolution():
    """Every preset must set both orthophoto-resolution and
    dem-resolution. Without these the downstream COG/trait pipeline
    silently misses files. All presets keep dsm enabled (main's
    behavior — `--dsm` is always passed)."""
    for name in QUALITY_PRESETS:
        out = _apply_quality_preset(name)
        assert _opt("orthophoto-resolution", out) is not None, (
            f"{name} dropped orthophoto-resolution"
        )
        assert _opt("dem-resolution", out) is not None, (
            f"{name} dropped dem-resolution"
        )
        assert _opt("dsm", out) is True, f"{name} dropped dsm"


def test_preset_orthophoto_resolution_steps_with_quality():
    """orthophoto-resolution (cm/px) must scale monotonically with
    preset fidelity: Draft coarsest, Ultra finest. A non-monotone
    sequence would mean a higher-fidelity tier produces a smaller
    ortho than a lower one.
    """
    order = ["Draft", "Standard", "High Quality", "Ultra"]
    resolutions = [
        float(_opt("orthophoto-resolution", _apply_quality_preset(n)))
        for n in order
    ]
    # cm/px: smaller = finer. Sequence must be strictly decreasing.
    assert resolutions == sorted(resolutions, reverse=True), (
        f"orthophoto-resolution not monotone across {order}: {resolutions}"
    )
    assert len(set(resolutions)) == len(resolutions), (
        f"two presets share the same orthophoto-resolution: {resolutions}"
    )


def test_returned_list_is_mutation_safe():
    """Caller mutations must not affect later calls — module state
    has to be cloned, not shared."""
    out_a = _apply_quality_preset("Draft")
    out_a.append({"name": "extra", "value": "stuff"})
    out_b = _apply_quality_preset("Draft")
    assert all(o["name"] != "extra" for o in out_b)


def test_every_preset_has_feature_quality():
    """Sanity guard: every named preset must touch the
    feature-quality flag, otherwise it isn't actually a quality preset.
    Catches typos in the QUALITY_PRESETS dict during refactors."""
    for name, overrides in QUALITY_PRESETS.items():
        names = {o["name"] for o in overrides}
        assert "feature-quality" in names, (
            f"preset {name} is missing feature-quality"
        )
