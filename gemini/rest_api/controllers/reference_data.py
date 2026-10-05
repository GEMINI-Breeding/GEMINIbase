"""
Reference-data controller.

Two-phase upload: (1) client posts the file to `/parse-headers`, the
server returns the column headers; (2) client picks a mapping for each
column — one of the canonical identity fields (`plot_id`, `col`, `row`,
`accession`) or a trait name — and posts the file again to `/upload`
along with the mapping JSON. The server parses the file through the
mapping, creates a ReferenceDataset record, bulk-inserts one
ReferencePlot row per data row, and returns the dataset metadata.

Aggregate queries over trait values are served from the same controller
so the dashboard can chart across all plots in a dataset.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Annotated, List, Optional

import pandas as pd
from litestar import Response
from litestar.controller import Controller
from litestar.enums import RequestEncodingType
from litestar.handlers import delete, get, post
from litestar.params import Body

from gemini.api.reference_data import (
    IDENTITY_FIELDS,
    ReferenceDataset,
)
from gemini.rest_api.controllers.files import (
    minio_storage_config,
    minio_storage_provider,
)
from gemini.rest_api.models import (
    ParseHeadersRequest,
    ParseHeadersResponse,
    ReferenceAggregateOutput,
    ReferenceDatasetOutput,
    ReferencePlotList,
    ReferenceMatchReport,
    ReferencePlotOutput,
    ReferenceUploadRequest,
    RESTAPIError,
)

logger = logging.getLogger(__name__)


# Mapping value older upload dialogs send for "don't import this column".
IGNORE_MAPPING = "__ignore__"

# "No value" spellings in field sheets, beyond pandas' defaults.
MISSING_TOKENS = {"", "-", ".", "na", "n/a", "nan", "#n/a"}

MAX_LISTED_ISSUES = 10


def _is_excel(filename: str) -> bool:
    return (filename or "").lower().endswith((".xls", ".xlsx", ".xlsm"))


def _sheet_names(filename: str, raw: bytes) -> List[str]:
    if not _is_excel(filename):
        return []
    return [str(s) for s in pd.ExcelFile(io.BytesIO(raw)).sheet_names]


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop blank rows and Excel's empty `Unnamed:` columns; trim header names."""
    df = df.dropna(how="all")
    df = df[[c for c in df.columns if not (str(c).startswith("Unnamed:") and df[c].isna().all())]]
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _read_dataframe(
    filename: str,
    raw: bytes,
    sheets: Optional[List[str]] = None,
    header_row: int = 0,
) -> pd.DataFrame:
    """Parse CSV or Excel bytes into a DataFrame of strings.

    CSV delimiter is sniffed (`,` `;` tab). `sheets` (Excel) are stacked,
    default first sheet. `header_row` is the 0-based row with column names.
    Adds `_sheet` / `_row` (spreadsheet row) for error messages.
    """
    if _is_excel(filename):
        frames = []
        for name in sheets or [0]:
            df = _clean_columns(
                pd.read_excel(io.BytesIO(raw), sheet_name=name, dtype=object, header=header_row)
            )
            df["_sheet"] = name if sheets and len(sheets) > 1 else None
            df["_row"] = df.index + header_row + 2
            frames.append(df)
        return pd.concat(frames, ignore_index=True, sort=False)

    text = raw.decode("utf-8-sig", errors="replace")
    first_line = next((ln for ln in text.splitlines()[header_row:] if ln.strip()), "")
    sep = max([",", ";", "\t"], key=first_line.count)
    df = _clean_columns(
        pd.read_csv(io.StringIO(text), dtype=object, sep=sep, header=header_row, skip_blank_lines=False)
    )
    df["_sheet"] = None
    df["_row"] = df.index + header_row + 2
    return df


def _data_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c not in ("_sheet", "_row")]


