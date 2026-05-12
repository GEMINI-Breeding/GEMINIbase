"""Multivariate trait-analysis endpoints.

Phase 1 ships /matrix and /correlation. Subsequent phases add /spatial,
/anova, /heritability, /pca, /gge.

Design notes captured in the plan at .claude/plans/polished-shimmying-lake.md:
- JSON in / JSON out (no NDJSON; payloads are bounded after aggregation).
- Replicates are inferred from repeated `accession_name` within (experiment,
  season, site). No schema field added.
- Aggregation is user-chosen per request — no default.
- Population filtering is applied in Python because `record_info.population`
  has no first-class column today.
- Row-count guard at 500_000 rows fetched (before pivot) returns
  `{"status": "too_large", ...}` so the UI can prompt the user to narrow.
"""

from datetime import date, datetime
from typing import List, Literal, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from litestar import Response
from litestar.controller import Controller
from litestar.handlers import post
from pydantic import BaseModel, Field
from scipy.spatial import ConvexHull
from scipy.stats import spearmanr

from gemini.api.trait_record import TraitRecord
from gemini.rest_api.models import RESTAPIBase, RESTAPIError


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

Aggregation = Literal["mean", "latest", "max", "min", "first", "date"]

ROW_LIMIT = 500_000


class MultivariateRequest(RESTAPIBase):
    """Shared request body for every multivariate endpoint.

    Filters use *names* (not IDs) to match the rest of the REST API.

    Two collapses can run sequentially:
    1. `aggregation` collapses multiple records on the SAME plot across
       different timestamps. Default "mean" — no-op when each plot has
       one record.
    2. `collapse_replicates`, when true, then averages across replicate
       plots that share `accession_name` within each (experiment, season,
       site). The output has one row per (accession × env).
    """

    trait_names: List[str] = Field(..., min_length=1)
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None
    populations: Optional[List[str]] = None
    aggregation: Aggregation = "mean"
    aggregation_date: Optional[date] = None
    collapse_replicates: bool = False


class TraitMatrixRow(RESTAPIBase):
    plot_id: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    accession_name: Optional[str] = None
    population: Optional[str] = None
    values: dict  # {trait_name: float | None}


class MatrixResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    n_records_fetched: int
    n_rows: int
    trait_names: List[str]
    rows: List[TraitMatrixRow]
    message: Optional[str] = None


class CorrelationMatrix(RESTAPIBase):
    trait_names: List[str]
    # rows aligned to trait_names; matrix[i][j] is corr(trait_i, trait_j)
    matrix: List[List[Optional[float]]]
    # n[i][j] = number of complete pairs used for cell (i, j)
    n: List[List[int]]


class CorrelationResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    n_rows: int
    pearson: Optional[CorrelationMatrix] = None
    spearman: Optional[CorrelationMatrix] = None
    message: Optional[str] = None


class SpatialCell(RESTAPIBase):
    plot_row_number: int
    plot_column_number: int
    value: float
    accession_name: Optional[str] = None
    plot_number: Optional[int] = None


class SpatialSite(RESTAPIBase):
    site_name: Optional[str] = None
    n_cells: int
    min_row: int
    max_row: int
    min_col: int
    max_col: int
    value_min: float
    value_max: float
    cells: List[SpatialCell]


class SpatialResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    trait_name: str
    n_records_fetched: int
    sites: List[SpatialSite]
    message: Optional[str] = None


class AnovaTerm(RESTAPIBase):
    term: str
    df: float
    sum_sq: float
    mean_sq: float
    F: Optional[float] = None
    p: Optional[float] = None
    eta_sq: Optional[float] = None


class AnovaPanel(RESTAPIBase):
    trait_name: str
    # For one-way panels env identifies the (experiment, season, site) triple
    # joined with " · ". For two-way it's the literal string "two-way".
    env_label: str
    kind: Literal["one_way", "two_way"]
    n_obs: int
    n_groups: int  # accessions
    replication_status: Literal["replicated", "unreplicated", "insufficient_data"]
    terms: List[AnovaTerm]
    message: Optional[str] = None


class AnovaResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    n_records_fetched: int
    panels: List[AnovaPanel]
    message: Optional[str] = None


class BLUP(RESTAPIBase):
    accession_name: str
    blup: float


class HeritabilityPanel(RESTAPIBase):
    trait_name: str
    env_label: str
    n_obs: int
    n_groups: int
    mean_reps: float
    var_g: Optional[float] = None
    var_e: Optional[float] = None
    h2: Optional[float] = None
    convergence_status: Literal["ok", "warning", "failed", "unreplicated", "insufficient_data"]
    blups: List[BLUP] = []
    message: Optional[str] = None


class HeritabilityResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    n_records_fetched: int
    panels: List[HeritabilityPanel]
    message: Optional[str] = None


class PCAScore(RESTAPIBase):
    # `id` is whatever uniquely keys the row (plot_id when per-plot,
    # accession_name when replicates were collapsed).
    id: str
    label: Optional[str] = None
    accession_name: Optional[str] = None
    population: Optional[str] = None
    experiment_name: Optional[str] = None
    site_name: Optional[str] = None
    components: List[float]  # length k


class PCALoading(RESTAPIBase):
    trait_name: str
    components: List[float]  # length k


class PCAResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    n_records_fetched: int
    n_components: int
    explained_variance_ratio: List[float]
    scores: List[PCAScore]
    loadings: List[PCALoading]
    trait_names: List[str]
    row_kind: Literal["plot", "accession"]
    message: Optional[str] = None


class GGEPoint(RESTAPIBase):
    name: str
    pc1: float
    pc2: float


class GGEResponse(RESTAPIBase):
    status: Literal["ok", "too_large", "insufficient_data"]
    trait_name: str
    n_records_fetched: int
    n_accessions: int
    n_envs: int
    explained_variance_ratio: List[float]  # PC1, PC2, …
    accession_scores: List[GGEPoint]
    env_scores: List[GGEPoint]
    polygon: List[str]  # which-won-where polygon vertices (ordered accession names)
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared data-fetch + aggregation helpers
# ---------------------------------------------------------------------------


def _fetch_long(req: MultivariateRequest) -> tuple[pd.DataFrame, int]:
    """Pull the long-form trait-record frame and the raw fetched-count.

    Applies the population filter in Python (no indexed JSON path today).
    """

    records = TraitRecord.filter(
        trait_names=req.trait_names,
        experiment_names=req.experiment_names,
        season_names=req.season_names,
        site_names=req.site_names,
    )

    rows: list[dict] = []
    n_fetched = 0
    for r in records:
        n_fetched += 1
        if n_fetched > ROW_LIMIT:
            # Bail early — don't materialize huge frames.
            return pd.DataFrame(), n_fetched

        pop = None
        if r.record_info:
            pop_val = r.record_info.get("population")
            if pop_val is not None:
                pop = str(pop_val)

        if req.populations and pop not in req.populations:
            continue

        rows.append({
            "plot_id": str(r.plot_id) if r.plot_id else None,
            "plot_number": r.plot_number,
            "plot_row_number": r.plot_row_number,
            "plot_column_number": r.plot_column_number,
            "experiment_name": r.experiment_name,
            "season_name": r.season_name,
            "site_name": r.site_name,
            "accession_name": r.accession_name,
            "population": pop,
            "trait_name": r.trait_name,
            "trait_value": r.trait_value,
            "timestamp": r.timestamp,
            "collection_date": r.collection_date,
        })

    return pd.DataFrame(rows), n_fetched


def _aggregate_per_plot(df: pd.DataFrame, req: MultivariateRequest) -> pd.DataFrame:
    """Collapse multiple measurements per (plot, trait) into one value.

    Returns a wide DataFrame keyed by (plot_id, experiment_name, season_name,
    site_name, accession_name, population, plot_number, plot_row_number,
    plot_column_number) with one column per trait_name.
    """

    if df.empty:
        return df

    key_cols = [
        "plot_id",
        "plot_number",
        "plot_row_number",
        "plot_column_number",
        "experiment_name",
        "season_name",
        "site_name",
        "accession_name",
        "population",
    ]

    work = df.copy()

    if req.aggregation == "date":
        if req.aggregation_date is None:
            raise ValueError("aggregation_date is required when aggregation == 'date'")
        work["_cd"] = pd.to_datetime(work["collection_date"]).dt.date
        work = work[work["_cd"] == req.aggregation_date]
        work.drop(columns=["_cd"], inplace=True)
        # After filtering to one date, take the mean for any remaining dups.
        agg_fn = "mean"
        sort_col = None
    elif req.aggregation == "mean":
        agg_fn = "mean"
        sort_col = None
    elif req.aggregation == "max":
        agg_fn = "max"
        sort_col = None
    elif req.aggregation == "min":
        agg_fn = "min"
        sort_col = None
    elif req.aggregation == "latest":
        agg_fn = None
        sort_col = ("timestamp", False)  # descending → first() picks latest
    elif req.aggregation == "first":
        agg_fn = None
        sort_col = ("timestamp", True)
    else:
        raise ValueError(f"Unknown aggregation: {req.aggregation}")

    if sort_col is not None:
        work = work.sort_values(sort_col[0], ascending=sort_col[1])
        collapsed = (
            work.groupby(key_cols + ["trait_name"], dropna=False)["trait_value"]
            .first()
            .reset_index()
        )
    else:
        collapsed = (
            work.groupby(key_cols + ["trait_name"], dropna=False)["trait_value"]
            .agg(agg_fn)
            .reset_index()
        )

    # pivot_table builds its row index from every key column. If a key column
    # is entirely null (e.g. plot_id missing for trait-only imports), an
    # all-NaN MultiIndex collapses to a single row that pivot_table then
    # drops, returning empty. Restrict the index to columns that carry info
    # for this query — usually accession_name + the env keys.
    index_cols = [c for c in key_cols if collapsed[c].notna().any()]
    if not index_cols:
        # No grouping key left — every record is "the same plot". Fall back
        # to a synthetic row index so the pivot keeps the values.
        collapsed["_row"] = range(len(collapsed))
        index_cols = ["_row"]
    wide = collapsed.pivot_table(
        index=index_cols,
        columns="trait_name",
        values="trait_value",
        aggfunc="first",
    ).reset_index()

    # Re-attach the dropped-null key columns as NaN so downstream callers
    # see a stable schema.
    for c in key_cols:
        if c not in wide.columns:
            wide[c] = None
    if "_row" in wide.columns:
        wide.drop(columns=["_row"], inplace=True)

    wide.columns.name = None

    if req.collapse_replicates:
        wide = _collapse_replicates(wide, [
            t for t in req.trait_names if t in wide.columns
        ])

    return wide


