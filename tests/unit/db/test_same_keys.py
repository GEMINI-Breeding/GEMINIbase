"""Bulk inserts group rows by their keys (rows whose None fields were
dropped can't share one multi-row execute)."""
from gemini.db.core.base import _same_keys


def test_mixed_rows_are_grouped_in_order():
    rows = [{"a": 1, "p": 1}, {"a": 2, "p": 2}, {"a": 3}, {"a": 4, "p": 4}, {"p": 5, "a": 5}]
    assert _same_keys(rows) == [
        [{"a": 1, "p": 1}, {"a": 2, "p": 2}],
        [{"a": 3}],
        [{"a": 4, "p": 4}, {"p": 5, "a": 5}],
    ]


def test_uniform_rows_stay_one_batch_and_empty_is_empty():
    rows = [{"a": i} for i in range(1000)]
    assert _same_keys(rows) == [rows]
    assert _same_keys([]) == []
