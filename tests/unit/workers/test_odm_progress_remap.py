"""
Unit tests for the ODM worker's progress remap.

NodeODM's `progress` field is the linear sum of ODM stage weights
(/code/stages/odm_app.py: dataset 0-5, opensfm 5-25, openmvs 25-50, ...).
On real flights opensfm + openmvs typically consume ~70% of wall-clock
time but only span 5-50 in ODM progress, so a linear remap to the UI's
20-85 band makes the bar appear stuck at ~23% for half the run.

`_remap_odm_progress` applies a piecewise-linear curve that gives those
slow stages more visible motion. These tests pin the curve so future
refactors don't silently flatten it back into a linear mapping.
"""
from gemini.workers.odm.worker import (
    _remap_odm_progress,
    _segment_ceiling,
    _smooth_progress,
)


def test_zero_maps_to_band_floor():
    assert _remap_odm_progress(0) == 20


def test_hundred_maps_to_band_ceiling():
    assert _remap_odm_progress(100) == 85


def test_breakpoints_match_stage_boundaries():
    """The breakpoints are aligned with ODM stage transitions so the bar
    advances at each stage end. Pin them so a refactor doesn't drift."""
    assert _remap_odm_progress(5) == 23  # end of dataset
    assert _remap_odm_progress(25) == 48  # end of opensfm
    assert _remap_odm_progress(50) == 65  # end of openmvs


def test_opensfm_band_is_wider_than_linear():
    """Opensfm covers ODM 5-25 (20 ODM points) and routinely consumes
    30-50% of wall-clock. The remap should give it more than its natural
    20-point share of the UI band — the whole point of this helper.
    Linear would put 25% ODM at ~36 UI; the remap puts it at 48."""
    linear = 20 + (25 / 100.0) * 65  # = 36.25
    assert _remap_odm_progress(25) > linear


def test_openmvs_band_is_wider_than_linear():
    """Same reasoning for openmvs (ODM 25-50)."""
    linear = 20 + (50 / 100.0) * 65  # = 52.5
    assert _remap_odm_progress(50) > linear


def test_monotonic_across_full_range():
    """Progress must never go backwards as ODM advances; otherwise the UI
    would render a regressing bar, which looks broken."""
    prev = -1.0
    for p in range(0, 101):
        v = _remap_odm_progress(p)
        assert v >= prev, f"regressed at ODM={p}: {v} < {prev}"
        prev = v


def test_clamps_below_zero():
    """ODM occasionally reports negative progress for a frame or two
    after a stage transition. Don't crash, don't go below the floor."""
    assert _remap_odm_progress(-10) == 20


def test_clamps_above_hundred():
    """Defensive: NodeODM has been observed to briefly report 101 during
    transitions. Don't escape the UI band ceiling."""
    assert _remap_odm_progress(150) == 85


def test_midway_in_opensfm_is_reasonable():
    """ODM 15 is mid-opensfm. The user should see distinct motion from
    the start of opensfm (UI 23) by then."""
    v = _remap_odm_progress(15)
    assert 30 < v < 45, f"ODM 15 → UI {v} feels stuck near the floor"


# ── Segment-ceiling + asymptotic plateau-creep ─────────────────────────────
#
# The piecewise remap alone can't fix the user-visible "stuck bar" problem
# because NodeODM's `progress` field itself plateaus within a stage — one
# real flight reported only 5 distinct progress values across 14 minutes of
# opensfm. `_smooth_progress` adds time-based creep on top of the static
# remap so the bar keeps moving while NodeODM sits on the same chunk.


def test_segment_ceiling_at_breakpoint_advances():
    """At an exact breakpoint we're entering the next segment, so the
    ceiling should be the *next* breakpoint's UI value, not the current."""
    assert _segment_ceiling(5) == 48   # entering opensfm → ceiling at end
    assert _segment_ceiling(25) == 65  # entering openmvs → ceiling at end


def test_segment_ceiling_inside_segment():
    """Mid-segment lookups return the same ceiling as the segment start."""
    assert _segment_ceiling(15) == 48  # mid-opensfm
    assert _segment_ceiling(40) == 65  # mid-openmvs
    assert _segment_ceiling(70) == 85  # mid-tail


def test_segment_ceiling_at_end_returns_band_ceiling():
    """ODM=100 sits at the band ceiling — no further segment to climb."""
    assert _segment_ceiling(100) == 85


def test_smooth_no_creep_at_zero_elapsed():
    """First poll on a new plateau has elapsed=0 — must report the static
    remap value, not bias upward."""
    assert _smooth_progress(odm_progress=5, plateau_elapsed=0, last_reported=0) == 23


def test_smooth_creeps_within_segment_over_time():
    """As elapsed grows, the smoothed value should asymptotically approach
    (but not reach) the segment ceiling. With tau=300 the half-life is 5
    minutes, so by 5 min we should be ~halfway from base to ceiling-1."""
    base = _remap_odm_progress(5)         # 23
    ceiling = _segment_ceiling(5) - 1     # 47 (1pt headroom)
    headroom = ceiling - base             # 24
    v_1min = _smooth_progress(5, 60, 0, tau=300)
    v_5min = _smooth_progress(5, 300, 0, tau=300)
    v_15min = _smooth_progress(5, 900, 0, tau=300)
    # 1 min → ~17% of headroom (60/360)
    assert base + 3 < v_1min < base + 6
    # 5 min → 50% of headroom (300/600)
    assert v_5min == base + headroom * 0.5
    # 15 min → 75% of headroom (900/1200)
    assert v_15min == base + headroom * 0.75
    # Never crosses ceiling
    assert _smooth_progress(5, 10_000_000, 0, tau=300) < base + headroom + 0.001


def test_smooth_never_regresses_on_rebase():
    """When ODM finally ticks to the next value, the new static base may be
    *below* what we've already smoothed up to. The bar must not go
    backwards — `last_reported` is the floor."""
    # Smoothed at odm=5 for 10 minutes → say ~38
    smoothed = _smooth_progress(5, 600, 0, tau=300)
    assert smoothed > 30
    # Now ODM ticks to 6.6 (still in opensfm); base=25 — but we should not
    # regress to 25 even though plateau_elapsed resets to 0.
    rebased = _smooth_progress(6.6, 0, smoothed, tau=300)
    assert rebased == smoothed


def test_smooth_completion_reaches_band_ceiling():
    """When ODM hits 100 and we report one final smoothed value, the bar
    should land at the 85 ceiling — no awkward 84.x finish."""
    assert _smooth_progress(100, 0, 0) == 85


def test_smooth_solves_real_world_stuck_plateau():
    """Regression: real flight where ODM sat at progress=5 for 14 minutes
    of opensfm. With the old code the bar stayed at 23%. With smoothing
    it should be visibly above 23 within the first minute and well past
    30 after a few minutes — even though the underlying ODM value
    hasn't budged."""
    base = _remap_odm_progress(5)  # 23
    after_1min = round(_smooth_progress(5, 60, 0, tau=300))
    after_5min = round(_smooth_progress(5, 300, 0, tau=300))
    after_14min = round(_smooth_progress(5, 14 * 60, 0, tau=300))
    assert after_1min > base
    assert after_5min >= base + 10
    assert after_14min >= base + 15
