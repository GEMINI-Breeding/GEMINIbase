"""Unit tests for the germplasm resolver module.

The resolver runs a single CTE query against Postgres and maps the row shape
back into ResolveResult objects. These tests mock the DB session to assert
the mapping/short-circuiting logic row-by-row.
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from gemini.api.germplasm_resolver import (
    resolve_germplasm,
    ResolveResult,
    MATCH_KINDS,
)


def _mk_row(idx, raw, **overrides):
    """Build a mock row mirroring the SELECT projection in _RESOLVE_SQL."""
    cols = {
        "idx": idx,
        "raw": raw,
        "acc_exact_id": None, "acc_exact_name": None,
        "line_exact_id": None, "line_exact_name": None,
        "alias_exp_acc_id": None, "alias_exp_line_id": None, "alias_exp_name": None,
        "alias_glob_acc_id": None, "alias_glob_line_id": None, "alias_glob_name": None,
    }
    cols.update(overrides)
    return SimpleNamespace(**cols)


@contextmanager
def _mock_session(rows):
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    yield session


@pytest.fixture
def patched_engine():
    with patch("gemini.api.germplasm_resolver.db_engine") as engine:
        rows_box = {"rows": []}

        @contextmanager
        def fake_get_session():
            with _mock_session(rows_box["rows"]) as s:
                yield s

        engine.get_session = fake_get_session
        yield engine, rows_box


class TestResolveEmpty:
    def test_empty_names_returns_empty(self, patched_engine):
        assert resolve_germplasm([], experiment_id=None) == []


class TestResolveOrder:
    def test_accession_exact_wins(self, patched_engine):
        engine, box = patched_engine
        acc_id = str(uuid4())
        box["rows"] = [_mk_row(1, "MAGIC110",
                               acc_exact_id=acc_id, acc_exact_name="MAGIC110",
                               line_exact_id=str(uuid4()), line_exact_name="should-ignore")]
        results = resolve_germplasm(["MAGIC110"], experiment_id=None)
        assert len(results) == 1
        assert results[0].match_kind == "accession_exact"
        assert results[0].accession_id == acc_id
        assert results[0].canonical_name == "MAGIC110"
        assert results[0].line_id is None

    def test_line_exact_used_when_no_accession(self, patched_engine):
        engine, box = patched_engine
        line_id = str(uuid4())
        box["rows"] = [_mk_row(1, "B73",
                               line_exact_id=line_id, line_exact_name="B73")]
        results = resolve_germplasm(["B73"], experiment_id=None)
        assert results[0].match_kind == "line_exact"
        assert results[0].line_id == line_id
        assert results[0].accession_id is None
        assert results[0].canonical_name == "B73"

    def test_alias_experiment_preferred_over_global(self, patched_engine):
        engine, box = patched_engine
        exp_acc = str(uuid4())
        glob_acc = str(uuid4())
        box["rows"] = [_mk_row(1, "1",
                               alias_exp_acc_id=exp_acc, alias_exp_name="MAGIC110",
                               alias_glob_acc_id=glob_acc, alias_glob_name="OTHER")]
        results = resolve_germplasm(["1"], experiment_id=uuid4())
        assert results[0].match_kind == "alias_experiment"
        assert results[0].accession_id == exp_acc
        assert results[0].canonical_name == "MAGIC110"

    def test_alias_global_used_when_no_experiment_hit(self, patched_engine):
        engine, box = patched_engine
        glob_line = str(uuid4())
        box["rows"] = [_mk_row(1, "Check1",
                               alias_glob_line_id=glob_line, alias_glob_name="CB-46")]
        results = resolve_germplasm(["Check1"], experiment_id=None)
        assert results[0].match_kind == "alias_global"
        assert results[0].line_id == glob_line
        assert results[0].canonical_name == "CB-46"

    def test_unresolved_when_nothing_matches(self, patched_engine):
        engine, box = patched_engine
        box["rows"] = [_mk_row(1, "MAGIC11O")]  # letter-O typo
        results = resolve_germplasm(["MAGIC11O"], experiment_id=None)
        assert results[0].match_kind == "unresolved"
        assert results[0].accession_id is None
        assert results[0].line_id is None
        assert results[0].candidates == []


class TestResolveOrdering:
    def test_preserves_input_order_across_many_rows(self, patched_engine):
        engine, box = patched_engine
        a = str(uuid4())
        # Simulate Postgres returning rows in some ORDER BY n.idx order.
        box["rows"] = [
            _mk_row(1, "MAGIC110", acc_exact_id=a, acc_exact_name="MAGIC110"),
            _mk_row(2, "ghost"),
            _mk_row(3, "B73", line_exact_id=str(uuid4()), line_exact_name="B73"),
        ]
        results = resolve_germplasm(["MAGIC110", "ghost", "B73"], experiment_id=None)
        assert [r.input_name for r in results] == ["MAGIC110", "ghost", "B73"]
        assert [r.match_kind for r in results] == ["accession_exact", "unresolved", "line_exact"]


class TestMatchKindSurface:
    def test_all_reserved_kinds_present(self):
        # Reserve fuzzy_* kinds so future slices can add them without
        # breaking the wire format.
        for k in ("accession_exact", "line_exact", "alias_experiment",
                  "alias_global", "fuzzy_accession", "fuzzy_line", "unresolved"):
            assert k in MATCH_KINDS

    def test_result_to_dict_is_json_safe(self):
        r = ResolveResult(input_name="x", match_kind="unresolved")
        d = r.to_dict()
        assert d["input_name"] == "x"
        assert d["match_kind"] == "unresolved"
        assert d["candidates"] == []
