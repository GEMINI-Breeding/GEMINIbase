"""Pure-helper tests for the multivariate-analysis controller.

These exercise the aggregation + correlation helpers without standing up the
DB. Integration coverage of the HTTP endpoints lives under tests/integration.
"""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_long_df():
    """A handful of plots, two traits, two timestamps per plot.

    Plot layout:
      plotA (acc=X): trait_a t1=1.0, t2=2.0; trait_b t1=10.0, t2=12.0
      plotB (acc=Y): trait_a t1=3.0, t2=5.0; trait_b t1=14.0, t2=16.0
      plotC (acc=X): trait_a t1=2.0, t2=4.0; trait_b t1=11.0, t2=13.0
    """
    rows = []
    t1 = datetime(2024, 5, 1, 12, 0, 0)
    t2 = datetime(2024, 5, 8, 12, 0, 0)
    d1 = date(2024, 5, 1)
    d2 = date(2024, 5, 8)

    plots = [
        ("plotA", "X", [("trait_a", 1.0, t1, d1), ("trait_a", 2.0, t2, d2),
                        ("trait_b", 10.0, t1, d1), ("trait_b", 12.0, t2, d2)]),
        ("plotB", "Y", [("trait_a", 3.0, t1, d1), ("trait_a", 5.0, t2, d2),
                        ("trait_b", 14.0, t1, d1), ("trait_b", 16.0, t2, d2)]),
        ("plotC", "X", [("trait_a", 2.0, t1, d1), ("trait_a", 4.0, t2, d2),
                        ("trait_b", 11.0, t1, d1), ("trait_b", 13.0, t2, d2)]),
    ]
    for plot_id, acc, measurements in plots:
        for trait, val, ts, cd in measurements:
            rows.append({
                "plot_id": plot_id,
                "plot_number": int(plot_id[-1].encode()[0]),
                "plot_row_number": 1,
                "plot_column_number": int(plot_id[-1].encode()[0]),
                "experiment_name": "ExpA",
                "season_name": "S1",
                "site_name": "SiteX",
                "accession_name": acc,
                "population": "pop1",
                "trait_name": trait,
                "trait_value": val,
                "timestamp": ts,
                "collection_date": cd,
            })
    return pd.DataFrame(rows)


