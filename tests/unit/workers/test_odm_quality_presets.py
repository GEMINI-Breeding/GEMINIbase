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


def test_default_quality_returns_defaults():
    """The 'Default' selection must produce DEFAULT_OPTIONS verbatim."""
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


def test_lowest_preset_sets_memory_friendly_flags():
    """Lowest is the only preset designed to fit in a 7-8 GiB Docker
    engine. Pin the four flags that make that possible — if any of
    them is dropped or renamed, the user gets OOMs and we should know."""
    out = _apply_quality_preset("Lowest")
    assert _opt("feature-quality", out) == "lowest"
    assert _opt("pc-quality", out) == "lowest"
    assert _opt("depthmap-resolution", out) == 320
    assert _opt("max-concurrency", out) == 4


def test_medium_preset_sets_intermediate_flags():
    out = _apply_quality_preset("Medium")
    assert _opt("feature-quality", out) == "medium"
    assert _opt("pc-quality", out) == "medium"
    assert _opt("depthmap-resolution", out) == 640


def test_ultra_preset_sets_full_quality_flags():
    out = _apply_quality_preset("Ultra")
    assert _opt("feature-quality", out) == "ultra"
    assert _opt("pc-quality", out) == "ultra"
    assert _opt("depthmap-resolution", out) == 1280


def test_preset_preserves_default_baseline_keys():
    """Every preset must keep the DEFAULT_OPTIONS baseline keys
    (orthophoto-resolution, dem-resolution, dsm) — otherwise the
    downstream COG/trait pipeline silently misses files."""
    for name in QUALITY_PRESETS:
        out = _apply_quality_preset(name)
        assert _opt("orthophoto-resolution", out) == 0.25, (
            f"{name} dropped orthophoto-resolution"
        )
        assert _opt("dem-resolution", out) == 0.25, (
            f"{name} dropped dem-resolution"
        )
        assert _opt("dsm", out) is True, f"{name} dropped dsm"


def test_returned_list_is_mutation_safe():
    """Caller mutations must not affect later calls — module state
    has to be cloned, not shared."""
    out_a = _apply_quality_preset("Lowest")
    out_a.append({"name": "extra", "value": "stuff"})
    out_b = _apply_quality_preset("Lowest")
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
