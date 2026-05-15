"""Tests for the GEMMA stdout streaming + progress parsing in gemma_runner.

We don't need a real `gemma` binary — we synthesize the exact byte pattern
GEMMA emits (carriage-return-refreshed `NN%===` bar) via a tiny shell
script and verify the on_progress callback sees a monotonic 0..100 sequence
of percentages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from gemini.workers.gwas import gemma_runner


def _make_emitter(tmp_path: Path, payload: str, exit_code: int = 0) -> Path:
    """Write a Python script that prints `payload` raw to stdout, then exits."""
    script = tmp_path / "emit.py"
    # Use sys.stdout.buffer.write so \r is preserved as-is (no newline xlate).
    body = (
        "import sys\n"
        f"sys.stdout.buffer.write({payload!r}.encode())\n"
        "sys.stdout.buffer.flush()\n"
        f"sys.exit({exit_code})\n"
    )
    script.write_text(body)
    script.chmod(0o755)
    return script


def test_stream_run_parses_progress_bar(tmp_path: Path) -> None:
    # Realistic-looking GEMMA stdout: header lines (no %), then a CR-refreshed
    # progress bar at 0,3,6,...,100. Final newline.
    bar_segments = []
    for pct in (0, 3, 12, 25, 50, 75, 99, 100):
        bar_segments.append(f"\r{pct:>4}%{'=' * max(pct // 3, 1)}")
    payload = (
        "GEMMA 0.98.5\n"
        "Reading Files ...\n"
        "## number of total individuals = 168\n"
        + "".join(bar_segments)
        + "\n"
    )

    script = _make_emitter(tmp_path, payload)
    seen: list[int] = []
    result = gemma_runner._stream_run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        on_progress=seen.append,
    )

    assert result.returncode == 0
    # The header line "## number of total individuals = 168" has no % — must
    # NOT be parsed as progress. We should only see the bar percents, in order.
    assert seen == [0, 3, 12, 25, 50, 75, 99, 100]


def test_stream_run_dedupes_repeated_percentages(tmp_path: Path) -> None:
    payload = "\r 25%==\r 25%==\r 25%==\r 50%====\r 50%====\n"
    script = _make_emitter(tmp_path, payload)
    seen: list[int] = []
    gemma_runner._stream_run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        on_progress=seen.append,
    )
    assert seen == [25, 50]


def test_stream_run_ignores_percent_in_text(tmp_path: Path) -> None:
    # Lines that mention "%" but aren't the GEMMA progress bar must not fire
    # the callback. The pattern anchors to `^\s*NN%=+` so a stray "MAF<5%"
    # in a header should be ignored.
    payload = (
        "## filter MAF < 5%\n"
        "## p-value threshold = 0.05% per test\n"
        "\r 42%====\n"
    )
    script = _make_emitter(tmp_path, payload)
    seen: list[int] = []
    gemma_runner._stream_run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        on_progress=seen.append,
    )
    assert seen == [42]


def test_stream_run_raises_with_tail_on_nonzero_exit(tmp_path: Path) -> None:
    payload = "header line\nFATAL: missing file 'foo'\n"
    script = _make_emitter(tmp_path, payload, exit_code=2)
    with pytest.raises(RuntimeError) as exc:
        gemma_runner._stream_run(
            [sys.executable, str(script)],
            cwd=tmp_path,
            on_progress=None,
        )
    msg = str(exc.value)
    assert "code 2" in msg
    assert "FATAL: missing file 'foo'" in msg


def test_stream_run_works_without_callback(tmp_path: Path) -> None:
    # No on_progress passed — should still consume output and return 0.
    payload = "\r 50%====\r100%========\n"
    script = _make_emitter(tmp_path, payload)
    result = gemma_runner._stream_run(
        [sys.executable, str(script)],
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert "100%" in result.stdout


def test_callback_exception_does_not_kill_run(tmp_path: Path) -> None:
    payload = "\r 10%=\r 20%==\r 30%===\n"
    script = _make_emitter(tmp_path, payload)
    calls: list[int] = []

    def boom(pct: int) -> None:
        calls.append(pct)
        if pct == 20:
            raise ValueError("test failure")

    result = gemma_runner._stream_run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        on_progress=boom,
    )
    assert result.returncode == 0
    # Callback raised at 20, but 30 should still be delivered.
    assert calls == [10, 20, 30]