class TestAggregation:
    def _req(self, aggregation: str, agg_date=None):
        from gemini.rest_api.controllers.multivariate_analysis import (
            MultivariateRequest,
        )
        return MultivariateRequest(
            trait_names=["trait_a", "trait_b"],
            aggregation=aggregation,
            aggregation_date=agg_date,
        )

    def test_mean(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(sample_long_df, self._req("mean"))
        # 3 plots, mean of 2 timestamps each
        assert len(wide) == 3
        by_plot = wide.set_index("plot_id")
        assert by_plot.loc["plotA", "trait_a"] == pytest.approx(1.5)
        assert by_plot.loc["plotB", "trait_a"] == pytest.approx(4.0)
        assert by_plot.loc["plotC", "trait_b"] == pytest.approx(12.0)

    def test_max(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(sample_long_df, self._req("max"))
        by_plot = wide.set_index("plot_id")
        assert by_plot.loc["plotA", "trait_a"] == 2.0
        assert by_plot.loc["plotB", "trait_b"] == 16.0

    def test_min(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(sample_long_df, self._req("min"))
        by_plot = wide.set_index("plot_id")
        assert by_plot.loc["plotA", "trait_a"] == 1.0
        assert by_plot.loc["plotC", "trait_b"] == 11.0

    def test_latest(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(sample_long_df, self._req("latest"))
        by_plot = wide.set_index("plot_id")
        # latest timestamp is t2 = 2024-05-08 → second value
        assert by_plot.loc["plotA", "trait_a"] == 2.0
        assert by_plot.loc["plotB", "trait_a"] == 5.0
        assert by_plot.loc["plotC", "trait_b"] == 13.0

    def test_first(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(sample_long_df, self._req("first"))
        by_plot = wide.set_index("plot_id")
        assert by_plot.loc["plotA", "trait_a"] == 1.0
        assert by_plot.loc["plotB", "trait_b"] == 14.0

    def test_specific_date(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        wide = _aggregate_per_plot(
            sample_long_df, self._req("date", agg_date=date(2024, 5, 1))
        )
        by_plot = wide.set_index("plot_id")
        assert by_plot.loc["plotA", "trait_a"] == 1.0
        assert by_plot.loc["plotB", "trait_b"] == 14.0

    def test_date_requires_aggregation_date(self, sample_long_df):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _aggregate_per_plot,
        )
        with pytest.raises(ValueError):
            _aggregate_per_plot(sample_long_df, self._req("date", agg_date=None))

    def test_collapse_replicates_means_across_plots_per_accession(self):
        """3 reps of accession A and 3 of B should collapse to 2 rows."""
        from gemini.rest_api.controllers.multivariate_analysis import (
            MultivariateRequest,
            _aggregate_per_plot,
        )
        ts = datetime(2024, 5, 1, 12, 0, 0)
        cd = date(2024, 5, 1)
        rows = []
        for plot_id, acc, val in [
            ("p1", "A", 10.0), ("p2", "A", 12.0), ("p3", "A", 14.0),
            ("p4", "B", 20.0), ("p5", "B", 22.0), ("p6", "B", 24.0),
        ]:
            rows.append({
                "plot_id": plot_id, "plot_number": int(plot_id[1:]),
                "plot_row_number": 1, "plot_column_number": int(plot_id[1:]),
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": acc, "population": "p1",
                "trait_name": "trait_a", "trait_value": val,
                "timestamp": ts, "collection_date": cd,
            })
        df = pd.DataFrame(rows)
        req = MultivariateRequest(
            trait_names=["trait_a"],
            aggregation="mean",
            collapse_replicates=True,
        )
        wide = _aggregate_per_plot(df, req)
        assert len(wide) == 2
        by_acc = wide.set_index("accession_name")
        assert by_acc.loc["A", "trait_a"] == pytest.approx(12.0)
        assert by_acc.loc["B", "trait_a"] == pytest.approx(22.0)
        # Spatial columns nulled out after collapse
        assert wide["plot_id"].isna().all()
        assert wide["plot_row_number"].isna().all()


class TestCorrelation:
    def test_pearson_against_pandas(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _pearson_with_n,
        )
        df = pd.DataFrame({
            "t1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "t2": [2.0, 4.1, 6.0, 7.9, 10.0],     # nearly perfect positive
            "t3": [10.0, 8.0, 6.0, 4.0, 2.0],     # perfect negative
        })
        c = _pearson_with_n(df, ["t1", "t2", "t3"])
        # diag = 1
        assert c.matrix[0][0] == pytest.approx(1.0)
        assert c.matrix[1][1] == pytest.approx(1.0)
        assert c.matrix[2][2] == pytest.approx(1.0)
        # t1 vs t3 perfectly anti-correlated
        assert c.matrix[0][2] == pytest.approx(-1.0)
        # t1 vs t2 ~ +1 (allow tiny tolerance)
        assert c.matrix[0][1] == pytest.approx(0.9997, rel=1e-3)
        # symmetric
        assert c.matrix[1][0] == c.matrix[0][1]
        # counts: all 5 pairs complete
        for row in c.n:
            for cell in row:
                assert cell == 5

    def test_pearson_with_missing(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _pearson_with_n,
        )
        df = pd.DataFrame({
            "t1": [1.0, 2.0, np.nan, 4.0, 5.0],
            "t2": [2.0, np.nan, 6.0, 8.0, 10.0],
        })
        c = _pearson_with_n(df, ["t1", "t2"])
        # 3 complete pairs: (1,2), (4,8), (5,10)
        assert c.n[0][1] == 3
        assert c.matrix[0][1] == pytest.approx(1.0)

    def test_pearson_constant_column_returns_none(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _pearson_with_n,
        )
        df = pd.DataFrame({
            "t1": [1.0, 1.0, 1.0],
            "t2": [4.0, 5.0, 6.0],
        })
        c = _pearson_with_n(df, ["t1", "t2"])
        assert c.matrix[0][1] is None

    def test_spearman_ranks_match(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _spearman_with_n,
        )
        df = pd.DataFrame({
            "t1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "t2": [1.0, 10.0, 100.0, 1000.0, 10000.0],  # monotone -> rho=1
        })
        c = _spearman_with_n(df, ["t1", "t2"])
        assert c.matrix[0][1] == pytest.approx(1.0)


class TestRequestValidation:
    def test_trait_names_required(self):
        from pydantic import ValidationError
        from gemini.rest_api.controllers.multivariate_analysis import (
            MultivariateRequest,
        )
        with pytest.raises(ValidationError):
            MultivariateRequest(trait_names=[], aggregation="mean")


class TestSpatial:
    def _wide(self, rows):
        """Build a wide frame matching what _aggregate_per_plot produces."""
        return pd.DataFrame(rows)

    def test_basic_grid(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_spatial_sites,
        )
        wide = self._wide([
            {
                "plot_id": "p1", "plot_number": 1,
                "plot_row_number": 1, "plot_column_number": 1,
                "experiment_name": "E", "season_name": "S",
                "site_name": "SiteX", "accession_name": "A",
                "population": "p", "trait_a": 10.0,
            },
            {
                "plot_id": "p2", "plot_number": 2,
                "plot_row_number": 1, "plot_column_number": 2,
                "experiment_name": "E", "season_name": "S",
                "site_name": "SiteX", "accession_name": "B",
                "population": "p", "trait_a": 12.0,
            },
            {
                "plot_id": "p3", "plot_number": 3,
                "plot_row_number": 2, "plot_column_number": 1,
                "experiment_name": "E", "season_name": "S",
                "site_name": "SiteX", "accession_name": "C",
                "population": "p", "trait_a": 14.0,
            },
        ])
        sites = _build_spatial_sites(wide, "trait_a")
        assert len(sites) == 1
        s = sites[0]
        assert s.site_name == "SiteX"
        assert s.n_cells == 3
        assert s.min_row == 1 and s.max_row == 2
        assert s.min_col == 1 and s.max_col == 2
        assert s.value_min == 10.0 and s.value_max == 14.0
        # cell at (1,1) should be accession A with value 10
        cell_11 = next(c for c in s.cells if c.plot_row_number == 1 and c.plot_column_number == 1)
        assert cell_11.value == 10.0
        assert cell_11.accession_name == "A"

    def test_drops_rows_without_row_column(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_spatial_sites,
        )
        wide = self._wide([
            {
                "plot_id": "p1", "plot_number": 1,
                "plot_row_number": np.nan, "plot_column_number": np.nan,
                "site_name": "X", "accession_name": "A", "population": None,
                "experiment_name": None, "season_name": None, "trait_a": 5.0,
            },
            {
                "plot_id": "p2", "plot_number": 2,
                "plot_row_number": 1, "plot_column_number": 1,
                "site_name": "X", "accession_name": "B", "population": None,
                "experiment_name": None, "season_name": None, "trait_a": 6.0,
            },
        ])
        sites = _build_spatial_sites(wide, "trait_a")
        assert len(sites) == 1
        assert sites[0].n_cells == 1

    def test_multi_site_split(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_spatial_sites,
        )
        wide = self._wide([
            {
                "plot_id": f"p{i}", "plot_number": i,
                "plot_row_number": 1, "plot_column_number": i,
                "site_name": site, "accession_name": f"A{i}", "population": None,
                "experiment_name": None, "season_name": None, "trait_a": float(i),
            }
            for i, site in enumerate(["S1", "S1", "S2", "S2"], start=1)
        ])
        sites = _build_spatial_sites(wide, "trait_a")
        assert sorted(s.site_name for s in sites) == ["S1", "S2"]
        for s in sites:
            assert s.n_cells == 2

    def test_empty_when_trait_missing(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_spatial_sites,
        )
        wide = self._wide([
            {
                "plot_id": "p1", "plot_number": 1,
                "plot_row_number": 1, "plot_column_number": 1,
                "site_name": "X", "accession_name": "A", "population": None,
                "experiment_name": None, "season_name": None, "trait_a": 5.0,
            },
        ])
        sites = _build_spatial_sites(wide, "trait_does_not_exist")
        assert sites == []


class TestAnova:
    def _replicated_wide(self):
        """3 accessions × 3 reps in one env. Accession effect is real."""
        rows = []
        for plot_id, acc, val in [
            ("p1", "A", 10.0), ("p2", "A", 11.0), ("p3", "A", 9.5),
            ("p4", "B", 14.0), ("p5", "B", 15.0), ("p6", "B", 13.5),
            ("p7", "C", 18.0), ("p8", "C", 19.0), ("p9", "C", 17.5),
        ]:
            rows.append({
                "plot_id": plot_id, "plot_number": int(plot_id[1:]),
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": acc, "population": None,
                "trait_a": val,
            })
        return pd.DataFrame(rows)

    def test_one_way_significant(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_anova_panels,
        )
        wide = self._replicated_wide()
        panels = _build_anova_panels(wide, ["trait_a"])
        assert len(panels) == 1
        p = panels[0]
        assert p.kind == "one_way"
        assert p.replication_status == "replicated"
        assert p.n_obs == 9
        assert p.n_groups == 3
        terms = {t.term: t for t in p.terms}
        assert "C(accession_name)" in terms
        # F should be large — accessions are well-separated (~82 in practice).
        acc_term = terms["C(accession_name)"]
        assert acc_term.F is not None and acc_term.F > 30
        assert acc_term.p is not None and acc_term.p < 0.001
        assert acc_term.df == 2.0

    def test_one_way_unreplicated_flagged(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_anova_panels,
        )
        # 3 accessions, one plot each — no replication
        rows = []
        for plot_id, acc, val in [("p1", "A", 10.0), ("p2", "B", 14.0), ("p3", "C", 18.0)]:
            rows.append({
                "plot_id": plot_id, "plot_number": int(plot_id[1:]),
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": acc, "population": None,
                "trait_a": val,
            })
        wide = pd.DataFrame(rows)
        panels = _build_anova_panels(wide, ["trait_a"])
        assert len(panels) == 1
        assert panels[0].replication_status == "unreplicated"
        assert panels[0].terms == []

    def test_two_way_when_multi_env(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_anova_panels,
        )
        # 2 envs × 3 accessions × 2 reps. Accession + env both real.
        rows = []
        plot_id = 0
        for env_idx, site in enumerate(["X", "Y"]):
            for acc, base in [("A", 10.0), ("B", 14.0), ("C", 18.0)]:
                for rep in range(2):
                    plot_id += 1
                    rows.append({
                        "plot_id": f"p{plot_id}", "plot_number": plot_id,
                        "plot_row_number": None, "plot_column_number": None,
                        "experiment_name": "E1", "season_name": "S1",
                        "site_name": site,
                        "accession_name": acc, "population": None,
                        # Env shift: site Y everything +5; small rep noise.
                        "trait_a": base + (5.0 if env_idx == 1 else 0.0) + 0.1 * rep,
                    })
        wide = pd.DataFrame(rows)
        panels = _build_anova_panels(wide, ["trait_a"])
        # Expect per-env panels (2) + one two-way panel = 3
        kinds = [p.kind for p in panels]
        assert kinds.count("one_way") == 2
        assert kinds.count("two_way") == 1
        two = next(p for p in panels if p.kind == "two_way")
        terms = {t.term: t for t in two.terms}
        # Type II ANOVA gives accession + env + interaction terms.
        assert any("accession_name" in k for k in terms)
        assert any("_env" in k for k in terms)
        # Main accession effect must be highly significant.
        acc_terms = [v for k, v in terms.items() if "accession_name" in k and ":" not in k]
        assert acc_terms[0].p is not None and acc_terms[0].p < 0.01

    def test_two_way_falls_back_when_no_replicated_cell(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_anova_panels,
        )
        # 2 envs × 3 accessions × 1 rep each — no replicated cell.
        rows = []
        plot_id = 0
        for site in ["X", "Y"]:
            for acc, base in [("A", 10.0), ("B", 14.0), ("C", 18.0)]:
                plot_id += 1
                rows.append({
                    "plot_id": f"p{plot_id}", "plot_number": plot_id,
                    "plot_row_number": None, "plot_column_number": None,
                    "experiment_name": "E1", "season_name": "S1",
                    "site_name": site, "accession_name": acc,
                    "population": None,
                    "trait_a": base + (3.0 if site == "Y" else 0.0),
                })
        wide = pd.DataFrame(rows)
        panels = _build_anova_panels(wide, ["trait_a"])
        two = [p for p in panels if p.kind == "two_way"]
        # Per-env panels report unreplicated (n_groups=3, but 1 plot each)
        # and contain no terms. Two-way panel falls back to additive model.
        if two:
            assert two[0].replication_status == "unreplicated"
            assert two[0].message is not None
            term_names = [t.term for t in two[0].terms]
            # No interaction term
            assert not any(":" in t for t in term_names)


class TestHeritability:
    def _wide_replicated(self, between_var: float, within_var: float, seed: int = 0):
        """Simulate 8 accessions × 4 reps with controllable variance shares."""
        rng = np.random.default_rng(seed)
        accessions = [f"A{i:02d}" for i in range(8)]
        # Per-accession true means (deviations from grand mean).
        g_effects = rng.normal(0, np.sqrt(max(between_var, 1e-9)), size=len(accessions))
        rows = []
        plot_id = 0
        for acc, g in zip(accessions, g_effects):
            for _ in range(4):
                plot_id += 1
                noise = rng.normal(0, np.sqrt(max(within_var, 1e-9)))
                rows.append({
                    "plot_id": f"p{plot_id}", "plot_number": plot_id,
                    "plot_row_number": None, "plot_column_number": None,
                    "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                    "accession_name": acc, "population": None,
                    "trait_a": 50.0 + g + noise,
                })
        return pd.DataFrame(rows)

    def test_h2_high_when_genotype_dominates(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_heritability_panels,
        )
        # Big between-accession variance, tiny within. H² should be near 1.
        wide = self._wide_replicated(between_var=20.0, within_var=0.05, seed=7)
        panels = _build_heritability_panels(wide, ["trait_a"])
        assert len(panels) == 1
        p = panels[0]
        assert p.convergence_status == "ok"
        assert p.h2 is not None and p.h2 > 0.95
        # BLUPs cover every accession
        assert len(p.blups) == 8
        names = [b.accession_name for b in p.blups]
        assert names == sorted(names)

    def test_h2_low_when_noise_dominates(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_heritability_panels,
        )
        # Tiny between, big within. H² should be near 0.
        wide = self._wide_replicated(between_var=0.05, within_var=20.0, seed=11)
        panels = _build_heritability_panels(wide, ["trait_a"])
        p = panels[0]
        assert p.h2 is not None
        assert p.h2 < 0.4

    def test_h2_unreplicated(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_heritability_panels,
        )
        # 3 accessions, 1 rep each.
        rows = []
        for i, (acc, val) in enumerate([("A", 10.0), ("B", 14.0), ("C", 18.0)], start=1):
            rows.append({
                "plot_id": f"p{i}", "plot_number": i,
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": acc, "population": None,
                "trait_a": val,
            })
        wide = pd.DataFrame(rows)
        panels = _build_heritability_panels(wide, ["trait_a"])
        assert len(panels) == 1
        p = panels[0]
        assert p.convergence_status == "unreplicated"
        assert p.h2 is None
        assert p.blups == []

    def test_h2_insufficient_data(self):
        from gemini.rest_api.controllers.multivariate_analysis import (
            _build_heritability_panels,
        )
        # Only one accession — can't fit variance.
        wide = pd.DataFrame([
            {
                "plot_id": "p1", "plot_number": 1,
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": "A", "population": None,
                "trait_a": 10.0,
            },
            {
                "plot_id": "p2", "plot_number": 2,
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": "A", "population": None,
                "trait_a": 11.0,
            },
        ])
        panels = _build_heritability_panels(wide, ["trait_a"])
        assert panels[0].convergence_status == "insufficient_data"


class TestPCA:
    def _wide(self, n_rows: int, seed: int = 0):
        """5 traits where 4 share a latent factor and 1 is unrelated noise.

        After z-scoring, PC1 captures the shared factor and loads heavily on
        the 4 correlated traits; trait_e (the noise column) gets a small
        PC1 loading.
        """
        rng = np.random.default_rng(seed)
        rows = []
        for i in range(n_rows):
            base = rng.normal(0, 1.0)
            rows.append({
                "plot_id": f"p{i}", "plot_number": i + 1,
                "plot_row_number": None, "plot_column_number": None,
                "experiment_name": "E1", "season_name": "S1", "site_name": "X",
                "accession_name": f"A{i:02d}", "population": "pop1",
                "trait_a": base + rng.normal(0, 0.2),
                "trait_b": base + rng.normal(0, 0.2),
                "trait_c": base + rng.normal(0, 0.2),
                "trait_d": base + rng.normal(0, 0.2),
                "trait_e": rng.normal(0, 1.0),
            })
        return pd.DataFrame(rows)

    def test_explained_variance_sums_to_one(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_pca
        wide = self._wide(n_rows=30, seed=3)
        resp = _run_pca(
            wide,
            ["trait_a", "trait_b", "trait_c", "trait_d", "trait_e"],
            row_kind="plot",
        )
        assert resp.status == "ok"
        # We return at most 5 components — full PC budget sums to 1.
        assert resp.n_components == 5
        assert sum(resp.explained_variance_ratio) == pytest.approx(1.0, abs=1e-6)

    def test_shared_factor_loads_on_pc1(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_pca
        wide = self._wide(n_rows=40, seed=5)
        resp = _run_pca(
            wide,
            ["trait_a", "trait_b", "trait_c", "trait_d", "trait_e"],
            row_kind="plot",
        )
        # PC1 captures the shared factor → big chunk of total variance.
        assert resp.explained_variance_ratio[0] > 0.5
        # The 4 correlated traits all have larger PC1 loadings than the
        # uncorrelated noise trait (trait_e).
        loadings = {l.trait_name: abs(l.components[0]) for l in resp.loadings}
        for t in ["trait_a", "trait_b", "trait_c", "trait_d"]:
            assert loadings[t] > loadings["trait_e"]

    def test_insufficient_traits(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_pca
        wide = pd.DataFrame([
            {"plot_id": "p1", "trait_a": 1.0, "trait_b": 2.0,
             "accession_name": "A", "population": None,
             "experiment_name": None, "season_name": None, "site_name": None,
             "plot_number": 1, "plot_row_number": None, "plot_column_number": None}
        ])
        resp = _run_pca(wide, ["trait_a", "trait_b"], row_kind="plot")
        assert resp.status == "insufficient_data"

    def test_insufficient_rows(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_pca
        wide = pd.DataFrame([{
            "plot_id": f"p{i}", "plot_number": i,
            "plot_row_number": None, "plot_column_number": None,
            "experiment_name": None, "season_name": None, "site_name": None,
            "accession_name": f"A{i}", "population": None,
            "trait_a": 1.0 * i, "trait_b": 2.0 * i, "trait_c": 3.0 * i,
        } for i in range(2)])
        resp = _run_pca(wide, ["trait_a", "trait_b", "trait_c"], row_kind="plot")
        assert resp.status == "insufficient_data"

    def test_row_kind_accession_uses_accession_id(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_pca
        wide = self._wide(n_rows=20, seed=2)
        # Simulate post-collapse-replicates: plot_id null, accession_name set.
        wide["plot_id"] = None
        resp = _run_pca(
            wide,
            ["trait_a", "trait_b", "trait_c", "trait_d", "trait_e"],
            row_kind="accession",
        )
        assert resp.row_kind == "accession"
        assert resp.scores[0].id == resp.scores[0].accession_name


class TestGGE:
    def _wide_with_envs(self, env_means, seed=0):
        """Build a wide df keyed by accession × env with known structure.

        `env_means` is dict {env_label: {accession: trait_value}}. Output
        mimics what _aggregate_per_plot produces (one row per plot,
        accession + env carried through, trait column).
        """
        rng = np.random.default_rng(seed)
        rows = []
        plot_id = 0
        for env, by_acc in env_means.items():
            # Each (env, accession) gets one row — already collapsed since
            # GGE force-overrides collapse_replicates=True before this.
            for acc, val in by_acc.items():
                plot_id += 1
                # Tiny jitter so columns aren't constant (avoids degenerate
                # std=0 fallback).
                noise = rng.normal(0, 0.01)
                rows.append({
                    "plot_id": None, "plot_number": None,
                    "plot_row_number": None, "plot_column_number": None,
                    "experiment_name": "E1", "season_name": "S1",
                    "site_name": env,
                    "accession_name": acc, "population": None,
                    "trait_a": val + noise,
                })
        return pd.DataFrame(rows)

    def test_insufficient_envs(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_gge
        # Only 2 envs.
        wide = self._wide_with_envs({
            "siteX": {"A": 10, "B": 12, "C": 14, "D": 16},
            "siteY": {"A": 11, "B": 13, "C": 15, "D": 17},
        }, seed=1)
        resp = _run_gge(wide, "trait_a")
        assert resp.status == "insufficient_data"
        assert resp.n_envs == 2

    def test_insufficient_accessions(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_gge
        wide = self._wide_with_envs({
            "siteX": {"A": 10, "B": 12},
            "siteY": {"A": 11, "B": 13},
            "siteZ": {"A": 9, "B": 14},
        }, seed=1)
        resp = _run_gge(wide, "trait_a")
        assert resp.status == "insufficient_data"

    def test_returns_polygon_and_scores(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_gge
        # 4 accessions × 3 envs with non-trivial GE interaction.
        # A and D rank-cross between siteX and siteZ.
        wide = self._wide_with_envs({
            "siteX": {"A": 20, "B": 15, "C": 10, "D": 5},
            "siteY": {"A": 14, "B": 14, "C": 14, "D": 14},
            "siteZ": {"A": 5, "B": 10, "C": 15, "D": 20},
        }, seed=42)
        resp = _run_gge(wide, "trait_a")
        assert resp.status == "ok"
        assert resp.n_accessions == 4
        assert resp.n_envs == 3
        # 4 accessions, 4 score points, 3 env vectors
        assert len(resp.accession_scores) == 4
        assert len(resp.env_scores) == 3
        # Polygon = convex hull of 4 points in 2D — with strong GE the
        # extremes (A and D) must be vertices.
        names = set(resp.polygon)
        assert {"A", "D"}.issubset(names)
        # Explained variance is monotonically non-increasing.
        evr = resp.explained_variance_ratio
        for i in range(len(evr) - 1):
            assert evr[i] >= evr[i + 1]

    def test_drops_envs_with_missing_accessions(self):
        from gemini.rest_api.controllers.multivariate_analysis import _run_gge
        # siteY misses accession D.
        wide = self._wide_with_envs({
            "siteX": {"A": 20, "B": 15, "C": 10, "D": 5},
            "siteY": {"A": 14, "B": 14, "C": 14},
            "siteZ": {"A": 5, "B": 10, "C": 15, "D": 20},
        }, seed=11)
        resp = _run_gge(wide, "trait_a")
        # D is dropped from the matrix (incomplete across envs).
        names = {p.name for p in resp.accession_scores}
        assert "D" not in names
