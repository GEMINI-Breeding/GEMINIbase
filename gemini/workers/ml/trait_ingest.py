"""Auto-ingest EXTRACT_TRAITS output into the `trait_records` columnar table.

The EXTRACT_TRAITS worker writes a per-plot GeoJSON to MinIO. Before this
helper landed, that artifact was orphaned — the analyze surface had no
way to find it. This module closes the gap: after the worker uploads
the GeoJSON, it calls `ingest_extracted_traits()` which:

  1. Parses experiment/season/site/population/date out of the MinIO
     output path so it doesn't need separate job parameters.
  2. Idempotently creates the dataset that scopes the records (via
     `POST /api/datasets`).
  3. For each trait column (Vegetation_Fraction, optionally
     Height_95p_meters): idempotently creates the trait definition,
     then POSTs `/api/traits/id/{trait_id}/records/bulk` with one row
     per plot feature.

Authentication and retry use the same WorkerSession the worker already
uses to PATCH job status. Any error is logged and re-raised so the
calling worker job fails with a descriptive message — the GeoJSON is
already written to MinIO at that point, so the user can re-run ingest
later (see `gemini.scripts.backfill_plot_geometry`).

Manual traits land in the same `trait_records` table via the CSV
import wizard's path; both data sources are now interchangeable from
the consumer's perspective.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

from gemini.workers.auth import WorkerSession

logger = logging.getLogger(__name__)


# Trait columns the EXTRACT_TRAITS worker produces. Anything not in this
# allow-list is ignored even if a future extractor adds new properties to
# the output GeoJSON — ingest then needs an intentional code change here.
EXTRACTED_TRAIT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Vegetation_Fraction", ""),
    ("Height_95p_meters", "m"),
)

# Pydantic / Litestar models on the server side import this enum value;
# we duplicate it here as a literal to avoid pulling the SQLAlchemy
# dependency stack into the worker for one int. See
# `gemini.api.enums.GEMINIDatasetType.Trait` (= 2).
_DATASET_TYPE_TRAIT = 2


def parse_scope_from_output_path(output_path: str) -> Optional[dict]:
    """Parse `Processed/{year}/{exp}/{loc}/{pop}/{date}/{platform}/{sensor}/...`
    into scope components. Returns None when the path doesn't follow that
    convention (e.g. someone wrote traits under a non-standard prefix —
    we'd rather skip ingest than guess).
    """
    if not output_path:
        return None
    parts = [p for p in output_path.split("/") if p]
    if len(parts) < 8 or parts[0] != "Processed":
        return None
    return {
        "year": parts[1],
        "experiment_name": parts[2],
        "site_name": parts[3],
        "population_name": parts[4],
        "date": parts[5],
        "platform": parts[6],
        "sensor": parts[7],
    }


def _ensure_dataset(
    http: WorkerSession,
    *,
    dataset_name: str,
    experiment_name: str,
    collection_date: str,
) -> None:
    """POST `/api/datasets`. 4xx (already-exists) is treated as success —
    same idempotent pattern the CSV import wizard uses."""
    try:
        resp = http.post(
            "/api/datasets",
            json={
                "dataset_name": dataset_name,
                "experiment_name": experiment_name,
                "dataset_type_id": _DATASET_TYPE_TRAIT,
                "collection_date": collection_date,
                "dataset_info": {
                    "source": "EXTRACT_TRAITS",
                },
            },
        )
        # 200/201 = newly created. The controller's get-or-create path
        # returns 500 on collision; gemini.api.Dataset.create swallows
        # duplicate-key errors via get_or_create. Either way: continue.
        if resp.status_code >= 500:
            logger.info(
                f"Dataset POST returned {resp.status_code} for {dataset_name!r}; "
                f"continuing on the assumption it already exists."
            )
    except Exception as e:
        # Network-level error — bubble up; insert_trait_records will fail
        # at the validity check anyway.
        logger.warning(f"Dataset ensure failed for {dataset_name!r}: {e}")


def _ensure_trait(
    http: WorkerSession,
    *,
    trait_name: str,
    trait_units: str,
    experiment_name: str,
) -> Optional[str]:
    """Idempotent trait-ensure. Returns the trait_id, or None on failure."""
    # GET first — cheapest path when the trait already exists.
    try:
        resp = http.get(
            "/api/traits", params={"trait_name": trait_name}
        )
        if resp.ok:
            existing = resp.json()
            if isinstance(existing, list):
                for row in existing:
                    if isinstance(row, dict) and row.get("trait_name") == trait_name:
                        rid = row.get("id")
                        if rid:
                            return str(rid)
    except Exception as e:
        logger.debug(f"Trait pre-fetch failed for {trait_name!r}: {e}")

    # Not found → create. Trait names are globally unique, so a race
    # between two workers creating the same name collides on the unique
    # index; the second one gets a 4xx/5xx and falls through to GET.
    try:
        resp = http.post(
            "/api/traits",
            json={
                "trait_name": trait_name,
                "trait_units": trait_units or None,
                "trait_level_id": 2,  # Plot
                "experiment_name": experiment_name,
            },
        )
        if resp.ok:
            row = resp.json()
            if isinstance(row, dict):
                rid = row.get("id")
                if rid:
                    return str(rid)
    except Exception as e:
        logger.warning(f"Trait create failed for {trait_name!r}: {e}")

    # Fallback: re-query after a failed create (someone else won the race).
    try:
        resp = http.get(
            "/api/traits", params={"trait_name": trait_name}
        )
        if resp.ok:
            existing = resp.json()
            if isinstance(existing, list):
                for row in existing:
                    if isinstance(row, dict) and row.get("trait_name") == trait_name:
                        rid = row.get("id")
                        if rid:
                            return str(rid)
    except Exception as e:
        logger.warning(f"Trait re-fetch failed for {trait_name!r}: {e}")
    return None


def _features_to_records(
    features: Iterable[dict], trait_column: str
) -> list[dict]:
    """Project a list of GeoJSON features into TraitRecordBulkInput records
    for one trait column. Skips features missing plot_number/row/col.

    Accepts both the legacy `plot`/`row`/`column` short-hand from R5a
    snapshots and the canonical `plot_number`/`plot_row_number`/
    `plot_column_number` keys used by the import wizard. Records inherit
    the EXTRACT_TRAITS run timestamp at the caller — there's only one
    "time of measurement" per job.
    """

    def _as_int(v):
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.strip():
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None
        if isinstance(v, float):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        return None

    out: list[dict] = []
    for f in features:
        if not isinstance(f, dict):
            continue
        props = f.get("properties") or {}
        if not isinstance(props, dict):
            continue
        value = props.get(trait_column)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        plot_number = _as_int(
            props.get("plot_number")
            if props.get("plot_number") is not None
            else props.get("plot") or props.get("Plot")
        )
        plot_row = _as_int(
            props.get("plot_row_number")
            if props.get("plot_row_number") is not None
            else props.get("row") or props.get("Row")
        )
        plot_col = _as_int(
            props.get("plot_column_number")
            if props.get("plot_column_number") is not None
            else props.get("column")
            or props.get("Column")
            or props.get("col")
            or props.get("Col")
        )
        if plot_number is None or plot_row is None or plot_col is None:
            continue
        accession = (
            props.get("accession_name")
            or props.get("accession")
            or props.get("Accession")
            or props.get("Label")
        )
        out.append(
            {
                "plot_number": plot_number,
                "plot_row_number": plot_row,
                "plot_column_number": plot_col,
                "trait_value": value,
                "accession_name": accession
                if isinstance(accession, str) and accession
                else None,
                "record_info": {"source": "EXTRACT_TRAITS"},
            }
        )
    return out


def ingest_extracted_traits(
    http: WorkerSession,
    *,
    output_path: str,
    geojson: dict,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Ingest the EXTRACT_TRAITS GeoJSON into `trait_records`.

    Args:
        http: Authenticated WorkerSession (typically `self._http` from
            the calling worker).
        output_path: The MinIO key the GeoJSON was uploaded to. The
            scope (experiment/season/site/population/date/sensor) is
            parsed from this path.
        geojson: The mutated FeatureCollection returned by
            `extract_traits_from_ortho` — each feature carries one
            value per trait column.
        timestamp: Per-record timestamp. Defaults to "now".

    Returns:
        Dict mapping trait_name → records-inserted count. Empty when
        the scope can't be parsed or no records were ingested.
    """
    scope = parse_scope_from_output_path(output_path)
    if scope is None:
        logger.info(
            f"Trait ingest: skipping — output_path {output_path!r} does not "
            f"match the Processed/.../traits/ convention."
        )
        return {}
    features = (
        (geojson or {}).get("features") if isinstance(geojson, dict) else None
    )
    if not isinstance(features, list) or not features:
        return {}

    ts = (timestamp or datetime.now(timezone.utc)).isoformat()
    dataset_name = (
        f"EXTRACT_TRAITS {scope['date']} {scope['platform']}/{scope['sensor']}"
    )
    _ensure_dataset(
        http,
        dataset_name=dataset_name,
        experiment_name=scope["experiment_name"],
        collection_date=scope["date"],
    )

    counts: dict[str, int] = {}
    for trait_name, units in EXTRACTED_TRAIT_COLUMNS:
        records = _features_to_records(features, trait_name)
        if not records:
            continue
        # Stamp each record's timestamp (the bulk endpoint reads
        # row['timestamp']).
        for r in records:
            r["timestamp"] = ts

        trait_id = _ensure_trait(
            http,
            trait_name=trait_name,
            trait_units=units,
            experiment_name=scope["experiment_name"],
        )
        if trait_id is None:
            logger.warning(
                f"Trait ingest: could not resolve trait_id for {trait_name!r}; "
                f"skipping this column ({len(records)} records lost for "
                f"experiment {scope['experiment_name']!r})."
            )
            continue

        payload = {
            "records": records,
            "experiment_name": scope["experiment_name"],
            "season_name": scope["year"],
            "site_name": scope["site_name"],
            "dataset_name": dataset_name,
            "collection_date": f"{scope['date']}T00:00:00",
        }
        try:
            resp = http.post(
                f"/api/traits/id/{trait_id}/records/bulk", json=payload
            )
        except Exception as e:
            logger.error(
                f"Trait ingest: bulk POST raised for {trait_name!r}: {e}"
            )
            continue
        # The `populate_trait_record_ids` trigger raises 422 when an
        # accession_name is supplied but doesn't exist in `accessions`.
        # The boundary GeoJSON's `accession` property is user-authored
        # (field-design CSV); whether those rows exist in `accessions`
        # depends on whether the user has imported their germplasm
        # separately. Rather than fail the whole ingest in that case,
        # drop accession_name from every record and retry — the trait
        # values still land, scoped to plot only. The user can re-link
        # accessions later by re-importing the germplasm + re-running.
        if (
            not resp.ok
            and resp.status_code == 422
            and "accession" in (resp.text or "").lower()
            and any(r.get("accession_name") for r in records)
        ):
            logger.info(
                f"Trait ingest: 422 on accession lookup for {trait_name!r}; "
                f"retrying without accession_name (records will be orphan-linked "
                f"to plots only)."
            )
            stripped = [
                {**r, "accession_name": None} for r in records
            ]
            try:
                resp = http.post(
                    f"/api/traits/id/{trait_id}/records/bulk",
                    json={**payload, "records": stripped},
                )
            except Exception as e:
                logger.error(
                    f"Trait ingest: bulk POST retry raised for {trait_name!r}: {e}"
                )
                continue
        if not resp.ok:
            logger.error(
                f"Trait ingest: bulk POST returned {resp.status_code} for "
                f"{trait_name!r}: {resp.text[:300] if hasattr(resp, 'text') else ''}"
            )
            continue
        try:
            body = resp.json()
            n = int(body.get("inserted_count", len(records)))
        except Exception:
            n = len(records)
        counts[trait_name] = n
        logger.info(
            f"Trait ingest: inserted {n} {trait_name!r} records "
            f"({scope['experiment_name']}/{scope['year']}/{scope['site_name']})."
        )

    return counts
