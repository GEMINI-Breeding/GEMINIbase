from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.season import Season
from gemini.rest_api.models import ( 
    SeasonInput, 
    SeasonOutput, 
    SeasonUpdate,
    ExperimentOutput, 
    RESTAPIError, 
    JSONB, 
    str_to_dict
)

from typing import List, Annotated, Optional

class SeasonController(Controller):

    # Get All Seasons
    @get(path="/all", sync_to_thread=True)
    def get_all_seasons(self, limit: int = 100, offset: int = 0) -> List[SeasonOutput]:
        try:
            seasons = Season.get_all(limit=limit, offset=offset)
            if seasons is None:
                error = RESTAPIError(
                    error="No seasons found",
                    error_description="No seasons were found"
                )
                return Response(content=error, status_code=404)
            return seasons
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all seasons"
            )
            return Response(content=error, status_code=500)

    # Get Seasons
    @get(sync_to_thread=True)
    def get_seasons(
        self,
        season_name: Optional[str] = None,
        season_info: Optional[JSONB] = None,
        season_start_date: Optional[str] = None,
        season_end_date: Optional[str] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[SeasonOutput]:
        try:
            if season_info is not None:
                season_info = str_to_dict(season_info)

            seasons = Season.search(
                season_name=season_name,
                season_info=season_info,
                season_start_date=season_start_date,
                season_end_date=season_end_date,
                experiment_name=experiment_name,
            )
            if seasons is None:
                error = RESTAPIError(
                    error="No seasons found",
                    error_description="No seasons were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return seasons
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving seasons"
            )
            return Response(content=error, status_code=500)
        
    # Get Season by ID
    @get(path="/id/{season_id:str}", sync_to_thread=True)
    def get_season_by_id(
        self, season_id: str
    ) -> SeasonOutput:
        try:
            season = Season.get_by_id(id=season_id)
            if season is None:
                error = RESTAPIError(
                    error="Season not found",
                    error_description="The season with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return season
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the season"
            )
            return Response(content=error, status_code=500)
        
    # Create Season
    @post(sync_to_thread=True)
    def create_season(
        self,
        data: Annotated[SeasonInput, Body]
    ) -> SeasonOutput:
        try:
            season = Season.create(
                season_name=data.season_name,
                season_info=data.season_info,
                season_start_date=data.season_start_date,
                season_end_date=data.season_end_date,
                experiment_name=data.experiment_name,
            )
            if season is None:
                error = RESTAPIError(
                    error="Season not created",
                    error_description="The season could not be created"
                )
                return Response(content=error, status_code=500)
            return season
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the season"
            )
            return Response(content=error, status_code=500)

    # Update Season
    @patch(path="/id/{season_id:str}", sync_to_thread=True)
    def update_season(
        self,
        season_id: str,
        data: Annotated[SeasonUpdate, Body]
    ) -> SeasonOutput:
        try:
            season_obj = Season.get_by_id(id=season_id) # Renamed to avoid conflict
            if season_obj is None:
                error = RESTAPIError(
                    error="Season not found",
                    error_description="The season with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            
            updated_season = season_obj.update( # Use a different variable for the result of update
                season_name=data.season_name,
                season_info=data.season_info,
                season_start_date=data.season_start_date,
                season_end_date=data.season_end_date
            )
            if updated_season is None:
                error = RESTAPIError(
                    error="Season not updated",
                    error_description="The season could not be updated"
                )
                return Response(content=error, status_code=500)
            return updated_season
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the season"
            )
            return Response(content=error, status_code=500)
        
    # Delete Season
    @delete(path="/id/{season_id:str}", sync_to_thread=True)
    def delete_season(
        self, season_id: str
    ) -> None:
        try:
            season = Season.get_by_id(id=season_id)
            if season is None:
                error = RESTAPIError(
                    error="Season not found",
                    error_description="The season with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = season.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Season not deleted",
                    error_description="The season could not be deleted"
                )
                return Response(content=error, status_code=500)
            # Successful deletion implies a 204 No Content or similar, 
            # so no explicit return is needed if the framework handles it.
            # If a specific Response is needed for success, it would be added here.
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the season"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Experiment
    @get(path="/id/{season_id:str}/experiment", sync_to_thread=True)
    def get_associated_experiment(
        self, season_id: str
    ) -> ExperimentOutput:
        try:
            season = Season.get_by_id(id=season_id)
            if season is None:
                error = RESTAPIError(
                    error="Season not found",
                    error_description="The season with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiment = season.get_associated_experiment()
            if experiment is None:
                error = RESTAPIError(
                    error="Experiment not found",
                    error_description="The associated experiment was not found"
                )
                return Response(content=error, status_code=404)
            return experiment
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the associated experiment"
            )
            return Response(content=error, status_code=500)
        

    
