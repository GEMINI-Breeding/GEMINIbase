"""Plot identifiers: whole numbers stay ints, named plots keep their text."""
import math

from gemini.workers.plot_ids import normalize_plot_number, plot_number_key
from gemini.workers.ml.trait_ingest import _features_to_records


def test_normalize():
    assert normalize_plot_number(101) == 101
    assert normalize_plot_number("101") == 101
    assert normalize_plot_number(" 101 ") == 101
    assert normalize_plot_number(101.0) == 101
    assert normalize_plot_number("KW1") == "KW1"
    assert normalize_plot_number(" KW1 ") == "KW1"
    for empty in (None, "", "  ", math.nan, "nan", True):
        assert normalize_plot_number(empty) is None


def test_natural_order():
    got = sorted(["KW10", "2", "KW2", 10, "1", None, "B1"], key=plot_number_key)
    assert got == ["1", "2", 10, "B1", "KW2", "KW10", None]


def test_named_plots_become_records_with_their_accession():
    feats = [
        {"properties": {"plot": "KW3", "row": 9, "col": 1, "accession": "BTx623", "temp": 30.5}},
        {"properties": {"plot": 101, "row": 1, "col": 1, "accession": "MACIA", "temp": 31.0}},
        {"properties": {"plot": "", "row": 1, "col": 2, "temp": 29.0}},
    ]
    recs = _features_to_records(feats, "temp")
    assert [r["plot_number"] for r in recs] == ["KW3", 101]
    assert recs[0]["accession_name"] == "BTx623"
    assert recs[0]["record_info"]["accession_name"] == "BTx623"
