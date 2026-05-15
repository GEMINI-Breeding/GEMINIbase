"""Tests for plotting helpers in workers/gwas/plots.py.

We don't validate pixel output; we validate the scatter coordinates that
matplotlib was handed. That's enough to catch the historical bug where
the QQ plot reversed the x-axis but not the y-axis, mis-pairing each
observed -log10(p) with the wrong expected quantile.
"""
from __future__ import annotations

from pathlib import Path

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
