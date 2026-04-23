"""Subprocess wrappers around GEMMA for kinship and association tests.

GEMMA has a persistent quirk: regardless of -outdir, it writes outputs to a
subdirectory called `output/` under the current working directory. We always
invoke it with cwd=<scratch_dir>, then resolve files from
<scratch_dir>/output/<prefix>.<suffix>.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

GEMMA_BIN = "gemma"

LMM_TEST_FLAGS = {
    "wald": "1",
    "lrt": "2",
    "score": "3",
    "all": "4",
}


@dataclass
class GemmaRunResult:
    assoc_path: Path
    log_path: Path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    logger.info("exec: %s  (cwd=%s)", " ".join(str(a) for a in argv), cwd)
    proc = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").splitlines()[-50:])
        raise RuntimeError(
            f"gemma exited with code {proc.returncode}:\n{tail}"
        )
    return proc


def kinship(
    bed_prefix: Path,
    work_dir: Path,
    out_name: str = "kin",
    kinship_type: int = 1,
    pheno_path: Path | None = None,
) -> Path:
    """Compute centered (1) or standardized (2) relatedness matrix.

    GEMMA uses the phenotype column to decide which samples to analyze; it
    rejects individuals whose phenotype is missing. Our worker writes -9 in
    .fam column 6 and keeps real values in a separate .pheno file, so we
    must pass -p even for kinship or GEMMA will see 0 analyzable individuals
    and bail.

    Returns path to the kinship .cXX.txt (centered) or .sXX.txt (standardized).
    """
    argv = [
        GEMMA_BIN,
        "-bfile", str(bed_prefix),
        "-gk", str(kinship_type),
        "-o", out_name,
    ]
    if pheno_path is not None:
        argv += ["-p", str(pheno_path)]
    _run(argv, cwd=work_dir)
    suffix = ".cXX.txt" if kinship_type == 1 else ".sXX.txt"
    return work_dir / "output" / f"{out_name}{suffix}"


def lmm(
    bed_prefix: Path,
    pheno_path: Path,
    kinship_path: Path,
    work_dir: Path,
    out_name: str = "run",
    test: str = "wald",
    covar_path: Path | None = None,
    trait_columns: list[int] | None = None,
) -> GemmaRunResult:
    """Run GEMMA univariate LMM (or mvLMM when trait_columns has length > 1).

    GEMMA convention:
      - phenotypes are loaded via -p (file must have one row per sample in .fam order).
      - -n <i [i i ...]> selects 1-indexed trait columns to test.
      - -lmm 4 with multiple -n columns triggers multivariate LMM.
    """
    flag = LMM_TEST_FLAGS[test]
    if trait_columns and len(trait_columns) > 1:
        flag = "4"  # mvLMM forces Wald-style multivariate test

    argv: list[str] = [
        GEMMA_BIN,
        "-bfile", str(bed_prefix),
        "-p", str(pheno_path),
        "-k", str(kinship_path),
        "-lmm", flag,
        "-o", out_name,
    ]
    if covar_path is not None:
        argv += ["-c", str(covar_path)]
    if trait_columns:
        argv.append("-n")
        argv += [str(i) for i in trait_columns]

    _run(argv, cwd=work_dir)
    return GemmaRunResult(
        assoc_path=work_dir / "output" / f"{out_name}.assoc.txt",
        log_path=work_dir / "output" / f"{out_name}.log.txt",
    )


def bslmm(
    bed_prefix: Path,
    pheno_path: Path,
    work_dir: Path,
    out_name: str = "run",
    model: int = 1,
) -> GemmaRunResult:
    """Bayesian sparse linear mixed model. `model` is 1|2|3 per GEMMA docs."""
    argv = [
        GEMMA_BIN,
        "-bfile", str(bed_prefix),
        "-p", str(pheno_path),
        "-bslmm", str(model),
        "-o", out_name,
    ]
    _run(argv, cwd=work_dir)
    return GemmaRunResult(
        assoc_path=work_dir / "output" / f"{out_name}.param.txt",
        log_path=work_dir / "output" / f"{out_name}.log.txt",
    )