def _is_missing(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return str(value).strip().lower() in MISSING_TOKENS


def _to_number(value) -> Optional[float]:
    """Parse a cell as a number; accepts a decimal comma (`4,5`)."""
    text = str(value).strip()
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_identity(field: str, value) -> Optional[str]:
    """Trim; write whole-number plot/row/col ids canonically (`0101`, `101.0` → `101`)."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    number = None if field == "accession" else _to_number(text)
    return str(int(number)) if number is not None and number.is_integer() else text


def _row_label(raw_row) -> str:
    sheet = raw_row.get("_sheet")
    return f"{sheet} row {raw_row.get('_row')}" if sheet else f"row {raw_row.get('_row')}"


def _apply_mapping(df: pd.DataFrame, mapping: dict) -> dict:
    """Rows as identity + traits dicts, via {source_column: canonical_name}.

    Rows with no trait values (blank lines, notes) are skipped and counted;
    rows without plot_id or col+row are skipped and listed; non-numeric trait
    cells are stored empty and listed.
    """
    rows: List[dict] = []
    skipped_empty = 0
    invalid: List[str] = []
    non_numeric: List[str] = []
    for _, raw_row in df.iterrows():
        normalized: dict = {"traits": {}}
        row_non_numeric: List[str] = []
        for source_col, canonical in mapping.items():
            if source_col not in df.columns:
                continue
            value = raw_row.get(source_col)
            if canonical in IDENTITY_FIELDS:
                normalized[canonical] = _normalize_identity(canonical, value)
            elif _is_missing(value):
                normalized["traits"][canonical] = None
            else:
                number = _to_number(value)
                if number is None:
                    row_non_numeric.append(f"{_row_label(raw_row)}: {source_col} = {str(value).strip()!r}")
                normalized["traits"][canonical] = number
        if not row_non_numeric and all(v is None for v in normalized["traits"].values()):
            skipped_empty += 1
            continue
        if not normalized.get("plot_id") and not (normalized.get("col") and normalized.get("row")):
            invalid.append(_row_label(raw_row))
            continue
        non_numeric.extend(row_non_numeric)
        rows.append(normalized)
    return {"rows": rows, "skipped_empty": skipped_empty, "invalid": invalid, "non_numeric": non_numeric}


def _listed(items: List[str]) -> str:
    more = len(items) - MAX_LISTED_ISSUES
    return "; ".join(items[:MAX_LISTED_ISSUES]) + (f"; and {more} more" if more > 0 else "")


def _upload_warnings(parsed: dict) -> List[str]:
    warnings: List[str] = []
    if parsed["invalid"]:
        warnings.append(
            f"Skipped {len(parsed['invalid'])} row(s) with no plot_id and no col/row: "
            + _listed(parsed["invalid"])
        )
    if parsed["non_numeric"]:
        warnings.append(
            f"{len(parsed['non_numeric'])} value(s) were not numbers and were left empty: "
            + _listed(parsed["non_numeric"])
        )
    return warnings


def _match_report(rows: List[dict], experiment: Optional[str], location: Optional[str]) -> Optional[dict]:
    """Rows that identify a plot in this experiment + site (plot number, then row/col)."""
    if not experiment or not location:
        return None
    from gemini.db.models.views.plot_view import PlotViewModel

    plots = PlotViewModel.search(experiment_name=experiment, site_name=location) or []
    numbers = {str(p.plot_number) for p in plots}
    coords = {(str(p.plot_row_number), str(p.plot_column_number)) for p in plots}
    matched = 0
    unmatched: List[str] = []
    for row in rows:
        pid = row.get("plot_id")
        if pid in numbers or (row.get("row"), row.get("col")) in coords:
            matched += 1
        elif (label := pid or f"row {row.get('row')}, col {row.get('col')}") not in unmatched:
            unmatched.append(label)
    return {
        "total": len(rows),
        "matched": matched,
        "unmatched": len(rows) - matched,
        "unmatched_examples": unmatched[:MAX_LISTED_ISSUES],
    }


def _original_object_info(original_object: Optional[str]) -> Optional[dict]:
    """dataset_info recording where the uploaded file lives in MinIO.

    The Files page stages the original through the chunked uploader before
    posting it here, so the bytes are already stored (and owned by the
    experiment's upload dataset). Record the pointer only if the object is
    really there — a stale or made-up path would render a download button
    that 404s.
    """
    if not original_object:
        return None
    try:
        if minio_storage_provider.file_exists(
            original_object, bucket_name=minio_storage_config.bucket_name
        ):
            return {"original_object": original_object}
    except Exception:
        logger.exception("could not check original_object %s", original_object)
    logger.warning("original_object %s not found; not recording it", original_object)
    return None


def _upload_info(original_object: Optional[str], legacy_reference_id: Optional[str]) -> Optional[dict]:
    """dataset_info for an upload: the original file's pointer, plus — for
    the previous-GEMI importer — the old dataset's id, which is how a
    re-import knows it already brought this one in (names aren't unique)."""
    info = dict(_original_object_info(original_object) or {})
    if legacy_reference_id:
        info["legacy_reference_id"] = legacy_reference_id
    return info or None


def _dataset_to_output(
    dataset: ReferenceDataset, plot_count: Optional[int] = None
) -> ReferenceDatasetOutput:
    return ReferenceDatasetOutput(
        id=str(dataset.id) if dataset.id else None,
        name=dataset.name,
        experiment=dataset.experiment,
        location=dataset.location,
        population=dataset.population,
        dataset_date=dataset.dataset_date,
        trait_columns=dataset.trait_columns or [],
        plot_count=plot_count if plot_count is not None else dataset.plot_count(),
        dataset_info=dataset.dataset_info,
        created_at=dataset.created_at,
    )


class ReferenceDataController(Controller):

    # ------------------------------------------------------------------
    # Header discovery
    # ------------------------------------------------------------------

    @post(
        path="/parse-headers",
        sync_to_thread=True,
    )
    def parse_headers(
        self,
        data: Annotated[
            ParseHeadersRequest,
            Body(media_type=RequestEncodingType.MULTI_PART),
        ],
        sheets: Optional[str] = None,
        header_row: Optional[int] = None,
    ) -> ParseHeadersResponse:
        """Column names as `/upload` parses them, plus sheets, a preview and numeric columns."""
        try:
            raw = data.file.file.read()
            filename = data.file.filename or ""
            df = _read_dataframe(
                filename, raw, sheets=json.loads(sheets) if sheets else None, header_row=header_row or 0
            )
            columns = _data_columns(df)
            numeric_columns = []
            for c in columns:
                values = [v for v in df[c].tolist() if not _is_missing(v)]
                if values and sum(_to_number(v) is not None for v in values) >= 0.8 * len(values):
                    numeric_columns.append(c)
            preview = [
                [None if _is_missing(v) else str(v) for v in row]
                for row in df[columns].head(5).itertuples(index=False, name=None)
            ]
            return ParseHeadersResponse(
                headers=columns,
                sheets=_sheet_names(filename, raw),
                preview=preview,
                numeric_columns=numeric_columns,
                row_count=len(df),
            )
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while parsing file headers.",
            )
            return Response(content=error, status_code=400)

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    @post(
        path="/upload",
        sync_to_thread=True,
    )
    def upload(
        self,
        data: Annotated[
            ReferenceUploadRequest,
            Body(media_type=RequestEncodingType.MULTI_PART),
        ],
        name: str,
        column_mapping_json: str,
        experiment: Optional[str] = None,
        location: Optional[str] = None,
        population: Optional[str] = None,
        date: Optional[str] = None,
        original_object: Optional[str] = None,
        legacy_reference_id: Optional[str] = None,
        sheets: Optional[str] = None,
        header_row: Optional[int] = None,
    ) -> ReferenceDatasetOutput:
        try:
            try:
                mapping = json.loads(column_mapping_json)
            except json.JSONDecodeError as e:
                error = RESTAPIError(
                    error="Invalid column_mapping_json",
                    error_description=f"Could not parse column_mapping_json: {e}",
                )
                return Response(content=error, status_code=400)

            if not isinstance(mapping, dict) or not mapping:
                error = RESTAPIError(
                    error="Invalid column_mapping_json",
                    error_description="column_mapping_json must be a non-empty JSON object.",
                )
                return Response(content=error, status_code=400)

            mapping = {k: v for k, v in mapping.items() if v and v != IGNORE_MAPPING}

            # Reject ambiguous mappings where two source columns would collapse
            # to the same non-identity (trait) canonical — the UI should guide
            # the user to rename one side rather than silently coalescing.
            trait_canonicals = [
                v for v in mapping.values() if v not in IDENTITY_FIELDS
            ]
            if len(trait_canonicals) != len(set(trait_canonicals)):
                dupes = {
                    c for c in trait_canonicals if trait_canonicals.count(c) > 1
                }
                error = RESTAPIError(
                    error="Duplicate column mapping",
                    error_description=(
                        "Multiple source columns map to the same trait: "
                        + ", ".join(sorted(dupes))
                    ),
                )
                return Response(content=error, status_code=400)

            raw = data.file.file.read()
            try:
                df = _read_dataframe(
                    data.file.filename or "",
                    raw,
                    sheets=json.loads(sheets) if sheets else None,
                    header_row=header_row or 0,
                )
            except Exception as e:
                error = RESTAPIError(
                    error="Unreadable file",
                    error_description=f"Could not parse the uploaded file: {e}",
                )
                return Response(content=error, status_code=400)

            parsed = _apply_mapping(df, mapping)
            rows = parsed["rows"]
            if not rows:
                description = (
                    "No row has a plot_id or both col and row: " + _listed(parsed["invalid"])
                    if parsed["invalid"]
                    else "The uploaded file has no data rows with values."
                )
                error = RESTAPIError(error="Invalid data", error_description=description)
                return Response(content=error, status_code=400)

            trait_columns = sorted(
                {c for c in mapping.values() if c not in IDENTITY_FIELDS}
            )

            dataset_date_parsed = None
            if date:
                try:
                    dataset_date_parsed = datetime.fromisoformat(date).date()
                except ValueError:
                    pass

            dataset = ReferenceDataset.create(
                name=name,
                experiment=experiment,
                location=location,
                population=population,
                dataset_date=dataset_date_parsed,
                trait_columns=trait_columns,
                dataset_info=_upload_info(original_object, legacy_reference_id),
            )
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not created",
                    error_description="The reference dataset could not be created.",
                )
                return Response(content=error, status_code=500)

            try:
                inserted = dataset.insert_plots(rows)
            except Exception as e:
                # Roll back the dataset so the user doesn't see an empty "success".
                logger.exception("insert_plots failed — rolling back the dataset")
                dataset.delete()
                error = RESTAPIError(
                    error="Plot insertion failed",
                    error_description=f"Failed to insert plots: {e}",
                )
                return Response(content=error, status_code=500)
            output = _dataset_to_output(dataset, plot_count=inserted)
            report = _match_report(rows, experiment, location)
            if report:
                output.match_report = ReferenceMatchReport(**report)
            output.warnings = _upload_warnings(parsed)
            output.skipped_empty_rows = parsed["skipped_empty"]
            return output
        except Exception as e:
            logger.exception("reference-data upload failed")
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred during reference data upload.",
            )
            return Response(content=error, status_code=500)

    # ------------------------------------------------------------------
    # List / Get / Delete
    # ------------------------------------------------------------------

    @get(path="/", sync_to_thread=True)
    def list_datasets(
        self,
        experiment: Optional[str] = None,
        location: Optional[str] = None,
        population: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[ReferenceDatasetOutput]:
        try:
            datasets = ReferenceDataset.search(
                name=name,
                experiment=experiment,
                location=location,
                population=population,
            ) or []
            return [_dataset_to_output(d) for d in datasets]
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while listing reference datasets.",
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{dataset_id:str}", sync_to_thread=True)
    def get_dataset(self, dataset_id: str) -> ReferenceDatasetOutput:
        try:
            dataset = ReferenceDataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="The reference dataset was not found.",
                )
                return Response(content=error, status_code=404)
            return _dataset_to_output(dataset)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the dataset.",
            )
            return Response(content=error, status_code=500)

    @delete(path="/id/{dataset_id:str}", sync_to_thread=True)
    def delete_dataset(self, dataset_id: str) -> None:
        dataset = ReferenceDataset.get_by_id(id=dataset_id)
        if dataset is None:
            return None
        dataset.delete()
        return None

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------

    @get(path="/id/{dataset_id:str}/plots-all", sync_to_thread=True)
    def get_all_plots(
        self, dataset_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> ReferencePlotList:
        try:
            dataset = ReferenceDataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="The reference dataset was not found.",
                )
                return Response(content=error, status_code=404)
            plots = dataset.get_plots(limit=limit, offset=offset)
            outputs = [ReferencePlotOutput.model_validate(p) for p in plots]
            return ReferencePlotList(data=outputs, count=len(outputs))
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving plots.",
            )
            return Response(content=error, status_code=500)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    @get(path="/id/{dataset_id:str}/aggregate", sync_to_thread=True)
    def aggregate(
        self,
        dataset_id: str,
        metric: str,
        aggregation: str = "avg",
    ) -> ReferenceAggregateOutput:
        try:
            dataset = ReferenceDataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="The reference dataset was not found.",
                )
                return Response(content=error, status_code=404)
            try:
                value, count = dataset.aggregate_metric(
                    metric=metric, aggregation=aggregation
                )
            except ValueError as e:
                error = RESTAPIError(
                    error="Invalid aggregation",
                    error_description=str(e),
                )
                return Response(content=error, status_code=400)
            return ReferenceAggregateOutput(
                dataset_id=str(dataset.id),
                metric=metric,
                aggregation=aggregation.lower(),
                value=value,
                count=count,
            )
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while computing the aggregate.",
            )
            return Response(content=error, status_code=500)