def _collapse_replicates(
    wide: pd.DataFrame,
    trait_cols: List[str],
) -> pd.DataFrame:
    """Average replicate plots that share accession_name within each env.

    The output has one row per (accession × experiment × season × site).
    Spatial columns (plot_id / plot_number / row / column) are nulled
    because they're not meaningful for a per-accession mean.

    If no rows have accession_name (e.g. trait CSV without an accession
    column), the collapse can't form groups — return the input unchanged so
    downstream analyses just see per-plot rows. This makes the toggle a
    silent no-op for data shapes that don't support genotype-level grouping.
    """
    if wide.empty:
        return wide

    if not wide["accession_name"].notna().any():
        return wide

    work = wide[wide["accession_name"].notna()].copy()

    env_cols = ["experiment_name", "season_name", "site_name"]
    grp_cols = ["accession_name"] + env_cols

    aggregations = {c: "mean" for c in trait_cols}
    # Keep population if present (single value per accession is typical;
    # ties just pick the first).
    if "population" in work.columns:
        aggregations["population"] = "first"

    collapsed = work.groupby(grp_cols, dropna=False).agg(aggregations).reset_index()

    # Spatial / plot identity is meaningless after collapse — null it out so
    # downstream code (e.g. SpatialHeatmap) doesn't mistakenly try to grid it.
    for c in ["plot_id", "plot_number", "plot_row_number", "plot_column_number"]:
        if c not in collapsed.columns:
            collapsed[c] = None
        else:
            collapsed[c] = None

    return collapsed


def _wide_to_rows(wide: pd.DataFrame, trait_names: List[str]) -> List[TraitMatrixRow]:
    if wide.empty:
        return []
    out: list[TraitMatrixRow] = []
    for _, r in wide.iterrows():
        values: dict[str, Optional[float]] = {}
        for t in trait_names:
            v = r.get(t)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                values[t] = None
            else:
                values[t] = float(v)
        out.append(TraitMatrixRow(
            plot_id=r.get("plot_id"),
            plot_number=_to_int(r.get("plot_number")),
            plot_row_number=_to_int(r.get("plot_row_number")),
            plot_column_number=_to_int(r.get("plot_column_number")),
            experiment_name=r.get("experiment_name"),
            season_name=r.get("season_name"),
            site_name=r.get("site_name"),
            accession_name=r.get("accession_name"),
            population=r.get("population"),
            values=values,
        ))
    return out


def _to_int(v) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _build_spatial_sites(wide: pd.DataFrame, trait_name: str) -> List[SpatialSite]:
    """Group the aggregated wide frame into per-site SpatialSite payloads.

    Drops rows that lack plot_row_number / plot_column_number — those can't
    be placed on a field grid. If no rows survive, returns [].
    """

    if wide.empty or trait_name not in wide.columns:
        return []

    grid = wide.dropna(subset=["plot_row_number", "plot_column_number", trait_name])
    if grid.empty:
        return []

    sites: list[SpatialSite] = []
    for site_name, sub in grid.groupby("site_name", dropna=False):
        rows_arr = sub["plot_row_number"].astype(int)
        cols_arr = sub["plot_column_number"].astype(int)
        vals = sub[trait_name].astype(float)
        cells = [
            SpatialCell(
                plot_row_number=int(r),
                plot_column_number=int(c),
                value=float(v),
                accession_name=acc if isinstance(acc, str) else None,
                plot_number=_to_int(pn),
            )
            for r, c, v, acc, pn in zip(
                rows_arr,
                cols_arr,
                vals,
                sub["accession_name"],
                sub["plot_number"],
            )
        ]
        sites.append(SpatialSite(
            site_name=site_name if isinstance(site_name, str) else None,
            n_cells=len(cells),
            min_row=int(rows_arr.min()),
            max_row=int(rows_arr.max()),
            min_col=int(cols_arr.min()),
            max_col=int(cols_arr.max()),
            value_min=float(vals.min()),
            value_max=float(vals.max()),
            cells=cells,
        ))

    return sites


def _env_label(row) -> str:
    parts = [
        str(row.get("experiment_name") or ""),
        str(row.get("season_name") or ""),
        str(row.get("site_name") or ""),
    ]
    return " · ".join(p for p in parts if p) or "(no env)"


def _replication_status(group: pd.DataFrame) -> str:
    """Per-env replication: accession has >1 plot in this env."""
    if group.empty:
        return "insufficient_data"
    counts = group.groupby("accession_name", dropna=False).size()
    counts = counts[counts.index.notna()]
    if counts.empty or (counts > 1).sum() == 0:
        return "unreplicated"
    return "replicated"


def _terms_from_anova_table(tbl: pd.DataFrame, ss_total: float) -> List[AnovaTerm]:
    """Convert a statsmodels ANOVA table into AnovaTerm rows + eta² of total."""
    out: list[AnovaTerm] = []
    for term, row in tbl.iterrows():
        df_val = float(row.get("df", 0.0))
        sum_sq = float(row.get("sum_sq", 0.0))
        mean_sq = sum_sq / df_val if df_val > 0 else 0.0
        F_val = row.get("F")
        p_val = row.get("PR(>F)")
        F_out = None if F_val is None or (isinstance(F_val, float) and np.isnan(F_val)) else float(F_val)
        p_out = None if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)) else float(p_val)
        eta = sum_sq / ss_total if ss_total > 0 else None
        out.append(AnovaTerm(
            term=str(term),
            df=df_val,
            sum_sq=sum_sq,
            mean_sq=mean_sq,
            F=F_out,
            p=p_out,
            eta_sq=eta,
        ))
    return out


