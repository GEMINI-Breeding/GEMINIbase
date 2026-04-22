"""
Germplasm resolver: translates spreadsheet-style identifiers (accession names,
line names, or arbitrary aliases) into canonical Accession or Line IDs at
import time.

Resolution order (first deterministic hit wins):
  1. accession_name exact (case-insensitive)
  2. line_name exact (case-insensitive)
  3. alias with scope='experiment' for the supplied experiment_id
  4. alias with scope='global'
  5. unresolved

No fuzzy matching in this slice — the match_kind enum reserves
'fuzzy_accession' / 'fuzzy_line' for a future extension. Callers are
responsible for whitespace normalization of inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from sqlalchemy import text

from gemini.db.core.base import db_engine

logger = logging.getLogger(__name__)


MATCH_KINDS = (
    "accession_exact",
    "line_exact",
    "alias_experiment",
    "alias_global",
    "fuzzy_accession",
    "fuzzy_line",
    "unresolved",
)


@dataclass
class ResolveCandidate:
    id: str
    kind: str            # 'accession' | 'line'
    name: str
    score: float = 1.0


@dataclass
class ResolveResult:
    input_name: str
    match_kind: str
    accession_id: Optional[str] = None
    line_id: Optional[str] = None
    canonical_name: Optional[str] = None
    candidates: List[ResolveCandidate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["candidates"] = [asdict(c) for c in self.candidates]
        return d


_RESOLVE_SQL = text(
    """
    WITH inputs(idx, raw) AS (
        SELECT i, n FROM unnest(CAST(:names AS text[])) WITH ORDINALITY AS t(n, i)
    ),
    norm AS (
        SELECT idx, raw, lower(raw) AS lc FROM inputs
    ),
    acc_exact AS (
        SELECT n.idx, a.id::text AS id, a.accession_name AS name
        FROM norm n
        JOIN gemini.accessions a ON lower(a.accession_name) = n.lc
    ),
    line_exact AS (
        SELECT n.idx, l.id::text AS id, l.line_name AS name
        FROM norm n
        JOIN gemini.lines l ON lower(l.line_name) = n.lc
        WHERE n.idx NOT IN (SELECT idx FROM acc_exact)
    ),
    alias_exp AS (
        SELECT n.idx,
               al.accession_id::text AS accession_id,
               al.line_id::text      AS line_id,
               COALESCE(a.accession_name, l.line_name) AS name
        FROM norm n
        JOIN gemini.accession_aliases al
             ON lower(al.alias) = n.lc
            AND al.scope = 'experiment'
            AND al.experiment_id = CAST(NULLIF(:experiment_id, '') AS uuid)
        LEFT JOIN gemini.accessions a ON a.id = al.accession_id
        LEFT JOIN gemini.lines l      ON l.id = al.line_id
        WHERE n.idx NOT IN (SELECT idx FROM acc_exact)
          AND n.idx NOT IN (SELECT idx FROM line_exact)
    ),
    alias_glob AS (
        SELECT n.idx,
               al.accession_id::text AS accession_id,
               al.line_id::text      AS line_id,
               COALESCE(a.accession_name, l.line_name) AS name
        FROM norm n
        JOIN gemini.accession_aliases al
             ON lower(al.alias) = n.lc
            AND al.scope = 'global'
        LEFT JOIN gemini.accessions a ON a.id = al.accession_id
        LEFT JOIN gemini.lines l      ON l.id = al.line_id
        WHERE n.idx NOT IN (SELECT idx FROM acc_exact)
          AND n.idx NOT IN (SELECT idx FROM line_exact)
          AND n.idx NOT IN (SELECT idx FROM alias_exp)
    )
    SELECT n.idx, n.raw,
           ae.id   AS acc_exact_id,   ae.name   AS acc_exact_name,
           le.id   AS line_exact_id,  le.name   AS line_exact_name,
           aex.accession_id AS alias_exp_acc_id, aex.line_id AS alias_exp_line_id, aex.name AS alias_exp_name,
           agl.accession_id AS alias_glob_acc_id, agl.line_id AS alias_glob_line_id, agl.name AS alias_glob_name
    FROM norm n
    LEFT JOIN acc_exact  ae  ON ae.idx = n.idx
    LEFT JOIN line_exact le  ON le.idx = n.idx
    LEFT JOIN alias_exp  aex ON aex.idx = n.idx
    LEFT JOIN alias_glob agl ON agl.idx = n.idx
    ORDER BY n.idx
    """
)


def resolve_germplasm(
    names: List[str],
    experiment_id: Optional[UUID | str] = None,
) -> List[ResolveResult]:
    """
    Resolve a batch of incoming names against canonical accessions/lines
    and their aliases. Returns one ResolveResult per input, in the same
    order as `names`.
    """
    if not names:
        return []

    exp_param = str(experiment_id) if experiment_id is not None else ""

    with db_engine.get_session() as session:
        rows = session.execute(
            _RESOLVE_SQL,
            {"names": list(names), "experiment_id": exp_param},
        ).all()

    results: List[ResolveResult] = [None] * len(names)  # type: ignore[list-item]
    for row in rows:
        idx = row.idx - 1  # SQL ordinality is 1-based
        raw = row.raw
        if row.acc_exact_id:
            results[idx] = ResolveResult(
                input_name=raw,
                match_kind="accession_exact",
                accession_id=row.acc_exact_id,
                canonical_name=row.acc_exact_name,
            )
        elif row.line_exact_id:
            results[idx] = ResolveResult(
                input_name=raw,
                match_kind="line_exact",
                line_id=row.line_exact_id,
                canonical_name=row.line_exact_name,
            )
        elif row.alias_exp_acc_id or row.alias_exp_line_id:
            results[idx] = ResolveResult(
                input_name=raw,
                match_kind="alias_experiment",
                accession_id=row.alias_exp_acc_id,
                line_id=row.alias_exp_line_id,
                canonical_name=row.alias_exp_name,
            )
        elif row.alias_glob_acc_id or row.alias_glob_line_id:
            results[idx] = ResolveResult(
                input_name=raw,
                match_kind="alias_global",
                accession_id=row.alias_glob_acc_id,
                line_id=row.alias_glob_line_id,
                canonical_name=row.alias_glob_name,
            )
        else:
            results[idx] = ResolveResult(
                input_name=raw,
                match_kind="unresolved",
            )
    return results
