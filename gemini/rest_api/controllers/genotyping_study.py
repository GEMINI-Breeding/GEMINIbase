from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.genotyping_study import GenotypingStudy
from gemini.api.genotype_record import GenotypeRecord
from gemini.api.variant import Variant
from gemini.api.accession import Accession
from gemini.db.models.variants import VariantModel
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
from gemini.db.core.base import db_engine
from gemini.rest_api.models import (
    GenotypingStudyInput,
    GenotypingStudyOutput,
    GenotypingStudyUpdate,
    GenotypeRecordBulkInput,
    GenotypeRecordOutput,
    GenotypeMatrixBatchInput,
    GenotypeMatrixBatchResult,
    ExperimentOutput,
    RESTAPIError,
    str_to_dict,
    JSONB,
)

from typing import List, Annotated, Optional


class GenotypingStudyController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_studies(self, limit: int = 100, offset: int = 0) -> List[GenotypingStudyOutput]:
        try:
            studies = GenotypingStudy.get_all(limit=limit, offset=offset)
            return studies or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(sync_to_thread=True)
    def search_studies(
        self,
        study_name: Optional[str] = None,
        study_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = None,
    ) -> List[GenotypingStudyOutput]:
        try:
            if study_info is not None:
                study_info = str_to_dict(study_info)
            return GenotypingStudy.search(study_name=study_name, study_info=study_info, experiment_name=experiment_name) or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{study_id:str}", sync_to_thread=True)
    def get_study_by_id(self, study_id: str) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Genotyping study not found", error_description=""), status_code=404)
            return study
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(sync_to_thread=True)
    def create_study(self, data: Annotated[GenotypingStudyInput, Body]) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.create(
                study_name=data.study_name,
                study_info=data.study_info,
                experiment_name=data.experiment_name,
            )
            if study is None:
                return Response(content=RESTAPIError(error="Creation failed", error_description=""), status_code=500)
            return study
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @patch(path="/id/{study_id:str}", sync_to_thread=True)
    def update_study(self, study_id: str, data: Annotated[GenotypingStudyUpdate, Body]) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            study = study.update(study_name=data.study_name, study_info=data.study_info)
            if study is None:
                return Response(content=RESTAPIError(error="Update failed", error_description=""), status_code=500)
            return study
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @delete(path="/id/{study_id:str}", sync_to_thread=True)
    def delete_study(self, study_id: str) -> None:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description="").to_html(), status_code=404)
            if not study.delete():
                return Response(content=RESTAPIError(error="Deletion failed", error_description=""), status_code=500)
            return None
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{study_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(self, study_id: str) -> List[ExperimentOutput]:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            experiments = study.get_associated_experiments()
            if not experiments:
                return Response(content=RESTAPIError(error="No associated experiments", error_description=""), status_code=404)
            return experiments
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(path="/id/{study_id:str}/records", sync_to_thread=True)
    def upload_records(self, study_id: str, data: Annotated[GenotypeRecordBulkInput, Body]) -> dict:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            records = []
            for r in data.records:
                r.setdefault("study_id", str(study.id))
                r.setdefault("study_name", study.study_name)
                records.append(GenotypeRecord(**r))
            success, ids = GenotypeRecord.insert(records)
            if not success:
                return Response(content=RESTAPIError(error="Upload failed", error_description=""), status_code=500)
            return {"inserted_count": len(ids), "ids": [str(i) for i in ids]}
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(path="/id/{study_id:str}/ingest-matrix", sync_to_thread=True)
    def ingest_matrix(
        self,
        study_id: str,
        data: Annotated[GenotypeMatrixBatchInput, Body],
    ) -> GenotypeMatrixBatchResult:
        try:
            return _ingest_matrix_impl(study_id, data)
        except Exception as e:
            import logging, traceback
            logging.getLogger(__name__).error(
                "ingest_matrix failed: %s\n%s", e, traceback.format_exc(),
            )
            return Response(
                content=RESTAPIError(error=str(e), error_description=""),
                status_code=500,
            )

    @get(path="/id/{study_id:str}/records", sync_to_thread=True)
    def get_records(
        self,
        study_id: str,
        variant_name: Optional[str] = None,
        accession_name: Optional[str] = None,
        chromosome: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GenotypeRecordOutput]:
        """
        Paginated genotype-record listing scoped to a single study. The
        previous implementation routed through GenotypeRecord.search,
        which materialized every matching row into Python before
        slicing — a 32k-variant × 310-sample study (~10M rows) hangs
        the browser and burns the server's memory. Here we push limit/
        offset straight to the DB and ORDER BY the primary key so the
        page output is stable across calls.
        """
        from sqlalchemy import select

        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=""),
                    status_code=404,
                )

            limit = max(1, min(limit, 500))
            offset = max(0, offset)

            with db_engine.get_session() as session:
                q = select(GenotypeRecordModel).where(
                    GenotypeRecordModel.study_id == str(study.id)
                )
                if variant_name:
                    q = q.where(GenotypeRecordModel.variant_name == variant_name)
                if accession_name:
                    q = q.where(GenotypeRecordModel.accession_name == accession_name)
                if chromosome is not None:
                    q = q.where(GenotypeRecordModel.chromosome == chromosome)
                q = q.order_by(GenotypeRecordModel.id).offset(offset).limit(limit)
                rows = session.execute(q).scalars().all()

            return [GenotypeRecordOutput.model_validate(r) for r in rows]
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{study_id:str}/export", sync_to_thread=True)
    def export_study(self, study_id: str, format: str = "hapmap", coding: str = "012") -> Response:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            content = study.export(format=format, coding=coding)
            if not content:
                return Response(content=RESTAPIError(error="No data to export", error_description=""), status_code=404)
            ext_map = {"hapmap": ".hmp.txt", "vcf": ".vcf", "numeric": ".num.txt", "plink": ".ped"}
            mime_map = {"hapmap": "text/tab-separated-values", "vcf": "text/plain", "numeric": "text/tab-separated-values", "plink": "text/plain"}
            ext = ext_map.get(format, ".txt")
            mime = mime_map.get(format, "text/plain")
            filename = f"{study.study_name}{ext}"
            return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
        except ValueError as e:
            return Response(content=RESTAPIError(error=str(e), error_description="Invalid export format"), status_code=400)
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)


