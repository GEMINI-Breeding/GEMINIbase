from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from pydantic import BaseModel

from gemini.api.plant import Plant
from gemini.rest_api.models import PlantInput, PlantOutput, PlantUpdate, RESTAPIError, JSONB, str_to_dict
from gemini.rest_api.models import CultivarOutput, PlotOutput 
from typing import List, Annotated, Optional

class PlantCultivarInput(BaseModel):
    cultivar_accession: str
    cultivar_population: str


class PlantController(Controller):

    # Get All Plants
    @get(path="/all", sync_to_thread=True)
    def get_all_plants(self, limit: int = 100, offset: int = 0) -> List[PlantOutput]:
        try:
            plants = Plant.get_all(limit=limit, offset=offset)
            if plants is None:
                error = RESTAPIError(
                    error="No plants found",
                    error_description="No plants were found"
                )
                return Response(content=error, status_code=404)
            return plants
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all plants"
            )
            return Response(content=error, status_code=500)

    # Get all Plants
    @get(sync_to_thread=True)
    def get_plants(
        self,
        plant_number: Optional[int] = None,
        plot_number: Optional[int] = None,
        plot_row_number: Optional[int] = None,
        plot_column_number: Optional[int] = None,
        cultivar_accession: Optional[str] = None,
        cultivar_population: Optional[str] = None,
        experiment_name: Optional[str] = None,
        season_name: Optional[str] = None,
        site_name: Optional[str] = None,
        plant_info: Optional[JSONB] = None
    ) -> List[PlantOutput]:
        try:
            if plant_info is not None:
                plant_info = str_to_dict(plant_info)

            plants = Plant.search(
                plant_number=plant_number,
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
            )

            if plants is None:
                error = RESTAPIError(
                    error="No plants found",
                    error_description="No plants were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return plants
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving plants"
            )
            return Response(content=error, status_code=500)
        
    # Get Plant by ID
    @get(path="/id/{plant_id:str}", sync_to_thread=True)
    def get_plant_by_id(
            self, plant_id: str
    ) -> PlantOutput:
        try:
            plant = Plant.get_by_id(id=plant_id)
            if plant is None:
                error = RESTAPIError(
                    error="Plant not found",
                    error_description="The plant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return plant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the plant"
            )
            return Response(content=error, status_code=500)
        
    # Create a new Plant
    @post(sync_to_thread=True)
    def create_plant(
        self,
        data: Annotated[PlantInput, Body]
    ) -> PlantOutput:
        try:
            if data.plant_info is not None:
                data.plant_info = str_to_dict(data.plant_info)

            plant = Plant.create(
                plant_number=data.plant_number,
                plant_info=data.plant_info,
                cultivar_accession=data.cultivar_accession,
                cultivar_population=data.cultivar_population,
                experiment_name=data.experiment_name,
                season_name=data.season_name,
                site_name=data.site_name,
                plot_number=data.plot_number,
                plot_row_number=data.plot_row_number,
                plot_column_number=data.plot_column_number
            )
            if plant is None:
                error = RESTAPIError(
                    error="Plant not created",
                    error_description="The plant could not be created"
                )
                return Response(content=error, status_code=500)
            return plant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the plant"
            )
            return Response(content=error, status_code=500)
        
    # Update a Plant
    @patch(path="/id/{plant_id:str}", sync_to_thread=True)
    def update_plant(
        self,
        plant_id: str,
        data: Annotated[PlantUpdate, Body]
    ) -> PlantOutput:
        try:
            plant = Plant.get_by_id(id=plant_id)
            if plant is None:
                error = RESTAPIError(
                    error="Plant not found",
                    error_description="The plant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plant = plant.update(
                plant_number=data.plant_number,
                plant_info=data.plant_info,
            )
            if plant is None:
                error = RESTAPIError(
                    error="Plant not updated",
                    error_description="The plant could not be updated"
                )
                return Response(content=error, status_code=500)
            return plant
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the plant"
            )
            return Response(content=error, status_code=500)
        
    # Delete a Plant
    @delete(path="/id/{plant_id:str}", sync_to_thread=True)
    def delete_plant(
        self,
        plant_id: str
    ) -> None:
        try:
            plant = Plant.get_by_id(id=plant_id)
            if plant is None:
                error = RESTAPIError(
                    error="Plant not found",
                    error_description="The plant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = plant.delete()
            if not is_deleted:
                error_html = RESTAPIError(
                    error="Failed to delete plant",
                    error_description="The plant could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the plant"
            )
            return Response(content=error, status_code=500)
        
    # Get Plant Cultivar
    @get(path="/id/{plant_id:str}/cultivar", sync_to_thread=True)
    def get_plant_cultivar(
        self,
        plant_id: str
    ) -> CultivarOutput:
        try:
            plant = Plant.get_by_id(id=plant_id)
            if plant is None:
                error = RESTAPIError(
                    error="Plant not found",
                    error_description="The plant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            cultivar = plant.get_associated_cultivar()
            if cultivar is None:
                error = RESTAPIError(
                    error="Cultivar not found",
                    error_description="The cultivar for the given plant was not found"
                )
                return Response(content=error, status_code=404)
            return cultivar
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the cultivar"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Plots
    @get(path="/id/{plant_id:str}/plot", sync_to_thread=True)
    def get_associated_plot(
        self,
        plant_id: str
    ) -> List[PlotOutput]:
        try:
            plant = Plant.get_by_id(id=plant_id)
            if plant is None:
                error = RESTAPIError(
                    error="Plant not found",
                    error_description="The plant with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plots = plant.get_associated_plot()
            if plots is None:
                error = RESTAPIError(
                    error="No plots found",
                    error_description="No plots were found associated with the given plant"
                )
                return Response(content=error, status_code=404)
            return plots
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the associated plots"
            )
            return Response(content=error, status_code=500)



