from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.variant import Variant
from gemini.rest_api.models import (
    VariantInput,
    VariantBulkInput,
    VariantOutput,
    VariantUpdate,
    RESTAPIError,
    str_to_dict,
    JSONB,
    ID,
)

from typing import List, Annotated, Optional


class VariantController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_variants(self, limit: int = 100, offset: int = 0) -> List[VariantOutput]:
        try:
            variants = Variant.get_all(limit=limit, offset=offset)
            return variants or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all variants"
            )
            return Response(content=error, status_code=500)

    @get(sync_to_thread=True)
    def get_variants(
        self,
        variant_name: Optional[str] = None,
        chromosome: Optional[int] = None,
        alleles: Optional[str] = None,
        variant_info: Optional[JSONB] = None,
    ) -> List[VariantOutput]:
        try:
            if variant_info is not None:
                variant_info = str_to_dict(variant_info)
            variants = Variant.search(
                variant_name=variant_name,
                chromosome=chromosome,
                alleles=alleles,
                variant_info=variant_info,
            )
            return variants or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving variants"
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{variant_id:str}", sync_to_thread=True)
    def get_variant_by_id(self, variant_id: str) -> VariantOutput:
        try:
            variant = Variant.get_by_id(id=variant_id)
            if variant is None:
                error = RESTAPIError(
                    error="Variant not found",
                    error_description="The variant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return variant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the variant"
            )
            return Response(content=error, status_code=500)

    @post(sync_to_thread=True)
    def create_variant(self, data: Annotated[VariantInput, Body]) -> VariantOutput:
        try:
            variant = Variant.create(
                variant_name=data.variant_name,
                chromosome=data.chromosome,
                position=data.position,
                alleles=data.alleles,
                design_sequence=data.design_sequence,
                variant_info=data.variant_info,
            )
            if variant is None:
                error = RESTAPIError(
                    error="Variant creation failed",
                    error_description="The variant could not be created"
                )
                return Response(content=error, status_code=500)
            return variant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the variant"
            )
            return Response(content=error, status_code=500)

    @post(path="/bulk", sync_to_thread=True)
    def create_variants_bulk(self, data: Annotated[VariantBulkInput, Body]) -> dict:
        try:
            success, ids = Variant.create_bulk(data.variants)
            if not success:
                error = RESTAPIError(
                    error="Bulk variant creation failed",
                    error_description="The variants could not be created"
                )
                return Response(content=error, status_code=500)
            return {"inserted_count": len(ids), "ids": [str(i) for i in ids]}
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while bulk-creating variants"
            )
            return Response(content=error, status_code=500)

    @patch(path="/id/{variant_id:str}", sync_to_thread=True)
    def update_variant(self, variant_id: str, data: Annotated[VariantUpdate, Body]) -> VariantOutput:
        try:
            variant = Variant.get_by_id(id=variant_id)
            if variant is None:
                error = RESTAPIError(
                    error="Variant not found",
                    error_description="The variant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            variant = variant.update(
                variant_name=data.variant_name,
                chromosome=data.chromosome,
                position=data.position,
                alleles=data.alleles,
                design_sequence=data.design_sequence,
                variant_info=data.variant_info,
            )
            if variant is None:
                error = RESTAPIError(
                    error="Variant update failed",
                    error_description="The variant could not be updated"
                )
                return Response(content=error, status_code=500)
            return variant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the variant"
            )
            return Response(content=error, status_code=500)

    @delete(path="/id/{variant_id:str}", sync_to_thread=True)
    def delete_variant(self, variant_id: str) -> None:
        try:
            variant = Variant.get_by_id(id=variant_id)
            if variant is None:
                error_html = RESTAPIError(
                    error="Variant not found",
                    error_description="The variant with the given ID was not found"
                ).to_html()
                return Response(content=error_html, status_code=404)
            is_deleted = variant.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Variant deletion failed",
                    error_description="The variant could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the variant"
            )
            return Response(content=error, status_code=500)
