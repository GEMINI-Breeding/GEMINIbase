from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.cultivar import Cultivar
from gemini.rest_api.models import (
    CultivarInput,
    CultivarOutput,
    CultivarUpdate,
    ExperimentOutput,
    PlotOutput,
    PlantOutput,
    RESTAPIError,
    str_to_dict,
    JSONB
)

from typing import List, Annotated, Optional

class CultivarController(Controller):

    # Get All Cultivars
    @get(path="/all", sync_to_thread=True)
    def get_all_cultivars(self, limit: int = 100, offset: int = 0) -> List[CultivarOutput]:
        try:
            cultivars = Cultivar.get_all(limit=limit, offset=offset)
            if cultivars is None:
                error = RESTAPIError(
                    error="No cultivars found in the database",
                    error_description="There are no cultivars available in the database"
                )
                return Response(content=error, status_code=404)
            return cultivars
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all cultivars"
            )
            return Response(content=error, status_code=500)

    # Get Cultivars
    @get(sync_to_thread=True)
    def get_cultivars(
        self,
        cultivar_population: Optional[str] = None,
        cultivar_accession: Optional[str] = None,
        cultivar_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[CultivarOutput]:
        try:
            if cultivar_info is not None:
                cultivar_info = str_to_dict(cultivar_info)

            cultivars = Cultivar.search(
                cultivar_population=cultivar_population,
                cultivar_accession=cultivar_accession,
                cultivar_info=cultivar_info,
                experiment_name=experiment_name
            )
            if cultivars is None:
                error= RESTAPIError(
                    error="No cultivars found",
                    error_description="No cultivars were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return cultivars
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving cultivars"
            )
            return Response(content=error_message, status_code=500)
        
        
    # Get Cultivar by ID
    @get(path="/id/{cultivar_id:str}", sync_to_thread=True)
    def get_cultivar_by_id(
        self, cultivar_id: str
    ) -> CultivarOutput:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return cultivar
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the cultivar"
            )
            return Response(content=error, status_code=500)
        
    # Create a new Cultivar
    @post(sync_to_thread=True)
    def create_cultivar(
        self, data: Annotated[CultivarInput, Body]
    ) -> CultivarOutput:
        try:
            cultivar = Cultivar.create(
                cultivar_population=data.cultivar_population,
                cultivar_accession=data.cultivar_accession,
                cultivar_info=data.cultivar_info,
                experiment_name=data.experiment_name
            )
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar creation failed",
                    error_description="The cultivar could not be created"
                )
                return Response(content=error, status_code=500)
            return cultivar
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the cultivar"
            )
            return Response(content=error, status_code=500)
        
    # Update Existing Cultivar
    @patch(path="/id/{cultivar_id:str}", sync_to_thread=True)
    def update_cultivar(
        self, cultivar_id: str, data: Annotated[CultivarUpdate, Body]
    ) -> CultivarOutput:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            cultivar = cultivar.update(
                cultivar_population=data.cultivar_population,
                cultivar_accession=data.cultivar_accession,
                cultivar_info=data.cultivar_info,
            )
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar update failed",
                    error_description="The cultivar could not be updated"
                )
                return Response(content=error, status_code=500)
            return cultivar
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the cultivar"
            )
            return Response(content=error, status_code=500)
        
    # Delete Cultivar
    @delete(path="/id/{cultivar_id:str}", sync_to_thread=True)
    def delete_cultivar(
        self, cultivar_id: str
    ) -> None:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error_html = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                ).to_html()
                return Response(content=error_html, status_code=404)
            is_deleted = cultivar.delete()
            if not is_deleted:
                error_message = RESTAPIError(
                    error="Cultivar deletion failed",
                    error_description="The cultivar could not be deleted"
                )
                return Response(content=error_message, status_code=500)
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the cultivar"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Associated Experiments
    @get(path="/id/{cultivar_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(
        self, cultivar_id: str
    ) -> List[ExperimentOutput]:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiments = cultivar.get_associated_experiments()
            if not experiments:
                error = RESTAPIError(
                    error="No associated experiments found",
                    error_description="The cultivar has no associated experiments"
                )
                return Response(content=error, status_code=404)
            return experiments
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated experiments"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Plots
    @get(path="/id/{cultivar_id:str}/plots", sync_to_thread=True)
    def get_associated_plots(
        self, cultivar_id: str
    ) -> List[PlotOutput]:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plots = cultivar.get_associated_plots()
            if not plots:
                error = RESTAPIError(
                    error="No associated plots found",
                    error_description="The cultivar has no associated plots"
                )
                return Response(content=error, status_code=404)
            return plots
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated plots"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Plants
    @get(path="/id/{cultivar_id:str}/plants", sync_to_thread=True)
    def get_associated_plants(
        self, cultivar_id: str
    ) -> List[PlantOutput]:
        try:
            cultivar = Cultivar.get_by_id(id=cultivar_id)
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plants = cultivar.get_associated_plants()
            if not plants:
                error = RESTAPIError(
                    error="No associated plants found",
                    error_description="The cultivar has no associated plants"
                )
                return Response(content=error, status_code=404)
            return plants
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated plants"
            )
            return Response(content=error, status_code=500)
