from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.genotyping_study import GenotypingStudy
from gemini.api.genotype_record import GenotypeRecord
from gemini.rest_api.models import (
    GenotypingStudyInput,
    GenotypingStudyOutput,
    GenotypingStudyUpdate,
    GenotypeRecordBulkInput,
    GenotypeRecordOutput,
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
            if studies is None:
                return Response(content=RESTAPIError(error="No genotyping studies found", error_description=""), status_code=404)
            return studies
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
            studies = GenotypingStudy.search(study_name=study_name, study_info=study_info, experiment_name=experiment_name)
            if studies is None:
                return Response(content=RESTAPIError(error="No genotyping studies found", error_description=""), status_code=404)
            return studies
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

    @get(path="/id/{study_id:str}/records", sync_to_thread=True)
    def get_records(
        self,
        study_id: str,
        variant_name: Optional[str] = None,
        accession_name: Optional[str] = None,
        chromosome: Optional[int] = None,
        limit: int = 100,
    ) -> List[GenotypeRecordOutput]:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            records = GenotypeRecord.search(
                study_name=study.study_name,
                variant_name=variant_name,
                accession_name=accession_name,
                chromosome=chromosome,
            )
            if records is None:
                return Response(content=RESTAPIError(error="No records found", error_description=""), status_code=404)
            return records[:limit]
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