def _one_way_panel(trait_name: str, env_label: str, sub: pd.DataFrame) -> AnovaPanel:
    """trait_value ~ C(accession_name) per env."""
    work = sub[["accession_name", trait_name]].dropna()
    work = work[work["accession_name"].notna()]
    n_obs = int(len(work))
    n_groups = int(work["accession_name"].nunique())
    rep = _replication_status(sub)

    if n_obs < 2 or n_groups < 2:
        return AnovaPanel(
            trait_name=trait_name,
            env_label=env_label,
            kind="one_way",
            n_obs=n_obs,
            n_groups=n_groups,
            replication_status="insufficient_data",
            terms=[],
            message="Need at least 2 accessions with values to run ANOVA.",
        )
    if rep == "unreplicated":
        return AnovaPanel(
            trait_name=trait_name,
            env_label=env_label,
            kind="one_way",
            n_obs=n_obs,
            n_groups=n_groups,
            replication_status="unreplicated",
            terms=[],
            message="No accession has more than one plot in this env — F is undefined.",
        )

    # Rename column to a syntactically-safe placeholder for the formula.
    df = work.rename(columns={trait_name: "_y"})
    model = smf.ols("_y ~ C(accession_name)", data=df).fit()
    tbl = sm.stats.anova_lm(model, typ=1)
    ss_total = float(tbl["sum_sq"].sum())
    return AnovaPanel(
        trait_name=trait_name,
        env_label=env_label,
        kind="one_way",
        n_obs=n_obs,
        n_groups=n_groups,
        replication_status="replicated",
        terms=_terms_from_anova_table(tbl, ss_total),
    )


def _two_way_panel(trait_name: str, wide: pd.DataFrame) -> Optional[AnovaPanel]:
    """trait_value ~ C(accession_name) + C(env) + C(accession_name):C(env), Type II.

    Returns None if data doesn't support a two-way design (single env after
    dropping NaN, or every cell has only one observation so interaction df=0).
    """
    work = wide[["accession_name", trait_name]].copy()
    work["_env"] = wide.apply(_env_label, axis=1)
    work = work.dropna(subset=["accession_name", trait_name])
    if work.empty:
        return None

    n_envs = work["_env"].nunique()
    if n_envs < 2:
        return None

    df = work.rename(columns={trait_name: "_y"})
    # For an interaction term we need at least one (accession, env) cell with
    # >1 obs; otherwise df_resid is 0 and statsmodels returns NaN F.
    cell_counts = df.groupby(["accession_name", "_env"]).size()
    has_replicated_cell = (cell_counts > 1).any()
    if has_replicated_cell:
        formula = "_y ~ C(accession_name) + C(_env) + C(accession_name):C(_env)"
    else:
        # Fall back to additive model: still informative for accession +
        # environment main effects, just no interaction term.
        formula = "_y ~ C(accession_name) + C(_env)"
    try:
        model = smf.ols(formula, data=df).fit()
        tbl = sm.stats.anova_lm(model, typ=2)
    except Exception:
        return None
    ss_total = float(tbl["sum_sq"].sum())
    return AnovaPanel(
        trait_name=trait_name,
        env_label="two-way",
        kind="two_way",
        n_obs=int(len(df)),
        n_groups=int(df["accession_name"].nunique()),
        replication_status="replicated" if has_replicated_cell else "unreplicated",
        terms=_terms_from_anova_table(tbl, ss_total),
        message=None if has_replicated_cell else (
            "No (accession × env) cell has more than one plot — "
            "interaction term dropped; main effects only."
        ),
    )


