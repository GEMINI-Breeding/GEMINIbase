from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.trait_level import TraitLevel
from gemini.rest_api.models import TraitLevelInput, TraitLevelOutput, TraitLevelUpdate, RESTAPIError, str_to_dict, JSONB

from typing import List, Annotated, Optional

class TraitLevelController(Controller):

    # Get All Trait Levels
    @get(path="/all", sync_to_thread=True)
    def get_all_trait_levels(self, limit: int = 100, offset: int = 0) -> List[TraitLevelOutput]:
        try:
            trait_levels = TraitLevel.get_all(limit=limit, offset=offset)
            if trait_levels is None:
                error = RESTAPIError(
                    error="No trait levels found",
                    error_description="No trait levels were found"
                )
                return Response(content=error, status_code=404)
            return trait_levels
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all trait levels"
            )
            return Response(content=error, status_code=500)
        
    # Get all Trait Levels
    @get(sync_to_thread=True)
    def get_trait_levels(
        self,
        trait_level_name: Optional[str] = None,
        trait_level_info: Optional[JSONB] = None
    ) -> List[TraitLevelOutput]:
        try:
            if trait_level_info is not None:
                trait_level_info = str_to_dict(trait_level_info)

            trait_levels = TraitLevel.search(
                trait_level_name=trait_level_name,
                trait_level_info=trait_level_info
            )

            if trait_levels is None:
                error = RESTAPIError(
                    error="No trait levels found",
                    error_description="No trait levels were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return trait_levels
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait levels"
            )
            return Response(content=error_message, status_code=500)

    # Get Trait Level by ID
    @get(path="/id/{trait_level_id:int}", sync_to_thread=True)
    def get_trait_level_by_id(
        self, trait_level_id: int
    ) -> TraitLevelOutput:
        try:
            trait_level = TraitLevel.get_by_id(id=trait_level_id)
            if trait_level is None:
                error = RESTAPIError(
                    error="Trait level not found",
                    error_description="The trait level with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return trait_level
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait levels"
            )
            return Response(content=error_message, status_code=500)

    # Create Trait Level
    @post(sync_to_thread=True)
    def create_trait_level(
        self,
        data: Annotated[TraitLevelInput, Body]
    ) -> TraitLevelOutput:
        try:
            trait_level = TraitLevel.create(
                trait_level_name=data.trait_level_name,
                trait_level_info=data.trait_level_info
            )
            if trait_level is None:
                error = RESTAPIError(
                    error="An error occurred while creating trait level",
                    error_description="An error occurred while creating trait level"
                )
                return Response(content=error, status_code=500)
            return trait_level
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating trait level"
            )
            return Response(content=error_message, status_code=500)
        
    # Update Trait Level
    @patch(path="/id/{trait_level_id:int}", sync_to_thread=True)
    def update_trait_level(
        self,
        trait_level_id: int,
        data: Annotated[TraitLevelUpdate, Body]
    ) -> TraitLevelOutput:
        try:
            trait_level = TraitLevel.get_by_id(id=trait_level_id)
            if trait_level is None:
                error = RESTAPIError(
                    error="Trait level not found",
                    error_description="The trait level with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            trait_level = trait_level.update(
                trait_level_name=data.trait_level_name,
                trait_level_info=data.trait_level_info
            )
            if trait_level is None:
                error = RESTAPIError(
                    error="An error occurred while updating trait level",
                    error_description="An error occurred while updating trait level"
                )
                return Response(content=error, status_code=500)
            return trait_level
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating trait level"
            )
            return Response(content=error_message, status_code=500)
        
    # Delete Trait Level
    @delete(path="/id/{trait_level_id:int}", sync_to_thread=True)
    def delete_trait_level(
        self, trait_level_id: int
    ) -> None:
        try:
            trait_level = TraitLevel.get_by_id(id=trait_level_id)
            if trait_level is None:
                error = RESTAPIError(
                    error="Trait level not found",
                    error_description="The trait level with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = trait_level.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Failed to delete trait level",
                    error_description="The trait level could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting trait level"
            )
            return Response(content=error_message, status_code=500)
