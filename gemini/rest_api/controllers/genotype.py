from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.genotype import Genotype
from gemini.api.genotype_record import GenotypeRecord
from gemini.rest_api.models import (
    GenotypeInput,
    GenotypeOutput,
    GenotypeUpdate,
    GenotypeRecordBulkInput,
    GenotypeRecordOutput,
    ExperimentOutput,
    RESTAPIError,
    str_to_dict,
    JSONB,
)

from typing import List, Annotated, Optional


class GenotypeController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_genotypes(self, limit: int = 100, offset: int = 0) -> List[GenotypeOutput]:
        try:
            genotypes = Genotype.get_all(limit=limit, offset=offset)
            if genotypes is None:
                error = RESTAPIError(
                    error="No genotypes found",
                    error_description="There are no genotypes available in the database"
                )
                return Response(content=error, status_code=404)
            return genotypes
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all genotypes"
            )
            return Response(content=error, status_code=500)

    @get(sync_to_thread=True)
    def get_genotypes(
        self,
        genotype_name: Optional[str] = None,
        genotype_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = None,
    ) -> List[GenotypeOutput]:
        try:
            if genotype_info is not None:
                genotype_info = str_to_dict(genotype_info)
            genotypes = Genotype.search(
                genotype_name=genotype_name,
                genotype_info=genotype_info,
                experiment_name=experiment_name,
            )
            if genotypes is None:
                error = RESTAPIError(
                    error="No genotypes found",
                    error_description="No genotypes were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return genotypes
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving genotypes"
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{genotype_id:str}", sync_to_thread=True)
    def get_genotype_by_id(self, genotype_id: str) -> GenotypeOutput:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return genotype
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the genotype"
            )
            return Response(content=error, status_code=500)

    @post(sync_to_thread=True)
    def create_genotype(self, data: Annotated[GenotypeInput, Body]) -> GenotypeOutput:
        try:
            genotype = Genotype.create(
                genotype_name=data.genotype_name,
                genotype_info=data.genotype_info,
                experiment_name=data.experiment_name,
            )
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype creation failed",
                    error_description="The genotype could not be created"
                )
                return Response(content=error, status_code=500)
            return genotype
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the genotype"
            )
            return Response(content=error, status_code=500)

    @patch(path="/id/{genotype_id:str}", sync_to_thread=True)
    def update_genotype(self, genotype_id: str, data: Annotated[GenotypeUpdate, Body]) -> GenotypeOutput:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            genotype = genotype.update(
                genotype_name=data.genotype_name,
                genotype_info=data.genotype_info,
            )
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype update failed",
                    error_description="The genotype could not be updated"
                )
                return Response(content=error, status_code=500)
            return genotype
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the genotype"
            )
            return Response(content=error, status_code=500)

    @delete(path="/id/{genotype_id:str}", sync_to_thread=True)
    def delete_genotype(self, genotype_id: str) -> None:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error_html = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                ).to_html()
                return Response(content=error_html, status_code=404)
            is_deleted = genotype.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Genotype deletion failed",
                    error_description="The genotype could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the genotype"
            )
            return Response(content=error, status_code=500)

    # -- Association endpoints --

    @get(path="/id/{genotype_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(self, genotype_id: str) -> List[ExperimentOutput]:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiments = genotype.get_associated_experiments()
            if not experiments:
                error = RESTAPIError(
                    error="No associated experiments found",
                    error_description="The genotype has no associated experiments"
                )
                return Response(content=error, status_code=404)
            return experiments
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated experiments"
            )
            return Response(content=error, status_code=500)

    # -- Record endpoints --

    @post(path="/id/{genotype_id:str}/records", sync_to_thread=True)
    def upload_genotype_records(
        self, genotype_id: str, data: Annotated[GenotypeRecordBulkInput, Body]
    ) -> dict:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            records = []
            for r in data.records:
                r.setdefault("genotype_id", str(genotype.id))
                r.setdefault("genotype_name", genotype.genotype_name)
                records.append(GenotypeRecord(**r))
            success, ids = GenotypeRecord.insert(records)
            if not success:
                error = RESTAPIError(
                    error="Record upload failed",
                    error_description="The genotype records could not be uploaded"
                )
                return Response(content=error, status_code=500)
            return {"inserted_count": len(ids), "ids": [str(i) for i in ids]}
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while uploading genotype records"
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{genotype_id:str}/records", sync_to_thread=True)
    def get_genotype_records(
        self,
        genotype_id: str,
        variant_name: Optional[str] = None,
        population_name: Optional[str] = None,
        chromosome: Optional[int] = None,
        limit: int = 100,
    ) -> List[GenotypeRecordOutput]:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            records = GenotypeRecord.search(
                genotype_name=genotype.genotype_name,
                variant_name=variant_name,
                population_name=population_name,
                chromosome=chromosome,
            )
            if records is None:
                error = RESTAPIError(
                    error="No records found",
                    error_description="No genotype records were found"
                )
                return Response(content=error, status_code=404)
            return records[:limit]
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving genotype records"
            )
            return Response(content=error, status_code=500)

    # -- Export endpoint --

    @get(path="/id/{genotype_id:str}/export", sync_to_thread=True)
    def export_genotype(
        self,
        genotype_id: str,
        format: str = "hapmap",
        coding: str = "012",
    ) -> Response:
        try:
            genotype = Genotype.get_by_id(id=genotype_id)
            if genotype is None:
                error = RESTAPIError(
                    error="Genotype not found",
                    error_description="The genotype with the given ID was not found"
                )
                return Response(content=error, status_code=404)

            content = genotype.export(format=format, coding=coding)
            if not content:
                error = RESTAPIError(
                    error="No data to export",
                    error_description="No genotype records found for export"
                )
                return Response(content=error, status_code=404)

            ext_map = {
                "hapmap": ".hmp.txt",
                "vcf": ".vcf",
                "numeric": ".num.txt",
                "plink": ".ped",
            }
            mime_map = {
                "hapmap": "text/tab-separated-values",
                "vcf": "text/plain",
                "numeric": "text/tab-separated-values",
                "plink": "text/plain",
            }
            ext = ext_map.get(format, ".txt")
            mime = mime_map.get(format, "text/plain")
            filename = f"{genotype.genotype_name}{ext}"

            return Response(
                content=content,
                media_type=mime,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except ValueError as e:
            error = RESTAPIError(
                error=str(e),
                error_description="Invalid export format"
            )
            return Response(content=error, status_code=400)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while exporting genotype data"
            )
            return Response(content=error, status_code=500)
