"""
Integration-style tests for the ODM worker's poll-loop smoothing.

The unit tests in `test_odm_progress_remap.py` pin the static remap and the
`_smooth_progress` helper in isolation. Those helpers were correct on their
own — but the bug they were meant to fix kept reappearing in production
because the *poll loop* tracked plateau-elapsed against the raw NodeODM
`progress` field, which jitters in tiny sub-percent steps inside a single
ODM stage. Every jitter reset `plateau_start` to "now", `plateau_elapsed`
never grew, and the asymptotic creep never fired. The bar sat at 23% for
6 minutes, then 25% for 9 minutes, exactly mirroring `_remap_odm_progress`
of NodeODM's chunky output — with no smoothing on top.

These tests pump realistic ODM progress sequences through the same
plateau-tracking logic the worker uses (segment-ceiling keyed) and assert
the UI value visibly creeps within the segment, even when ODM ticks.
"""
import math

from gemini.workers.odm.worker import (
    _remap_odm_progress,
    _segment_ceiling,
    _smooth_progress,
)


def _simulate_poll_loop(odm_progress_timeline: list[tuple[float, float]]) -> list[int]:
    """Replay the poll loop's smoothing against a (time_seconds, odm_progress)
    timeline and return the rounded UI values it would have reported.

    Mirrors the logic in `OdmWorker._poll_nodeodm` exactly: plateau tracked
    by segment ceiling, last_smoothed monotonically updated.
    """
    prev_segment_ceiling: float | None = None
    plateau_start = 0.0
    last_smoothed = 0.0
    reported: list[int] = []

    for now, odm_progress in odm_progress_timeline:
        current_ceiling = _segment_ceiling(odm_progress)
        if prev_segment_ceiling is None or current_ceiling != prev_segment_ceiling:
            plateau_start = now
            prev_segment_ceiling = current_ceiling
        plateau_elapsed = now - plateau_start
        smoothed = _smooth_progress(odm_progress, plateau_elapsed, last_smoothed)
        last_smoothed = smoothed
        reported.append(round(smoothed))

    return reported


def test_jittery_odm_within_opensfm_still_creeps():
    """Regression for the production "stuck at 23%" report.

    NodeODM walked progress 5.0 → 5.0 → 5.0 → 5.4 → 5.4 → 6.6 over six
    minutes of opensfm. Previously the loop reset plateau on every tick,
    producing a flat 23 the whole time. With segment-keyed plateau the
    bar must climb visibly (≥5 UI points) inside the segment, since
    every value here maps to the same segment (opensfm, ceiling 48).
    """
    timeline = []
    for second in range(0, 6 * 60 + 1, 5):  # 5 s polls, 6 minutes
        if second < 60:
            p = 5.0
        elif second < 180:
            p = 5.4
        elif second < 240:
            p = 6.0
        else:
            p = 6.6
        timeline.append((float(second), p))

    reported = _simulate_poll_loop(timeline)

    assert reported[0] == 23, f"first poll should remap 5.0 → 23, got {reported[0]}"
    final = reported[-1]
    assert final >= 28, (
        f"after 6 min stuck inside opensfm the bar should creep "
        f"≥5 points beyond 23, got {final}"
    )
    # Monotonic — the bar must never go backwards.
    for i in range(1, len(reported)):
        assert reported[i] >= reported[i - 1], (
            f"regressed at poll {i}: {reported[i]} < {reported[i - 1]}"
        )


def test_segment_crossing_re_seats_creep_window():
    """When ODM genuinely crosses into the next stage (opensfm → openmvs at
    p=25), plateau should reset so the new segment gets its own creep
    budget. Otherwise old elapsed time would let us shoot to the new
    ceiling instantly."""
    timeline = []
    # 10 minutes inside opensfm at p=20.
    for second in range(0, 10 * 60, 5):
        timeline.append((float(second), 20.0))
    # Cross into openmvs.
    crossing_time = 10 * 60
    timeline.append((float(crossing_time), 25.0))
    # 5 s after crossing, still at p=25 — fresh plateau.
    timeline.append((float(crossing_time + 5), 25.0))

    reported = _simulate_poll_loop(timeline)

    pre_cross = reported[-3]
    at_cross = reported[-2]
    just_after = reported[-1]

    # We never regress.
    assert at_cross >= pre_cross
    assert just_after >= at_cross

    # Just after the crossing, the smoothed value should be near the new
    # segment's static base (48) but not yet shoot deep into it — the
    # creep window was reset, so 5 s of elapsed buys almost nothing on
    # top of `last_smoothed`.
    assert just_after - at_cross <= 1, (
        f"crossing into a new segment should not jump the bar by >1 point "
        f"in 5 s; saw {at_cross} → {just_after}"
    )


def test_no_smoothing_when_odm_advances_quickly():
    """Sanity: when ODM advances steadily through opensfm in chunky steps
    every 5 s, the bar should track the static remap (no big creep added)
    because plateau-elapsed never grows much before the segment ceiling
    changes via crossing... but here we stay in the same segment, so the
    creep does accumulate slightly. The assertion is just that we follow
    the static curve roughly."""
    timeline = [(float(i * 5), float(p)) for i, p in enumerate(range(5, 25))]
    reported = _simulate_poll_loop(timeline)

    # Final report should be at least the static remap of the final ODM
    # value, possibly higher due to in-segment creep — never lower.
    final_static = _remap_odm_progress(timeline[-1][1])
    assert reported[-1] >= round(final_static) - 1
    # And monotonic.
    for i in range(1, len(reported)):
        assert reported[i] >= reported[i - 1]


def test_real_world_log_replay_no_longer_stuck():
    """Replay of the user-reported flight: ODM sat at 5.0 from t=0 to
    t=395 s, then 6.6 from t=395 s to t=905 s. Old code reported 23
    then 25 with no in-between motion. New code must report a visible
    climb inside both plateaus *and* never regress when ODM ticks."""
    timeline = []
    for second in range(0, 395, 5):
        timeline.append((float(second), 5.0))
    for second in range(395, 905, 5):
        timeline.append((float(second), 6.6))

    reported = _simulate_poll_loop(timeline)

    # Initial poll: static remap of 5.0 = 23.
    assert reported[0] == 23

    # 6 minutes into the first plateau, the bar must have moved.
    # poll cadence 5 s → index for t=360 is 72.
    assert reported[72] >= 28, (
        f"after 6 min stuck at ODM=5.0 the bar should be ≥28, got {reported[72]}"
    )

    # Final poll (t≈900) must be well above 25 — the user-reported
    # endpoint of the second plateau under the broken code.
    final = reported[-1]
    assert final >= 35, f"expected significant creep by t=900s, got {final}"

    # Monotonic across the entire timeline.
    for i in range(1, len(reported)):
        assert reported[i] >= reported[i - 1]