def _ingest_matrix_impl(
    study_id: str, data: GenotypeMatrixBatchInput,
) -> GenotypeMatrixBatchResult:
    """Body of POST /genotyping_studies/{id}/ingest-matrix, extracted so
    tests can exercise it without Litestar routing overhead, and so the
    endpoint handler stays a thin try/except that converts raw exceptions
    to 500s with a logged traceback."""
    from sqlalchemy import select

    errors: list[str] = []
    study = GenotypingStudy.get_by_id(id=study_id)
    if study is None:
        return Response(
            content=RESTAPIError(error="Not found", error_description=""),
            status_code=404,
        )

    sample_headers = data.sample_headers or []
    variant_rows = data.variant_rows or []
    if not sample_headers or not variant_rows:
        return GenotypeMatrixBatchResult(
            variants_inserted=0, records_inserted=0, errors=["Empty batch"]
        )

    # Resolve accession_name -> id for every sample header. Caller is
    # responsible for upstream skip/create decisions; unknown names are
    # reported as errors and their column is dropped from the batch.
    with db_engine.get_session() as session:
        acc_rows = session.execute(
            select(AccessionModel.id, AccessionModel.accession_name).where(
                AccessionModel.accession_name.in_(sample_headers)
            )
        ).all()
    accession_id_by_name = {row.accession_name: row.id for row in acc_rows}
    resolved_sample_indices: list[int] = []
    for idx, name in enumerate(sample_headers):
        if name in accession_id_by_name:
            resolved_sample_indices.append(idx)
        else:
            errors.append(f"Unknown accession: {name}")

    # Idempotent variant upsert. Rows missing required NOT NULL columns
    # (chromosome/position/alleles) get defaulted so ingest doesn't die on
    # a partial HapMap header.
    variant_payload: list[dict] = []
    for vr in variant_rows:
        variant_payload.append({
            "variant_name": vr.variant_name,
            "chromosome": vr.chromosome if vr.chromosome is not None else 0,
            "position": vr.position if vr.position is not None else 0.0,
            "alleles": vr.alleles or "",
            "design_sequence": vr.design_sequence or "",
            "variant_info": {},
        })
    inserted_variant_ids = VariantModel.insert_bulk("variant_unique", variant_payload)
    variants_inserted = len(inserted_variant_ids)

    # insert_bulk returns only newly-inserted IDs; existing variants need a
    # name lookup so we can build records that reference them.
    with db_engine.get_session() as session:
        v_rows = session.execute(
            select(VariantModel.id, VariantModel.variant_name).where(
                VariantModel.variant_name.in_([vr.variant_name for vr in variant_rows])
            )
        ).all()
    variant_id_by_name = {row.variant_name: row.id for row in v_rows}

    # Flatten matrix → one record per (variant, resolved_sample) with a
    # non-null call.
    record_info = data.record_info or {}
    record_payload: list[dict] = []
    for vr in variant_rows:
        variant_id = variant_id_by_name.get(vr.variant_name)
        if variant_id is None:
            errors.append(f"Variant not resolved: {vr.variant_name}")
            continue
        calls = vr.calls or []
        for sample_idx in resolved_sample_indices:
            if sample_idx >= len(calls):
                continue
            call_value = calls[sample_idx]
            if call_value is None:
                continue
            call_str = str(call_value).strip()
            if not call_str:
                continue
            sample_name = sample_headers[sample_idx]
            accession_id = accession_id_by_name[sample_name]
            record_payload.append({
                "study_id": str(study.id),
                "study_name": study.study_name,
                "variant_id": str(variant_id),
                "variant_name": vr.variant_name,
                "chromosome": vr.chromosome if vr.chromosome is not None else 0,
                "position": vr.position if vr.position is not None else 0.0,
                "accession_id": str(accession_id),
                "accession_name": sample_name,
                "call_value": call_str[:10],
                "record_info": record_info,
            })

    records_inserted = 0
    if record_payload:
        inserted_record_ids = GenotypeRecordModel.insert_bulk(
            "genotype_records_unique", record_payload
        )
        records_inserted = len(inserted_record_ids)

    return GenotypeMatrixBatchResult(
        variants_inserted=variants_inserted,
        records_inserted=records_inserted,
        errors=errors,
    )