def _h2_panel(trait_name: str, env_label: str, sub: pd.DataFrame) -> HeritabilityPanel:
    """Per-env broad-sense H² via MixedLM REML.

    Model: trait_value ~ 1 + (1|accession). Variance components:
      σ²_g — between-accession variance (genotype effect)
      σ²_e — residual / within-accession variance
    H² = σ²_g / (σ²_g + σ²_e / mean_reps)

    The mean_reps weighting yields the "operational" H² appropriate for
    the actual replication in this env (Holland 2003). Unbalanced is OK.
    """
    import warnings

    work = sub[["accession_name", trait_name]].dropna()
    work = work[work["accession_name"].notna()]
    n_obs = int(len(work))
    n_groups = int(work["accession_name"].nunique())

    if n_obs < 2 or n_groups < 2:
        return HeritabilityPanel(
            trait_name=trait_name,
            env_label=env_label,
            n_obs=n_obs,
            n_groups=n_groups,
            mean_reps=0.0,
            convergence_status="insufficient_data",
            message="Need at least 2 accessions with values to estimate H².",
        )

    rep_counts = work.groupby("accession_name").size()
    mean_reps = float(rep_counts.mean())
    if (rep_counts > 1).sum() == 0:
        return HeritabilityPanel(
            trait_name=trait_name,
            env_label=env_label,
            n_obs=n_obs,
            n_groups=n_groups,
            mean_reps=mean_reps,
            convergence_status="unreplicated",
            message="No accession has more than one plot — H² is undefined without replicates.",
        )

    df = work.rename(columns={trait_name: "_y"})

    convergence_status: Literal["ok", "warning", "failed"] = "ok"
    var_g = var_e = None
    blups: list[BLUP] = []

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = sm.MixedLM.from_formula("_y ~ 1", groups="accession_name", data=df)
            result = model.fit(reml=True, method="lbfgs")
        if not getattr(result, "converged", True):
            convergence_status = "warning"
        elif any(
            issubclass(w.category, (Warning,))
            and ("converge" in str(w.message).lower() or "singular" in str(w.message).lower())
            for w in caught
        ):
            convergence_status = "warning"

        # cov_re is a 1×1 (or scalar) matrix of the random-effect variance.
        cov_re = result.cov_re
        try:
            var_g_raw = float(cov_re.iloc[0, 0])  # DataFrame
        except (AttributeError, TypeError):
            try:
                var_g_raw = float(cov_re[0, 0])  # ndarray
            except (TypeError, IndexError):
                var_g_raw = float(cov_re)
        var_e_raw = float(result.scale)
        var_g = max(0.0, var_g_raw)
        var_e = max(0.0, var_e_raw)

        # BLUPs: posterior accession means.
        re_dict = result.random_effects  # {accession: pd.Series([deviation])}
        intercept = float(result.fe_params.iloc[0])
        for acc, dev_series in re_dict.items():
            try:
                dev = float(dev_series.iloc[0])
            except AttributeError:
                dev = float(dev_series[0])
            blups.append(BLUP(accession_name=str(acc), blup=intercept + dev))
        blups.sort(key=lambda b: b.accession_name)
    except Exception as e:
        return HeritabilityPanel(
            trait_name=trait_name,
            env_label=env_label,
            n_obs=n_obs,
            n_groups=n_groups,
            mean_reps=mean_reps,
            convergence_status="failed",
            message=f"REML fit failed: {e}",
        )

    denom = (var_g or 0.0) + ((var_e or 0.0) / mean_reps if mean_reps > 0 else 0.0)
    h2 = float(var_g / denom) if denom > 0 else None

    return HeritabilityPanel(
        trait_name=trait_name,
        env_label=env_label,
        n_obs=n_obs,
        n_groups=n_groups,
        mean_reps=mean_reps,
        var_g=var_g,
        var_e=var_e,
        h2=h2,
        convergence_status=convergence_status,
        blups=blups,
    )


def _build_heritability_panels(
    wide: pd.DataFrame,
    trait_names: List[str],
) -> List[HeritabilityPanel]:
    panels: list[HeritabilityPanel] = []
    if wide.empty:
        return panels
    work = wide.copy()
    work["_env"] = work.apply(_env_label, axis=1)
    for trait in trait_names:
        if trait not in work.columns:
            continue
        for env_lbl, sub in work.groupby("_env", dropna=False):
            panels.append(_h2_panel(trait, env_lbl, sub))
    return panels


def _build_anova_panels(wide: pd.DataFrame, trait_names: List[str]) -> List[AnovaPanel]:
    panels: list[AnovaPanel] = []
    if wide.empty:
        return panels

    work = wide.copy()
    work["_env"] = work.apply(_env_label, axis=1)

    for trait in trait_names:
        if trait not in work.columns:
            continue
        # One panel per (trait, env).
        for env_lbl, sub in work.groupby("_env", dropna=False):
            panels.append(_one_way_panel(trait, env_lbl, sub))
        # Cross-env two-way if multiple envs are present.
        two_way = _two_way_panel(trait, work)
        if two_way is not None:
            panels.append(two_way)
    return panels


