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
from gemini.rest_api.models import (
    ParseHeadersRequest,
    ParseHeadersResponse,
    ReferenceAggregateOutput,
    ReferenceDatasetOutput,
    ReferencePlotList,
    ReferencePlotOutput,
    ReferenceUploadRequest,
    RESTAPIError,
)

logger = logging.getLogger(__name__)


def _read_dataframe(filename: str, raw: bytes) -> pd.DataFrame:
    """Parse CSV or Excel bytes into a DataFrame, with string-typed columns."""
    lower = (filename or "").lower()
    if lower.endswith((".xls", ".xlsx", ".xlsm")):
        return pd.read_excel(io.BytesIO(raw), dtype=object)
    return pd.read_csv(io.BytesIO(raw), dtype=object)


def _apply_mapping(df: pd.DataFrame, mapping: dict) -> List[dict]:
    """Translate raw DataFrame rows into identity + traits dicts using a mapping.

    mapping: {source_column: canonical_name}  — canonical_name is one of
             IDENTITY_FIELDS or any trait label.
    """
    rows: List[dict] = []
    # Build inverse lookup so we know which canonical name each column maps to.
    for _, raw_row in df.iterrows():
        normalized: dict = {"traits": {}}
        for source_col, canonical in mapping.items():
            if canonical is None or canonical == "":
                continue
            if source_col not in df.columns:
                continue
            value = raw_row.get(source_col)
            if pd.isna(value):
                value = None
            if canonical in IDENTITY_FIELDS:
                normalized[canonical] = None if value is None else str(value)
            else:
                # Keep trait values numeric when we can; fall back to str.
                if value is None:
                    normalized["traits"][canonical] = None
                else:
                    try:
                        normalized["traits"][canonical] = float(value)
                    except (TypeError, ValueError):
                        normalized["traits"][canonical] = str(value)
        rows.append(normalized)
    return rows


def _validate_rows(rows: List[dict]) -> Optional[str]:
    """Return an error string if any row lacks the minimum identity fields."""
    if not rows:
        return "The uploaded file has no data rows."
    for idx, row in enumerate(rows):
        has_plot_id = bool(row.get("plot_id"))
        has_coords = bool(row.get("col")) and bool(row.get("row"))
        if not has_plot_id and not has_coords:
            return (
                f"Row {idx + 1}: each row must have plot_id or both col and row."
            )
    return None


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
    ) -> ParseHeadersResponse:
        try:
            raw = data.file.file.read()
            df = _read_dataframe(data.file.filename or "", raw)
            headers = [str(h) for h in df.columns if h is not None and str(h).strip()]
            return ParseHeadersResponse(headers=headers)
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

            raw = data.file.file.read()
            try:
                df = _read_dataframe(data.file.filename or "", raw)
            except Exception as e:
                error = RESTAPIError(
                    error="Unreadable file",
                    error_description=f"Could not parse the uploaded file: {e}",
                )
                return Response(content=error, status_code=400)

            rows = _apply_mapping(df, mapping)
            error_msg = _validate_rows(rows)
            if error_msg:
                error = RESTAPIError(
                    error="Invalid data",
                    error_description=error_msg,
                )
                return Response(content=error, status_code=400)

            trait_columns = sorted(
                {
                    canonical
                    for canonical in mapping.values()
                    if canonical and canonical not in IDENTITY_FIELDS
                }
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
            )
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not created",
                    error_description="The reference dataset could not be created.",
                )
                return Response(content=error, status_code=500)

            inserted = dataset.insert_plots(rows)
            return _dataset_to_output(dataset, plot_count=inserted)
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
