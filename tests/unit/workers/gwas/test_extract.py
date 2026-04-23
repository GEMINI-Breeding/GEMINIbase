"""Unit tests for gemini.workers.gwas.extract.

Pure-function tests (no DB) covering:
  - allele encoding edge cases
  - PLINK .bed bit-packing layout (LSB-first, 4 samples/byte)
  - phenotype .pheno row order + missing handling
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ============================================================
# _encode_call
# ============================================================

class TestEncodeCall:

    def setup_method(self):
        from gemini.workers.gwas.extract import (
            CODE_HOM_A1, CODE_HOM_A2, CODE_HET, CODE_MISSING,
        )
        self.hom_a1 = CODE_HOM_A1
        self.hom_a2 = CODE_HOM_A2
        self.het = CODE_HET
        self.missing = CODE_MISSING

    def test_hom_ref_maps_to_hom_a2(self):
        # alleles = "T/C" → A1=alt=C, A2=ref=T. "TT" is hom ref → hom A2.
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call("TT", "C", "T") == self.hom_a2

    def test_hom_alt_maps_to_hom_a1(self):
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call("CC", "C", "T") == self.hom_a1

    def test_het_either_order(self):
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call("TC", "C", "T") == self.het
        assert _encode_call("CT", "C", "T") == self.het

    def test_lowercase_input(self):
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call("tt", "C", "T") == self.hom_a2
        assert _encode_call("cc", "C", "T") == self.hom_a1

    def test_missing_variants(self):
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call(None, "C", "T") == self.missing
        assert _encode_call("", "C", "T") == self.missing
        assert _encode_call("NN", "C", "T") == self.missing
        assert _encode_call("N", "C", "T") == self.missing
        assert _encode_call("--", "C", "T") == self.missing
        assert _encode_call(".", "C", "T") == self.missing

    def test_unknown_allele_is_missing(self):
        # "AG" when alleles are T/C → missing (no overlap).
        from gemini.workers.gwas.extract import _encode_call
        assert _encode_call("AG", "C", "T") == self.missing


# ============================================================
# _pack_variant_row
# ============================================================

class TestPackVariantRow:

    def test_exact_four_samples(self):
        from gemini.workers.gwas.extract import _pack_variant_row
        # 4 samples: hom_a1 (00), missing (01), het (10), hom_a2 (11).
        # Byte = 11 10 01 00 (MSB→LSB) = 0xE4
        codes = np.array([0b00, 0b01, 0b10, 0b11], dtype=np.uint8)
        assert _pack_variant_row(codes) == bytes([0xE4])

    def test_padding_missing_for_non_multiple_of_four(self):
        from gemini.workers.gwas.extract import _pack_variant_row, CODE_MISSING
        # 5 samples → 2 bytes; padding samples 6,7,8 filled with 01 (missing).
        codes = np.array([0b00, 0b00, 0b00, 0b00, 0b10], dtype=np.uint8)
        packed = _pack_variant_row(codes)
        assert len(packed) == 2
        assert packed[0] == 0x00  # all hom_a1 in first 4 samples
        # byte 2: sample 4 = 10 (bits 0-1); samples 5,6,7 pad with 01.
        # = 01 01 01 10 = 0x56
        assert packed[1] == 0x56

    def test_all_missing_row(self):
        from gemini.workers.gwas.extract import _pack_variant_row, CODE_MISSING
        codes = np.full(8, CODE_MISSING, dtype=np.uint8)
        packed = _pack_variant_row(codes)
        # 01 repeated → 0x55 per byte
        assert packed == bytes([0x55, 0x55])

    def test_lsb_first_single_sample(self):
        from gemini.workers.gwas.extract import _pack_variant_row
        # 1 sample hom_a2 (11) should land in bits 0-1 of byte 1;
        # padding 2-4 are 01 each. Byte = 01 01 01 11 = 0x57.
        codes = np.array([0b11], dtype=np.uint8)
        assert _pack_variant_row(codes) == bytes([0x57])


# ============================================================
# write_phenotype row ordering + missing-as -9
# ============================================================

class TestWritePhenotype:

    def _mock_session_execute(self, results_by_trait: dict[str, list[tuple[str, float]]]):
        """Build a fake db_engine.get_session() whose session.execute() returns
        a new iterable each call, matching the trait_id in the where clause.
        """
        # We key each returned iterable by call order, relying on the fact
        # that extract.write_phenotype iterates trait_ids in order.
        calls = {"i": 0}
        trait_ids = list(results_by_trait.keys())

        def fake_execute(stmt):
            i = calls["i"]
            calls["i"] = i + 1
            tid = trait_ids[i] if i < len(trait_ids) else None
            return iter(results_by_trait.get(tid, []))

        session = MagicMock()
        session.execute.side_effect = fake_execute
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=session)
        ctx.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.get_session.return_value = ctx
        return engine

    def test_single_trait_ordering_and_missing(self, tmp_path: Path):
        from gemini.workers.gwas import extract

        sample_order = ["acc-A", "acc-B", "acc-C"]
        trait_ids = ["trait-1"]
        rows = {"trait-1": [("acc-A", 10.0), ("acc-C", 30.0)]}  # acc-B missing

        engine = self._mock_session_execute(rows)
        with patch.object(extract, "db_engine", engine):
            out, n_covered = extract.write_phenotype(
                sample_order=sample_order,
                trait_ids=trait_ids,
                out_dir=tmp_path,
            )
        text = out.read_text().splitlines()
        assert text == ["10", "-9", "30"]
        assert n_covered == 2

    def test_multi_trait_columns(self, tmp_path: Path):
        from gemini.workers.gwas import extract

        sample_order = ["a", "b"]
        trait_ids = ["t1", "t2"]
        rows = {
            "t1": [("a", 1.0), ("b", 2.0)],
            "t2": [("a", 5.5)],          # b missing t2
        }
        engine = self._mock_session_execute(rows)
        with patch.object(extract, "db_engine", engine):
            out, n_covered = extract.write_phenotype(
                sample_order=sample_order,
                trait_ids=trait_ids,
                out_dir=tmp_path,
            )
        lines = out.read_text().splitlines()
        assert lines == ["1 5.5", "2 -9"]
        assert n_covered == 2

    def test_aggregates_repeated_observations(self, tmp_path: Path):
        from gemini.workers.gwas import extract

        sample_order = ["a", "b"]
        trait_ids = ["t1"]
        rows = {"t1": [("a", 10.0), ("a", 20.0), ("b", 5.0)]}   # mean(a) = 15

        engine = self._mock_session_execute(rows)
        with patch.object(extract, "db_engine", engine):
            out, _ = extract.write_phenotype(
                sample_order=sample_order,
                trait_ids=trait_ids,
                out_dir=tmp_path,
                agg="mean",
            )
        assert out.read_text().splitlines() == ["15", "5"]

    def test_rejects_bad_agg(self, tmp_path: Path):
        from gemini.workers.gwas import extract
        with pytest.raises(ValueError, match="phenotype_agg"):
            extract.write_phenotype(
                sample_order=["a"], trait_ids=["t"], out_dir=tmp_path, agg="mode",
            )

    def test_rejects_empty_trait_list(self, tmp_path: Path):
        from gemini.workers.gwas import extract
        with pytest.raises(ValueError, match="trait_id"):
            extract.write_phenotype(
                sample_order=["a"], trait_ids=[], out_dir=tmp_path,
            )


# ============================================================
# .bim bp-coordinate handling (regression for PLINK "Invalid bp" error)
# ============================================================

class TestBimBpCoordinates:
    """
    Reproduce the conditions under which PLINK2 rejected the .bim file:
    chromosome-start variants with cM == 0 used to write bp == 0, which is
    invalid. We test the post-fix behavior directly against the .bim path
    written by write_plink_fileset — mocked at the session layer.
    """

    def _fake_engine_with_variants(self, variants: list[tuple]):
        """
        variants: list of (chromosome:int, position_cm:float, variant_name:str, alleles:str)

        Returns a fake engine whose session.execute returns rows for:
          (1) distinct accessions   → one sample "sX"
          (2) distinct variants     → the supplied list
          (3) genotype records      → empty stream
        """
        from unittest.mock import MagicMock

        class FakeAcc:
            def __init__(self, name):
                self.id = f"aid-{name}"
                self.accession_name = name

        class FakeVar:
            def __init__(self, vid, name, chrom, pos, alleles):
                self.id = vid
                self.variant_name = name
                self.chromosome = chrom
                self.position = pos
                self.alleles = alleles

        # Rows for the 3 execute calls (in order)
        acc_rows = [("aid-s0", "s0"), ("aid-s1", "s1")]
        var_rows = [
            (f"vid-{i}", name, chrom, pos, alleles)
            for i, (chrom, pos, name, alleles) in enumerate(variants)
        ]

        calls = {"i": 0}

        def fake_execute(_stmt):
            i = calls["i"]
            calls["i"] = i + 1
            # The extraction runs 3 ordered queries then a streaming one.
            if i == 0:
                return _Result(acc_rows)
            if i == 1:
                return _Result(var_rows)
            return _Result([])  # genotype stream: no calls

        class _Result:
            def __init__(self, rows):
                self.rows = rows
            def all(self):
                return self.rows
            def __iter__(self):
                return iter(self.rows)

        session = MagicMock()
        session.execute.side_effect = fake_execute
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=session)
        ctx.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.get_session.return_value = ctx
        return engine

    def test_zero_cm_produces_bp_ge_1(self, tmp_path: Path):
        """
        Regression: 3 variants on chrom 1 all with cM == 0 should write
        strictly increasing, all-positive bp values (not 0, 0, 0).
        """
        from unittest.mock import patch
        from gemini.workers.gwas import extract

        variants = [
            (1, 0.0, "2_24641", "T/C"),
            (1, 0.0, "2_26334", "C/A"),
            (1, 0.0, "2_26347", "A/G"),
        ]
        engine = self._fake_engine_with_variants(variants)
        with patch.object(extract, "db_engine", engine):
            paths = extract.write_plink_fileset(
                study_id="00000000-0000-0000-0000-000000000000",
                study_name="test",
                out_dir=tmp_path,
                basename="raw",
            )
        lines = paths.bim.read_text().splitlines()
        assert len(lines) == 3
        bps = [int(line.split()[3]) for line in lines]
        assert all(bp >= 1 for bp in bps), f"bp must be >= 1, got {bps}"
        assert bps == sorted(bps) and len(set(bps)) == len(bps), (
            f"bp must be strictly increasing within chromosome, got {bps}"
        )

    def test_cm_scaling_preserved_when_distinct(self, tmp_path: Path):
        """When cM values differ, bp should reflect the cM ordering."""
        from unittest.mock import patch
        from gemini.workers.gwas import extract

        variants = [
            (1, 0.0, "snpA", "T/C"),
            (1, 14.2, "snpB", "T/C"),
            (1, 47.9, "snpC", "T/C"),
            (2, 0.0, "snpD", "T/C"),
        ]
        engine = self._fake_engine_with_variants(variants)
        with patch.object(extract, "db_engine", engine):
            paths = extract.write_plink_fileset(
                study_id="00000000-0000-0000-0000-000000000000",
                study_name="test",
                out_dir=tmp_path,
                basename="raw",
            )
        rows = [line.split() for line in paths.bim.read_text().splitlines()]
        # Per-chromosome bp monotonic, positive
        by_chrom: dict[str, list[int]] = {}
        for r in rows:
            by_chrom.setdefault(r[0], []).append(int(r[3]))
        for chrom, bps in by_chrom.items():
            assert all(b >= 1 for b in bps), (chrom, bps)
            assert bps == sorted(bps) and len(set(bps)) == len(bps), (chrom, bps)