def _run_pca(
    wide: pd.DataFrame,
    trait_names: List[str],
    row_kind: Literal["plot", "accession"],
) -> PCAResponse:
    """Standardize the wide trait matrix and run SVD-based PCA.

    Drops rows with any NaN across the requested traits (PCA requires a
    complete matrix). Returns at most min(5, n_traits, n_rank) components.
    """
    available = [t for t in trait_names if t in wide.columns]
    if len(available) < 3:
        return PCAResponse(
            status="insufficient_data",
            n_records_fetched=0,
            n_components=0,
            explained_variance_ratio=[],
            scores=[],
            loadings=[],
            trait_names=available,
            row_kind=row_kind,
            message="PCA needs at least 3 traits with values.",
        )

    work = wide.dropna(subset=available).copy()
    n_rows = len(work)
    if n_rows < 3:
        return PCAResponse(
            status="insufficient_data",
            n_records_fetched=0,
            n_components=0,
            explained_variance_ratio=[],
            scores=[],
            loadings=[],
            trait_names=available,
            row_kind=row_kind,
            message="PCA needs at least 3 complete rows after dropping NaN.",
        )

    X = work[available].to_numpy(dtype=float)
    # Z-score: per-column mean 0, std 1. Constant columns get std=1 to avoid
    # nan output, which leaves them as zeros after centering.
    mu = X.mean(axis=0)
    sigma = X.std(axis=0, ddof=0)
    sigma_safe = np.where(sigma > 0, sigma, 1.0)
    Z = (X - mu) / sigma_safe

    # SVD: Z = U S Vt. Scores = U*S, loadings = V (columns) scaled by S/sqrt(n-1)
    # for a covariance biplot. We return the principal-component coordinates
    # (U*S) for scores and the rescaled right singular vectors for loadings.
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    # Explained variance per component = S^2 / (n-1); total var = sum.
    eigvals = (S**2) / max(n_rows - 1, 1)
    total_var = eigvals.sum()
    evr = (eigvals / total_var).tolist() if total_var > 0 else [0.0] * len(S)

    n_components = min(5, len(S))
    scores_mat = (U[:, :n_components] * S[:n_components]).tolist()
    # Loading vectors: columns of V (rows of Vt), each scaled by sqrt(eigval)
    # so arrows are comparable to score units in the biplot.
    loadings_mat = (Vt[:n_components, :].T * np.sqrt(eigvals[:n_components])).tolist()

    pca_scores: list[PCAScore] = []
    for i, (_, r) in enumerate(work.reset_index(drop=True).iterrows()):
        if row_kind == "accession":
            row_id = str(r.get("accession_name") or f"row{i}")
            label = row_id
        else:
            row_id = str(r.get("plot_id") or f"row{i}")
            label = str(r.get("accession_name") or row_id)
        pca_scores.append(PCAScore(
            id=row_id,
            label=label,
            accession_name=(
                str(r["accession_name"])
                if pd.notna(r.get("accession_name"))
                else None
            ),
            population=(
                str(r["population"])
                if pd.notna(r.get("population"))
                else None
            ),
            experiment_name=(
                str(r["experiment_name"])
                if pd.notna(r.get("experiment_name"))
                else None
            ),
            site_name=(
                str(r["site_name"])
                if pd.notna(r.get("site_name"))
                else None
            ),
            components=[float(v) for v in scores_mat[i]],
        ))

    pca_loadings = [
        PCALoading(
            trait_name=t,
            components=[float(v) for v in loadings_mat[i]],
        )
        for i, t in enumerate(available)
    ]

    return PCAResponse(
        status="ok",
        n_records_fetched=0,  # caller patches this
        n_components=n_components,
        explained_variance_ratio=[float(v) for v in evr[:n_components]],
        scores=pca_scores,
        loadings=pca_loadings,
        trait_names=available,
        row_kind=row_kind,
    )


def _run_gge(
    wide: pd.DataFrame,
    trait_name: str,
) -> GGEResponse:
    """Genotype Main effect + Genotype-by-Environment interaction (GGE).

    Builds an accession × env matrix of trait means, environment-centers
    (subtracts column means — Yan & Tinker 2006 convention), runs SVD, and
    returns the first two principal components as a biplot.

    Polygon: convex hull of the genotype score cloud — vertex accessions
    are the "winners" in some direction of environment space.
    """

    if trait_name not in wide.columns:
        return GGEResponse(
            status="insufficient_data",
            trait_name=trait_name,
            n_records_fetched=0,
            n_accessions=0,
            n_envs=0,
            explained_variance_ratio=[],
            accession_scores=[],
            env_scores=[],
            polygon=[],
            message=f"Trait {trait_name!r} not present after aggregation.",
        )

    work = wide[[trait_name, "accession_name", "experiment_name", "season_name", "site_name"]].copy()
    work = work[work["accession_name"].notna() & work[trait_name].notna()]
    if work.empty:
        return GGEResponse(
            status="insufficient_data",
            trait_name=trait_name,
            n_records_fetched=0,
            n_accessions=0,
            n_envs=0,
            explained_variance_ratio=[],
            accession_scores=[],
            env_scores=[],
            polygon=[],
            message="No records with accession_name after aggregation.",
        )

    # Environment = (experiment, season, site) tuple.
    work["_env"] = work.apply(_env_label, axis=1)
    mat = (
        work.groupby(["accession_name", "_env"])[trait_name]
        .mean()
        .unstack("_env")
    )
    # Keep only accessions / envs with no missing cell so SVD is well-defined.
    mat = mat.dropna(axis=0, how="any").dropna(axis=1, how="any")
    n_acc, n_env = mat.shape

    if n_env < 3:
        return GGEResponse(
            status="insufficient_data",
            trait_name=trait_name,
            n_records_fetched=0,
            n_accessions=n_acc,
            n_envs=n_env,
            explained_variance_ratio=[],
            accession_scores=[],
            env_scores=[],
            polygon=[],
            message="GGE biplot needs at least 3 environments with complete data.",
        )
    if n_acc < 3:
        return GGEResponse(
            status="insufficient_data",
            trait_name=trait_name,
            n_records_fetched=0,
            n_accessions=n_acc,
            n_envs=n_env,
            explained_variance_ratio=[],
            accession_scores=[],
            env_scores=[],
            polygon=[],
            message="GGE biplot needs at least 3 accessions present in every selected env.",
        )

    # Environment-centering: subtract each env's mean. The resulting matrix
    # contains G + GE (the "GGE" the biplot visualizes).
    centered = mat.subtract(mat.mean(axis=0), axis=1).to_numpy(dtype=float)

    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    eigvals = (S**2) / max(n_acc - 1, 1)
    total = eigvals.sum()
    evr = (eigvals / total).tolist() if total > 0 else [0.0] * len(S)

    # Symmetric scaling — both genotype and env scores get a √S factor each,
    # which is the standard GGE biplot convention (preserves inner-product
    # interpretation of cells).
    scale = np.sqrt(S)
    g_scores = U * scale  # (n_acc, k)
    e_scores = (Vt.T * scale)  # (n_env, k)

    accession_scores = [
        GGEPoint(name=str(a), pc1=float(g_scores[i, 0]), pc2=float(g_scores[i, 1]))
        for i, a in enumerate(mat.index)
    ]
    env_scores = [
        GGEPoint(name=str(e), pc1=float(e_scores[i, 0]), pc2=float(e_scores[i, 1]))
        for i, e in enumerate(mat.columns)
    ]

    # Which-won-where polygon: convex hull of genotype PC1×PC2 scores.
    polygon: list[str] = []
    pts = g_scores[:, :2]
    if len(pts) >= 3:
        try:
            hull = ConvexHull(pts)
            polygon = [str(mat.index[i]) for i in hull.vertices]
        except Exception:
            polygon = []

    return GGEResponse(
        status="ok",
        trait_name=trait_name,
        n_records_fetched=0,  # caller patches
        n_accessions=n_acc,
        n_envs=n_env,
        explained_variance_ratio=[float(v) for v in evr],
        accession_scores=accession_scores,
        env_scores=env_scores,
        polygon=polygon,
    )


