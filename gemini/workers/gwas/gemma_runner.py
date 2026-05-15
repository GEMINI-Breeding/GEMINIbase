"""Subprocess wrappers around GEMMA for kinship and association tests.

GEMMA has a persistent quirk: regardless of -outdir, it writes outputs to a
subdirectory called `output/` under the current working directory. We always
invoke it with cwd=<scratch_dir>, then resolve files from
<scratch_dir>/output/<prefix>.<suffix>.

GEMMA also emits its per-SNP progress bar to stdout as carriage-return
refreshed lines like "  0%=", " 12%=======", etc. We stream that here so
callers can drive a UI progress bar instead of blocking for minutes on a
single subprocess.run().
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

GEMMA_BIN = "gemma"

LMM_TEST_FLAGS = {
    "wald": "1",
    "lrt": "2",
    "score": "3",
    "all": "4",
}

OnProgress = Callable[[int], None]

# GEMMA's progress bar: optional leading spaces, then "NN%", then "=" run.
# We accept 1–3 digit percentages, anchored to the start of the segment so
# stray "p<0.05%" style text in headers can't trip the parser.
_GEMMA_PROGRESS_RE = re.compile(r"^\s*(\d{1,3})%=+")


def _stream_run(
    argv: list[str],
    cwd: Path,
    on_progress: Optional[OnProgress] = None,
) -> subprocess.CompletedProcess:
    """Run a command, streaming stdout line-by-line.

    GEMMA refreshes its progress bar with `\\r`, so we split on both `\\r`
    and `\\n` and inspect each fragment. Anything matching the progress
    pattern triggers `on_progress(int_pct)`; everything else is just kept
    in the captured buffer for error reporting on non-zero exit.
    """
    logger.info("exec: %s  (cwd=%s)", " ".join(str(a) for a in argv), cwd)
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert proc.stdout is not None

    captured_parts: list[str] = []
    buf = ""
    last_pct = -1
    try:
        while True:
            chunk_b = proc.stdout.read(256)
            if not chunk_b:
                break
            chunk = chunk_b.decode("utf-8", errors="replace")
            captured_parts.append(chunk)
            buf += chunk
            # Split on \r or \n; keep the trailing partial in buf.
            parts = re.split(r"[\r\n]+", buf)
            buf = parts.pop()
            for line in parts:
                if not on_progress:
                    continue
                m = _GEMMA_PROGRESS_RE.match(line)
                if not m:
                    continue
                pct = int(m.group(1))
                if not 0 <= pct <= 100 or pct == last_pct:
                    continue
                last_pct = pct
                try:
                    on_progress(pct)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("on_progress callback failed: %s", exc)
    finally:
        proc.stdout.close()

    proc.wait()
    captured = "".join(captured_parts)

    if proc.returncode != 0:
        tail = "\n".join(captured.splitlines()[-50:])
        raise RuntimeError(
            f"gemma exited with code {proc.returncode}:\n{tail}"
        )

    return subprocess.CompletedProcess(
        args=argv,
        returncode=0,
        stdout=captured,
        stderr="",
    )


def _run(argv: list[str], cwd: Path, on_progress: Optional[OnProgress] = None) -> subprocess.CompletedProcess:
    """Backwards-compatible wrapper kept for callers that don't need streaming."""
    return _stream_run(argv, cwd, on_progress=on_progress)


@dataclass
class GemmaRunResult:
    assoc_path: Path
    log_path: Path


def kinship(
    bed_prefix: Path,
    work_dir: Path,
    out_name: str = "kin",
    kinship_type: int = 1,
    pheno_path: Path | None = None,
    on_progress: Optional[OnProgress] = None,
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
    _run(argv, cwd=work_dir, on_progress=on_progress)
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
    on_progress: Optional[OnProgress] = None,
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

    _run(argv, cwd=work_dir, on_progress=on_progress)
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
    on_progress: Optional[OnProgress] = None,
) -> GemmaRunResult:
    """Bayesian sparse linear mixed model. `model` is 1|2|3 per GEMMA docs."""
    argv = [
        GEMMA_BIN,
        "-bfile", str(bed_prefix),
        "-p", str(pheno_path),
        "-bslmm", str(model),
        "-o", out_name,
    ]
    _run(argv, cwd=work_dir, on_progress=on_progress)
    return GemmaRunResult(
        assoc_path=work_dir / "output" / f"{out_name}.param.txt",
        log_path=work_dir / "output" / f"{out_name}.log.txt",
    )
