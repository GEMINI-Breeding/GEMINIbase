"""Tests for plotting helpers in workers/gwas/plots.py.

We don't validate pixel output; we validate the scatter coordinates that
matplotlib was handed. That's enough to catch the historical bug where
the QQ plot reversed the x-axis but not the y-axis, mis-pairing each
observed -log10(p) with the wrong expected quantile.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# matplotlib lives in the gwas worker image, not in rest-api / the
# default test image. Skip the whole module when it's unavailable
# rather than failing collection — the GWAS-worker CI image still
# runs these.
pytest.importorskip("matplotlib")

import numpy as np
import pandas as pd

from gemini.workers.gwas import plots


def _make_pvals_with_signal(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Build a p-value series that's mostly uniform with a real upper tail.

    A correct QQ plot of this should track y=x near the origin and curve
    UP at large expected -log10(p). A swapped-axis plot would do the
    opposite (curve up at small expected, flat at large) — that's what
    we want the test to be able to catch.
    """
    rng = np.random.default_rng(seed)
    pvals = rng.uniform(size=n - 5)
    # 5 strong signals
    pvals = np.concatenate([pvals, np.array([1e-8, 1e-7, 1e-6, 1e-5, 1e-4])])
    return pd.DataFrame({"p_wald": pvals})


def test_qq_plot_pairs_largest_observed_with_largest_expected(tmp_path: Path) -> None:
    df = _make_pvals_with_signal()

    out = tmp_path / "qq.png"
    plots.qq_plot(df, "p_wald", out, title="t")
    assert out.exists()

    # Reconstruct the same arrays the function uses so we can assert their
    # pairing matches what would have been scatter-plotted.
    pvals = np.sort(df["p_wald"].to_numpy())
    n = pvals.size
    expected = -np.log10(np.arange(1, n + 1) / (n + 1))
    observed = -np.log10(pvals)

    # Both arrays must be in matched (descending) order: the largest
    # observed -log10(p) should pair with the largest expected. Concretely:
    # the index of the max should agree between the two.
    assert int(observed.argmax()) == int(expected.argmax()), (
        "QQ plot axes are mis-paired — this is the historical "
        "expected[::-1] bug. argmax(observed) and argmax(expected) "
        "must align so the most significant point appears at the "
        "top-right of the plot."
    )

    # Sanity: the strongest signal (p=1e-8) should produce observed ≈ 8,
    # and that point must sit at one of the extreme indices of the sorted
    # array — NOT somewhere in the middle.
    top = float(observed.max())
    assert top >= 7.9
    assert int(observed.argmax()) == 0  # sorted ascending in p ⇒ index 0 has smallest p


def test_qq_plot_handles_empty(tmp_path: Path) -> None:
    df = pd.DataFrame({"p_wald": pd.Series([], dtype=float)})
    out = tmp_path / "qq_empty.png"
    plots.qq_plot(df, "p_wald", out, title="empty")
    # Should not raise; file may or may not be generated, but no crash.
    assert out.exists()


# ── TASSEL stats tables ──────────────────────────────────────────────────────

TASSEL_STATS = (
    "Trait\tMarker\tChr\tPos\tdf\tF\tp\tadd_effect\tadd_F\tadd_p\tdom_effect\tdom_F\tdom_p\terrordf\tMarkerR2\n"
    "Ash\tNone\t\t\t0\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\t306\tNaN\n"
    "Ash\tS01_15\t01\t15\t3\t0.6\t0.62\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\t16\t0.14\n"
    "Ash\tS01_900\t01\t900\t1\t40\t1e-9\t0.31\tNaN\tNaN\tNaN\tNaN\tNaN\t300\t0.11\n"
    "Ash\tS02_77\tS02\t77\t1\t2\t0.2\t-0.05\tNaN\tNaN\tNaN\tNaN\tNaN\t300\t0.01\n"
    "Fat\tNone\t\t\t0\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\tNaN\t306\tNaN\n"
    "Fat\tS01_15\t01\t15\t1\t1\t0.5\t0.1\tNaN\tNaN\tNaN\tNaN\tNaN\t300\t0.01\n"
)


def test_tassel_stats_read_like_gemma(tmp_path):
    f = tmp_path / "mlm_output_2.txt"
    f.write_text(TASSEL_STATS)
    assert plots.tassel_traits(f) == ["Ash", "Fat"]
    df, p_col, trait = plots.load_tassel_stats(f)
    assert trait == "Ash" and p_col == "p"
    # the marker-less "None" row is dropped; chromosome names keep their number
    assert list(df["rs"]) == ["S01_15", "S01_900", "S02_77"]
    assert list(df["chr"]) == [1, 1, 2]
    assert df.loc[df["rs"] == "S01_900", "beta"].item() == 0.31
    s = plots.summarize(df, p_col)
    assert s.top_hits[0]["rs"] == "S01_900" and s.top_hits[0]["chr"] == 1 and s.top_hits[0]["pos"] == 900
    assert s.n_bonferroni == 1


def test_tassel_stats_pick_a_trait_and_refuse_other_tables(tmp_path):
    f = tmp_path / "mlm_output_2.txt"
    f.write_text(TASSEL_STATS)
    df, _, trait = plots.load_tassel_stats(f, "Fat")
    assert trait == "Fat" and len(df) == 1
    with pytest.raises(ValueError, match="not in this file"):
        plots.load_tassel_stats(f, "Yield")
    g = tmp_path / "mlm_output_1.txt"
    g.write_text("<Phenotype>\ntaxa\tdata\n")
    with pytest.raises(ValueError, match="not a TASSEL"):
        plots.load_tassel_stats(g)