def _pearson_with_n(values: pd.DataFrame, trait_names: List[str]) -> CorrelationMatrix:
    n = len(trait_names)
    matrix: list[list[Optional[float]]] = [[None] * n for _ in range(n)]
    counts: list[list[int]] = [[0] * n for _ in range(n)]
    for i, ti in enumerate(trait_names):
        col_i = values[ti].dropna()
        counts[i][i] = int(len(col_i))
        if len(col_i) >= 1:
            matrix[i][i] = 1.0
        for j in range(i + 1, len(trait_names)):
            tj = trait_names[j]
            pair = values[[ti, tj]].dropna()
            counts[i][j] = counts[j][i] = int(len(pair))
            if len(pair) >= 2 and pair[ti].std(ddof=0) > 0 and pair[tj].std(ddof=0) > 0:
                rho = float(pair[ti].corr(pair[tj], method="pearson"))
                matrix[i][j] = matrix[j][i] = rho
    return CorrelationMatrix(trait_names=trait_names, matrix=matrix, n=counts)


def _spearman_with_n(values: pd.DataFrame, trait_names: List[str]) -> CorrelationMatrix:
    n = len(trait_names)
    matrix: list[list[Optional[float]]] = [[None] * n for _ in range(n)]
    counts: list[list[int]] = [[0] * n for _ in range(n)]
    for i, ti in enumerate(trait_names):
        col_i = values[ti].dropna()
        counts[i][i] = int(len(col_i))
        if len(col_i) >= 1:
            matrix[i][i] = 1.0
        for j in range(i + 1, len(trait_names)):
            tj = trait_names[j]
            pair = values[[ti, tj]].dropna()
            counts[i][j] = counts[j][i] = int(len(pair))
            if len(pair) >= 2:
                rho, _ = spearmanr(pair[ti], pair[tj])
                if rho is not None and not np.isnan(rho):
                    matrix[i][j] = matrix[j][i] = float(rho)
    return CorrelationMatrix(trait_names=trait_names, matrix=matrix, n=counts)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class MultiVariateAnalysisController(Controller):

    @post(path="/matrix", sync_to_thread=True)
    def matrix(self, data: MultivariateRequest) -> Response:
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=MatrixResponse(
                        status="too_large",
                        n_records_fetched=n_fetched,
                        n_rows=0,
                        trait_names=data.trait_names,
                        rows=[],
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            if df.empty:
                return Response(
                    content=MatrixResponse(
                        status="insufficient_data",
                        n_records_fetched=n_fetched,
                        n_rows=0,
                        trait_names=data.trait_names,
                        rows=[],
                        message="No records match the selected filters.",
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            rows = _wide_to_rows(wide, data.trait_names)
            return Response(
                content=MatrixResponse(
                    status="ok",
                    n_records_fetched=n_fetched,
                    n_rows=len(rows),
                    trait_names=data.trait_names,
                    rows=rows,
                ),
                status_code=200,
            )
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to build trait matrix.",
                ),
                status_code=500,
            )

    @post(path="/correlation", sync_to_thread=True)
    def correlation(self, data: MultivariateRequest) -> Response:
        if len(data.trait_names) < 2:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description="Correlation needs at least 2 trait_names.",
                ),
                status_code=400,
            )
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=CorrelationResponse(
                        status="too_large",
                        n_rows=0,
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            if wide.empty or len(wide) < 2:
                return Response(
                    content=CorrelationResponse(
                        status="insufficient_data",
                        n_rows=len(wide),
                        message="Need at least 2 plots after aggregation to compute correlation.",
                    ),
                    status_code=200,
                )

            value_cols = [c for c in data.trait_names if c in wide.columns]
            for missing in set(data.trait_names) - set(value_cols):
                wide[missing] = np.nan
            values = wide[data.trait_names]

            pearson = _pearson_with_n(values, data.trait_names)
            spearman = _spearman_with_n(values, data.trait_names)

            return Response(
                content=CorrelationResponse(
                    status="ok",
                    n_rows=int(len(wide)),
                    pearson=pearson,
                    spearman=spearman,
                ),
                status_code=200,
            )
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to compute correlation.",
                ),
                status_code=500,
            )

    @post(path="/spatial", sync_to_thread=True)
    def spatial(self, data: MultivariateRequest) -> Response:
        # Spatial is single-trait by definition — each map renders one trait
        # across a field grid. The shared MultivariateRequest takes a list,
        # but we only honor the first entry.
        if len(data.trait_names) != 1:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description="Spatial needs exactly 1 trait_name.",
                ),
                status_code=400,
            )
        trait_name = data.trait_names[0]
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=SpatialResponse(
                        status="too_large",
                        trait_name=trait_name,
                        n_records_fetched=n_fetched,
                        sites=[],
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            sites = _build_spatial_sites(wide, trait_name)
            if not sites:
                return Response(
                    content=SpatialResponse(
                        status="insufficient_data",
                        trait_name=trait_name,
                        n_records_fetched=n_fetched,
                        sites=[],
                        message=(
                            "No plots with plot_row_number and plot_column_number "
                            "in the selected filters — spatial map needs gridded plots."
                        ),
                    ),
                    status_code=200,
                )

            return Response(
                content=SpatialResponse(
                    status="ok",
                    trait_name=trait_name,
                    n_records_fetched=n_fetched,
                    sites=sites,
                ),
                status_code=200,
            )
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to build spatial map.",
                ),
                status_code=500,
            )

    @post(path="/anova", sync_to_thread=True)
    def anova(self, data: MultivariateRequest) -> Response:
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=AnovaResponse(
                        status="too_large",
                        n_records_fetched=n_fetched,
                        panels=[],
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            panels = _build_anova_panels(wide, data.trait_names)
            if not panels:
                return Response(
                    content=AnovaResponse(
                        status="insufficient_data",
                        n_records_fetched=n_fetched,
                        panels=[],
                        message="Not enough data to run ANOVA on any selected trait.",
                    ),
                    status_code=200,
                )

            return Response(
                content=AnovaResponse(
                    status="ok",
                    n_records_fetched=n_fetched,
                    panels=panels,
                ),
                status_code=200,
            )
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to compute ANOVA.",
                ),
                status_code=500,
            )

    @post(path="/heritability", sync_to_thread=True)
    def heritability(self, data: MultivariateRequest) -> Response:
        # Like ANOVA, never collapse replicates — H² depends on
        # within-genotype variation.
        data = data.model_copy(update={"collapse_replicates": False})
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=HeritabilityResponse(
                        status="too_large",
                        n_records_fetched=n_fetched,
                        panels=[],
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            panels = _build_heritability_panels(wide, data.trait_names)
            if not panels:
                return Response(
                    content=HeritabilityResponse(
                        status="insufficient_data",
                        n_records_fetched=n_fetched,
                        panels=[],
                        message="Not enough data to estimate heritability on any selected trait.",
                    ),
                    status_code=200,
                )

            return Response(
                content=HeritabilityResponse(
                    status="ok",
                    n_records_fetched=n_fetched,
                    panels=panels,
                ),
                status_code=200,
            )
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to compute heritability.",
                ),
                status_code=500,
            )

    @post(path="/pca", sync_to_thread=True)
    def pca(self, data: MultivariateRequest) -> Response:
        if len(data.trait_names) < 3:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description="PCA needs at least 3 trait_names.",
                ),
                status_code=400,
            )
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=PCAResponse(
                        status="too_large",
                        n_records_fetched=n_fetched,
                        n_components=0,
                        explained_variance_ratio=[],
                        scores=[],
                        loadings=[],
                        trait_names=data.trait_names,
                        row_kind=(
                            "accession" if data.collapse_replicates else "plot"
                        ),
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            row_kind = "accession" if data.collapse_replicates else "plot"
            resp = _run_pca(wide, data.trait_names, row_kind)
            resp.n_records_fetched = n_fetched
            return Response(content=resp, status_code=200)
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to compute PCA.",
                ),
                status_code=500,
            )

    @post(path="/gge", sync_to_thread=True)
    def gge(self, data: MultivariateRequest) -> Response:
        if len(data.trait_names) != 1:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description="GGE biplot needs exactly 1 trait_name.",
                ),
                status_code=400,
            )
        trait_name = data.trait_names[0]
        # GGE always works on per-genotype × per-env means; force the
        # replicate collapse regardless of what the request asked for.
        data = data.model_copy(update={"collapse_replicates": True})
        try:
            df, n_fetched = _fetch_long(data)
            if n_fetched > ROW_LIMIT:
                return Response(
                    content=GGEResponse(
                        status="too_large",
                        trait_name=trait_name,
                        n_records_fetched=n_fetched,
                        n_accessions=0,
                        n_envs=0,
                        explained_variance_ratio=[],
                        accession_scores=[],
                        env_scores=[],
                        polygon=[],
                        message=(
                            f"Fetched > {ROW_LIMIT:,} records before aggregation. "
                            "Narrow filters and retry."
                        ),
                    ),
                    status_code=200,
                )

            wide = _aggregate_per_plot(df, data)
            resp = _run_gge(wide, trait_name)
            resp.n_records_fetched = n_fetched
            return Response(content=resp, status_code=200)
        except ValueError as ve:
            return Response(
                content=RESTAPIError(
                    error="invalid_request",
                    error_description=str(ve),
                ),
                status_code=400,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(
                    error=str(e),
                    error_description="Failed to compute GGE biplot.",
                ),
                status_code=500,
            )
