"""
Integration test for the GWAS pipeline binaries + wrappers.

This test does NOT exercise the DB extraction path — that surface is covered
by unit tests. The value here is confirming that:

  (a) `plink2` and `gemma` are installed and invokable,
  (b) our subprocess wrappers produce usable outputs,
  (c) the plots/summarize code parses GEMMA's .assoc.txt correctly,
  (d) under a null phenotype, the p-value distribution is approximately
      uniform (λ ≈ 1) — a cheap smoke test that the pipeline is wired up
      correctly end to end.

Run from inside the gemini-worker-gwas container (where the binaries live):
    docker compose exec gemini-worker-gwas python -m pytest \\
        tests/integration/test_gwas_pipeline.py -v -m integration

Skipped automatically when `plink2` / `gemma` aren't on PATH.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.integration

BINARIES_AVAILABLE = shutil.which("plink2") is not None and shutil.which("gemma") is not None


@pytest.fixture
def synthetic_bed(tmp_path: Path) -> Path:
    """Generate a minimal PLINK fileset: 100 variants × 20 samples, random alleles."""
    from gemini.workers.gwas import extract

    rng = np.random.default_rng(42)
    n_variants, n_samples = 100, 20

    # Random 0/1/2 allele dosages → PLINK codes.
    # dose 0 → hom A2 (11), 1 → het (10), 2 → hom A1 (00).
    # Avoid missing for this smoke test so GEMMA has plenty of data.
    dosages = rng.integers(0, 3, size=(n_variants, n_samples))
    code_map = np.array([extract.CODE_HOM_A2, extract.CODE_HET, extract.CODE_HOM_A1], dtype=np.uint8)
    codes = code_map[dosages]

    prefix = tmp_path / "sim"
    # .fam
    with (tmp_path / "sim.fam").open("w") as f:
        for i in range(n_samples):
            f.write(f"s{i} s{i} 0 0 0 -9\n")
    # .bim — PLINK rejects interleaved chromosomes, so group variants first.
    variant_specs = sorted(
        [((i % 5) + 1, (i // 5) * 1000 + 1, f"snp{i}") for i in range(n_variants)]
    )
    with (tmp_path / "sim.bim").open("w") as f:
        for chrom, bp, name in variant_specs:
            f.write(f"{chrom} {name} 0 {bp} A G\n")
    # .bed
    with (tmp_path / "sim.bed").open("wb") as f:
        f.write(bytes([0x6C, 0x1B, 0x01]))
        for i in range(n_variants):
            f.write(extract._pack_variant_row(codes[i]))
    return prefix


@pytest.fixture
def null_pheno(tmp_path: Path) -> Path:
    """Random-normal phenotype aligned to the 20-sample .fam."""
    rng = np.random.default_rng(7)
    path = tmp_path / "sim.pheno"
    with path.open("w") as f:
        for v in rng.standard_normal(20):
            f.write(f"{v:.6g}\n")
    return path


@pytest.mark.skipif(not BINARIES_AVAILABLE, reason="plink2 and gemma not on PATH")
class TestGwasPipelineBinaries:

    def test_qc_runs(self, synthetic_bed: Path, tmp_path: Path):
        from gemini.workers.gwas import plink_runner
        result = plink_runner.qc(
            in_prefix=synthetic_bed,
            out_prefix=tmp_path / "qc",
            maf=0.01, geno=0.5, mind=0.5, hwe=1e-20,
        )
        assert (tmp_path / "qc.bed").exists()
        assert (tmp_path / "qc.bim").exists()
        assert (tmp_path / "qc.fam").exists()
        assert result.n_variants_after > 0

    def test_pca_runs(self, synthetic_bed: Path, tmp_path: Path):
        from gemini.workers.gwas import plink_runner
        plink_runner.qc(
            in_prefix=synthetic_bed,
            out_prefix=tmp_path / "qc",
            maf=0.01, geno=0.5, mind=0.5, hwe=1e-20,
        )
        eigenvec = plink_runner.pca(
            in_prefix=tmp_path / "qc",
            out_prefix=tmp_path / "pca",
            n_pcs=3,
        )
        assert eigenvec.exists()
        text = eigenvec.read_text().splitlines()
        assert len(text) >= 20  # header + 20 samples

    def test_full_pipeline_produces_uniform_pvals(
        self, synthetic_bed: Path, null_pheno: Path, tmp_path: Path
    ):
        """End-to-end: QC → kinship → LMM → parse → summarize → plot.

        Under a null phenotype drawn independently of genotypes, the p-value
        distribution should be approximately uniform. We use a relaxed
        Kolmogorov–Smirnov bound (p > 0.001) — with only 100 variants the
        KS statistic is noisy, so this is a smoke test, not a precision test.
        """
        from gemini.workers.gwas import gemma_runner, plink_runner, plots
        from scipy import stats

        qc_result = plink_runner.qc(
            in_prefix=synthetic_bed,
            out_prefix=tmp_path / "qc",
            maf=0.01, geno=0.5, mind=0.5, hwe=1e-20,
        )
        plink_runner.write_gemma_covar(
            eigenvec_path=tmp_path / "nonexistent.eigenvec",
            fam_path=tmp_path / "qc.fam",
            covar_out=tmp_path / "covar.txt",
            n_pcs=0,  # intercept-only
        )
        kin = gemma_runner.kinship(
            bed_prefix=tmp_path / "qc",
            work_dir=tmp_path,
            out_name="kin",
            pheno_path=null_pheno,  # GEMMA reads -9 from .fam otherwise
        )
        assert kin.exists()

        run = gemma_runner.lmm(
            bed_prefix=tmp_path / "qc",
            pheno_path=null_pheno,
            kinship_path=kin,
            covar_path=tmp_path / "covar.txt",
            work_dir=tmp_path,
            out_name="run",
            test="wald",
        )
        assert run.assoc_path.exists()

        df, p_col = plots.load_assoc(run.assoc_path)
        assert p_col == "p_wald"
        summary = plots.summarize(df, p_col)
        assert summary.n_variants == qc_result.n_variants_after

        # KS test for uniformity of p-values.
        pvals = df[p_col].dropna().to_numpy()
        pvals = pvals[(pvals > 0) & (pvals <= 1)]
        ks = stats.kstest(pvals, "uniform")
        assert ks.pvalue > 0.001, (
            f"p-values don't look uniform (KS p={ks.pvalue:.4f}); "
            f"λ={summary.genomic_inflation_lambda:.3f}"
        )

        manhattan = plots.manhattan_plot(df, p_col, tmp_path / "m.png")
        qq = plots.qq_plot(df, p_col, tmp_path / "q.png")
        assert manhattan.exists() and manhattan.stat().st_size > 0
        assert qq.exists() and qq.stat().st_size > 0
