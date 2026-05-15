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

    # Cumulative x so chromosomes don't overlap. We compute the
    # per-chromosome offset and per-chromosome min(ps) in one pass,
    # then vectorise the x assignment via map+subtract. The previous
    # row-wise df.apply implementation crashed with "Cannot set a
    # DataFrame with multiple columns to the single column x" on
    # certain GEMMA outputs (the lambda's inner `d[mask]["ps"]`
    # silently returns a DataFrame when the source has any duplicate
    # column name, propagating up through the subtraction). The
    # vectorised form has no such failure mode and is ~100× faster
    # on real-world variant counts.
    offsets: dict[int, int] = {}
    chrom_min_ps: dict[int, int] = {}
    running = 0
    xticks = []
    xticklabels = []
    for chrom, grp in d.groupby("chr_int", sort=True):
        offsets[chrom] = running
        min_ps = int(grp["ps"].min())
        max_ps = int(grp["ps"].max())
        span = max_ps - min_ps + 1
        chrom_min_ps[chrom] = min_ps
        xticks.append(running + span // 2)
        xticklabels.append(str(chrom))
        running += span
    d["x"] = (
        d["chr_int"].map(offsets).astype(int)
        + d["ps"].astype(int)
        - d["chr_int"].map(chrom_min_ps).astype(int)
    )

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


def kinship_heatmap(
    kin_path: Path,
    out_path: Path,
    title: Optional[str] = None,
) -> Path:
    """Render the GEMMA centered relatedness matrix as a clustered heatmap.

    Samples are reordered by average-linkage hierarchical clustering on
    `1 - kinship` (treating kinship as a similarity → distance), so
    related individuals fall into visible blocks. Diagonal is the
    sample's relatedness with itself; high off-diagonal values indicate
    close relatedness.

    The kinship file is a square N×N text matrix written by
    ``gemma -gk 1``; sample order matches the .fam used to generate it.
    We don't have the sample labels embedded in the file, so the axes
    are unlabelled — labelling 300+ ticks is unreadable anyway.
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    from scipy.spatial.distance import squareform

    K = pd.read_csv(kin_path, sep=r"\s+", header=None, engine="python").to_numpy()
    n = K.shape[0]
    if n == 0 or K.shape[0] != K.shape[1]:
        # Bail rather than crash: emit a 1×1 placeholder so the worker
        # uploads *something* the UI can render.
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.set_title("kinship matrix unavailable")
        ax.axis("off")
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path

    # Cluster on 1 - K (force-symmetrize to dodge floating-point asymmetry
    # in the lower triangle). squareform expects zero diagonal.
    D = 1.0 - 0.5 * (K + K.T)
    np.fill_diagonal(D, 0.0)
    # Clamp tiny negatives that come out of the symmetrization round-trip.
    D = np.clip(D, 0.0, None)
    try:
        Z = linkage(squareform(D, checks=False), method="average")
        order = leaves_list(Z)
    except Exception:
        # Degenerate matrices (e.g. all-zero off-diagonals on a single-
        # variant QC pass) can break linkage. Fall back to identity order.
        order = np.arange(n)
    K_ord = K[np.ix_(order, order)]

    fig, ax = plt.subplots(figsize=(7, 6))
    # Symmetric color scale around zero — kinship-to-self is high,
    # unrelated pairs hover near zero, half-sibs are positive but smaller.
    vmax = float(np.percentile(np.abs(K_ord), 99))
    im = ax.imshow(K_ord, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel(f"{n} samples (clustered)")
    ax.set_ylabel(f"{n} samples (clustered)")
    if title:
        ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="kinship")
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
    pvals.sort()  # ascending p → descending -log10(p) below
    n = pvals.size
    # arange/(n+1) is ascending, so -log10 of it is descending — i.e. expected[0]
    # is the LARGEST expected -log10(p). observed = -log10(sorted_p) is also
    # descending. Both arrays are already in matched (descending) order, so
    # we pair them element-wise as-is.
    expected = -np.log10(np.arange(1, n + 1) / (n + 1))
    observed = -np.log10(pvals)

    chisq = stats.chi2.isf(pvals, df=1)
    lam = float(np.median(chisq) / stats.chi2.ppf(0.5, df=1)) if n else float("nan")

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(expected, observed, s=6, rasterized=True)
    lim = max(float(expected.max()), float(observed.max())) if n else 1.0
    ax.plot([0, lim], [0, lim], color="red", linewidth=0.8)
    ax.set_xlabel("Expected -log10(p)")
    ax.set_ylabel("Observed -log10(p)")
    ax.set_title(f"{title or 'QQ plot'}  (λ={lam:.3f})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
