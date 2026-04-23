"""Manhattan + QQ plot generation and summary-stat computation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive; no display server inside the worker
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

logger = logging.getLogger(__name__)

GENOME_WIDE_P = 5e-8
SUGGESTIVE_P = 1e-5


@dataclass
class AssocSummary:
    n_variants: int
    p_column: str
    genomic_inflation_lambda: float
    n_genome_wide: int
    n_suggestive: int
    bonferroni_threshold: float
    n_bonferroni: int
    top_hits: list[dict]


def load_assoc(assoc_path: Path) -> tuple[pd.DataFrame, str]:
    """Load a GEMMA .assoc.txt; return (df, p_column_name).

    GEMMA's univariate output always contains one of p_wald / p_lrt / p_score.
    mvLMM output contains p_wald (multivariate).
    """
    df = pd.read_csv(assoc_path, sep=r"\s+", engine="python")
    for col in ("p_wald", "p_lrt", "p_score"):
        if col in df.columns:
            return df, col
    raise ValueError(f"No p-value column found in {assoc_path} (columns={list(df.columns)})")


def summarize(df: pd.DataFrame, p_col: str, top_n: int = 10) -> AssocSummary:
    pvals = df[p_col].dropna().to_numpy()
    pvals = pvals[(pvals > 0) & (pvals <= 1)]
    n = int(pvals.size)
    if n == 0:
        return AssocSummary(
            n_variants=0, p_column=p_col,
            genomic_inflation_lambda=float("nan"),
            n_genome_wide=0, n_suggestive=0,
            bonferroni_threshold=float("nan"), n_bonferroni=0,
            top_hits=[],
        )

    # Genomic inflation: ratio of median observed chi^2 (df=1) to expected (0.456).
    chisq = stats.chi2.isf(pvals, df=1)
    lam = float(np.median(chisq) / stats.chi2.ppf(0.5, df=1))

    bonf = 0.05 / n
    n_gw = int((pvals < GENOME_WIDE_P).sum())
    n_sug = int((pvals < SUGGESTIVE_P).sum())
    n_bonf = int((pvals < bonf).sum())

    # Top hits by ascending p.
    sorted_df = df.sort_values(p_col).head(top_n)
    hits = []
    for _, row in sorted_df.iterrows():
        hit = {
            "rs": str(row.get("rs", "")),
            "chr": int(row["chr"]) if pd.notna(row.get("chr")) else None,
            "pos": int(row["ps"]) if pd.notna(row.get("ps")) else None,
            "p": float(row[p_col]),
        }
        if "beta" in row.index and pd.notna(row["beta"]):
            hit["beta"] = float(row["beta"])
        if "se" in row.index and pd.notna(row["se"]):
            hit["se"] = float(row["se"])
        if "af" in row.index and pd.notna(row["af"]):
            hit["af"] = float(row["af"])
        hits.append(hit)

    return AssocSummary(
        n_variants=n,
        p_column=p_col,
        genomic_inflation_lambda=lam,
        n_genome_wide=n_gw,
        n_suggestive=n_sug,
        bonferroni_threshold=bonf,
        n_bonferroni=n_bonf,
        top_hits=hits,
    )


def manhattan_plot(
    df: pd.DataFrame,
    p_col: str,
    out_path: Path,
    title: Optional[str] = None,
    bonferroni: Optional[float] = None,
) -> Path:
    """Render a standard Manhattan plot."""
    d = df.dropna(subset=[p_col, "chr", "ps"]).copy()
    d = d[(d[p_col] > 0) & (d[p_col] <= 1)]
    d["chr_int"] = pd.to_numeric(d["chr"], errors="coerce").fillna(0).astype(int)
    d = d.sort_values(["chr_int", "ps"]).reset_index(drop=True)
    d["logp"] = -np.log10(d[p_col].astype(float))

    # Cumulative x so chromosomes don't overlap.
    offsets: dict[int, int] = {}
    running = 0
    xticks = []
    xticklabels = []
    for chrom, grp in d.groupby("chr_int", sort=True):
        offsets[chrom] = running
        span = int(grp["ps"].max() - grp["ps"].min() + 1)
        xticks.append(running + span // 2)
        xticklabels.append(str(chrom))
        running += span
    d["x"] = d.apply(lambda r: offsets[r["chr_int"]] + (r["ps"] - d[d["chr_int"] == r["chr_int"]]["ps"].min()), axis=1)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    palette = ["#1f77b4", "#ff7f0e"]
    for i, (chrom, grp) in enumerate(d.groupby("chr_int", sort=True)):
        ax.scatter(grp["x"], grp["logp"], s=6, color=palette[i % 2], rasterized=True)

    ax.axhline(-np.log10(SUGGESTIVE_P), color="gray", linestyle="--", linewidth=0.8, label=f"suggestive (p={SUGGESTIVE_P:.0e})")
    ax.axhline(-np.log10(GENOME_WIDE_P), color="red", linestyle="--", linewidth=0.8, label=f"genome-wide (p={GENOME_WIDE_P:.0e})")
    if bonferroni:
        ax.axhline(-np.log10(bonferroni), color="purple", linestyle=":", linewidth=0.8, label=f"Bonferroni (p={bonferroni:.2e})")

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_xlabel("Chromosome")
    ax.set_ylabel(f"-log10({p_col})")
    if title:
        ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def qq_plot(
    df: pd.DataFrame,
    p_col: str,
    out_path: Path,
    title: Optional[str] = None,
) -> Path:
    """Render a QQ plot with genomic-inflation annotation."""
    pvals = df[p_col].dropna().to_numpy()
    pvals = pvals[(pvals > 0) & (pvals <= 1)]
    pvals.sort()
    n = pvals.size
    expected = -np.log10(np.arange(1, n + 1) / (n + 1))
    observed = -np.log10(pvals)

    chisq = stats.chi2.isf(pvals, df=1)
    lam = float(np.median(chisq) / stats.chi2.ppf(0.5, df=1)) if n else float("nan")

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(expected[::-1], observed, s=6, rasterized=True)
    lim = max(float(expected.max()), float(observed.max())) if n else 1.0
    ax.plot([0, lim], [0, lim], color="red", linewidth=0.8)
    ax.set_xlabel("Expected -log10(p)")
    ax.set_ylabel("Observed -log10(p)")
    ax.set_title(f"{title or 'QQ plot'}  (λ={lam:.3f})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
