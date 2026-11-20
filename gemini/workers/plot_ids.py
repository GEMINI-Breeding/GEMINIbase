"""A plot's identifier as the field names it.

Most fields number their plots (101, 102, …); some name a few with letters
(check plots ``KW1``…``KW20``, ``B12``). The database keeps the identifier
as text. Everywhere else a whole number stays an int, so numbered plots
read and compare as they always have, and any other identifier is its
trimmed text. No dependencies: workers import this too.
"""
from typing import Any, Optional, Union


def normalize_plot_number(v: Any) -> Optional[Union[int, str]]:
    """int for a whole number (101, "101", 101.0, " 101 "), trimmed text
    for any other identifier ("KW1"), None for nothing (None, "", NaN, bool)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return int(v) if v.is_integer() else str(v)
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    try:
        f = float(s)
    except ValueError:
        return s
    if f != f:
        return None
    return int(f) if f.is_integer() else s


def plot_number_key(v: Any):
    """Sort key: numbered plots by value first, then named ones by text,
    with a trailing number compared by value (KW2 before KW10)."""
    n = normalize_plot_number(v)
    if n is None:
        return (2, "", 0)
    if isinstance(n, int):
        return (0, "", n)
    head = n.rstrip("0123456789")
    tail = n[len(head):]
    return (1, head, int(tail) if tail else -1)
