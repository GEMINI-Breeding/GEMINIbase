"""Subprocess wrappers around PLINK 2.0 for QC and PCA."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PLINK_BIN = "plink2"


@dataclass
class QcResult:
    bed_prefix: Path
    n_variants_before: int
    n_variants_after: int
    n_samples_before: int
    n_samples_after: int
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
            f"{argv[0]} exited with code {proc.returncode}:\n{tail}"
        )
    return proc


def _parse_counts(log_text: str) -> tuple[int, int, int, int]:
    """Pull before/after variant+sample counts from a plink2 .log file.

    PLINK2 logs are messy but reliably contain phrases like:
      "312 samples ... loaded"
      "32143 variants loaded"
      "28112 variants remaining after main filters"
      "308 samples remaining after main filters"
    We take the first/last occurrences of the respective numeric lines.
    """
    variants_before = variants_after = samples_before = samples_after = 0
    for line in log_text.splitlines():
        s = line.strip()
        if "variants loaded" in s:
            try:
                variants_before = int(s.split()[0].replace(",", ""))
            except ValueError:
                pass
        elif "variants remaining" in s:
            try:
                variants_after = int(s.split()[0].replace(",", ""))
            except ValueError:
                pass
        elif ("samples" in s and "loaded" in s):
            try:
                samples_before = int(s.split()[0].replace(",", ""))
            except ValueError:
                pass
        elif ("samples remaining" in s) or ("people remaining" in s):
            try:
                samples_after = int(s.split()[0].replace(",", ""))
            except ValueError:
                pass
    if variants_after == 0:
        variants_after = variants_before
    if samples_after == 0:
        samples_after = samples_before
    return variants_before, variants_after, samples_before, samples_after


def qc(
    in_prefix: Path,
    out_prefix: Path,
    maf: float = 0.05,
    geno: float = 0.1,
    mind: float = 0.1,
    hwe: float = 1e-6,
) -> QcResult:
    """Apply standard MAF / missingness / HWE filters."""
    cwd = out_prefix.parent
    argv = [
        PLINK_BIN,
        "--bfile", str(in_prefix),
        "--maf", str(maf),
        "--geno", str(geno),
        "--mind", str(mind),
        "--hwe", str(hwe),
        "--make-bed",
        "--allow-extra-chr",
        "--out", str(out_prefix),
    ]
    _run(argv, cwd=cwd)
    log_path = out_prefix.with_suffix(".log")
    counts = _parse_counts(log_path.read_text() if log_path.exists() else "")
    return QcResult(
        bed_prefix=out_prefix,
        n_variants_before=counts[0],
        n_variants_after=counts[1],
        n_samples_before=counts[2],
        n_samples_after=counts[3],
        log_path=log_path,
    )


def pca(
    in_prefix: Path,
    out_prefix: Path,
    n_pcs: int = 10,
) -> Path:
    """Compute top-n PCs; returns path to the .eigenvec file."""
    cwd = out_prefix.parent
    argv = [
        PLINK_BIN,
        "--bfile", str(in_prefix),
        "--pca", str(n_pcs),
        "--allow-extra-chr",
        "--out", str(out_prefix),
    ]
    _run(argv, cwd=cwd)
    return out_prefix.with_suffix(".eigenvec")


def write_gemma_covar(
    eigenvec_path: Path,
    fam_path: Path,
    covar_out: Path,
    n_pcs: int,
) -> int:
    """Build a GEMMA -c covariate file from a PLINK .eigenvec file.

    GEMMA requires: one row per sample in the exact order of the .fam file,
    with the first column as an all-ones intercept. Samples missing from the
    eigenvec get zeros (they would have been dropped by --mind before PCA).

    Returns the number of covariate columns written (1 + n_pcs, or 1 if
    n_pcs == 0 and no eigenvec was produced).
    """
    sample_order = [line.split()[1] for line in fam_path.read_text().splitlines() if line.strip()]
    pcs_by_sample: dict[str, list[str]] = {}
    if n_pcs > 0 and eigenvec_path.exists():
        for line in eigenvec_path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[0].upper() in {"FID", "#FID", "#IID"}:
                continue
            iid = parts[1]
            pcs_by_sample[iid] = parts[2:2 + n_pcs]

    n_cols = 1 + n_pcs
    with covar_out.open("w") as f:
        for iid in sample_order:
            pcs = pcs_by_sample.get(iid, ["0"] * n_pcs) if n_pcs > 0 else []
            f.write(" ".join(["1", *pcs]) + "\n")
    return n_cols
