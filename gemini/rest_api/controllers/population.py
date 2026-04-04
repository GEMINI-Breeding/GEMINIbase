from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.population import Population
from gemini.rest_api.models import (
    PopulationInput,
    PopulationOutput,
    PopulationUpdate,
    ExperimentOutput,
    PlotOutput,
    PlantOutput,
    RESTAPIError,
    str_to_dict,
    JSONB
)

from typing import List, Annotated, Optional

class PopulationController(Controller):

    # Get All Populations
    @get(path="/all", sync_to_thread=True)
    def get_all_populations(self, limit: int = 100, offset: int = 0) -> List[PopulationOutput]:
        try:
            populations = Population.get_all(limit=limit, offset=offset)
            if populations is None:
                error = RESTAPIError(
                    error="No populations found in the database",
                    error_description="There are no populations available in the database"
                )
                return Response(content=error, status_code=404)
            return populations
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all populations"
            )
            return Response(content=error, status_code=500)

    # Get Populations
    @get(sync_to_thread=True)
    def get_populations(
        self,
        population_name: Optional[str] = None,
        population_accession: Optional[str] = None,
        population_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[PopulationOutput]:
        try:
            if population_info is not None:
                population_info = str_to_dict(population_info)

            populations = Population.search(
                population_name=population_name,
                population_accession=population_accession,
                population_info=population_info,
                experiment_name=experiment_name
            )
            if populations is None:
                error= RESTAPIError(
                    error="No populations found",
                    error_description="No populations were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return populations
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving populations"
            )
            return Response(content=error_message, status_code=500)
        
        
    # Get Population by ID
    @get(path="/id/{population_id:str}", sync_to_thread=True)
    def get_population_by_id(
        self, population_id: str
    ) -> PopulationOutput:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return population
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the population"
            )
            return Response(content=error, status_code=500)
        
    # Create a new Population
    @post(sync_to_thread=True)
    def create_population(
        self, data: Annotated[PopulationInput, Body]
    ) -> PopulationOutput:
        try:
            population = Population.create(
                population_name=data.population_name,
                population_accession=data.population_accession,
                population_info=data.population_info,
                experiment_name=data.experiment_name
            )
            if population is None:
                error = RESTAPIError(
                    error="Population creation failed",
                    error_description="The population could not be created"
                )
                return Response(content=error, status_code=500)
            return population
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the population"
            )
            return Response(content=error, status_code=500)
        
    # Update Existing Population
    @patch(path="/id/{population_id:str}", sync_to_thread=True)
    def update_population(
        self, population_id: str, data: Annotated[PopulationUpdate, Body]
    ) -> PopulationOutput:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            population = population.update(
                population_name=data.population_name,
                population_accession=data.population_accession,
                population_info=data.population_info,
            )
            if population is None:
                error = RESTAPIError(
                    error="Population update failed",
                    error_description="The population could not be updated"
                )
                return Response(content=error, status_code=500)
            return population
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the population"
            )
            return Response(content=error, status_code=500)
        
    # Delete Population
    @delete(path="/id/{population_id:str}", sync_to_thread=True)
    def delete_population(
        self, population_id: str
    ) -> None:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error_html = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                ).to_html()
                return Response(content=error_html, status_code=404)
            is_deleted = population.delete()
            if not is_deleted:
                error_message = RESTAPIError(
                    error="Population deletion failed",
                    error_description="The population could not be deleted"
                )
                return Response(content=error_message, status_code=500)
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the population"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Associated Experiments
    @get(path="/id/{population_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(
        self, population_id: str
    ) -> List[ExperimentOutput]:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiments = population.get_associated_experiments()
            if not experiments:
                error = RESTAPIError(
                    error="No associated experiments found",
                    error_description="The population has no associated experiments"
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
    @get(path="/id/{population_id:str}/plots", sync_to_thread=True)
    def get_associated_plots(
        self, population_id: str
    ) -> List[PlotOutput]:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plots = population.get_associated_plots()
            if not plots:
                error = RESTAPIError(
                    error="No associated plots found",
                    error_description="The population has no associated plots"
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
    @get(path="/id/{population_id:str}/plants", sync_to_thread=True)
    def get_associated_plants(
        self, population_id: str
    ) -> List[PlantOutput]:
        try:
            population = Population.get_by_id(id=population_id)
            if population is None:
                error = RESTAPIError(
                    error="Population not found",
                    error_description="The population with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plants = population.get_associated_plants()
            if not plants:
                error = RESTAPIError(
                    error="No associated plants found",
                    error_description="The population has no associated plants"
                )
                return Response(content=error, status_code=404)
            return plants
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated plants"
            )
            return Response(content=error, status_code=500)
