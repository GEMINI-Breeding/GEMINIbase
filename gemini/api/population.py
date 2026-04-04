"""

This module defines the Population class, which represents a population in the Gemini API.

It provides methods to create, retrieve, update, delete, and manage populations,
as well as to associate them with experiments, plots, and plants.

The module includes the following methods:

- `exists`: Check if a population exists by population and accession.
- `create`: Create a new population with optional experiment association.
- `get`: Retrieve a population by population, accession, and optional experiment name.
- `get_by_id`: Retrieve a population by its ID.
- `get_all`: Retrieve all populations.
- `search`: Search for populations based on various criteria.
- `update`: Update the details of a population.
- `delete`: Delete a population. 
- `refresh`: Refresh the population's data from the database.
- `get_info`: Get additional information about the population.
- `set_info`: Set additional information for the population.
- `get_associated_experiments`: Get all experiments associated with the population.
- `associate_experiment`: Associate the population with an experiment.
- `unassociate_experiment`: Unassociate the population from an experiment.
- `belongs_to_experiment`: Check if the population belongs to a specific experiment.
- `get_associated_plots`: Get all plots associated with the population.
- `associate_plot`: Associate the population with a plot.
- `unassociate_plot`: Unassociate the population from a plot.
- `belongs_to_plot`: Check if the population belongs to a specific plot.
- `get_associated_plants`: Get all plants associated with the population.
- `belongs_to_plant`: Check if the population belongs to a specific plant.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.populations import PopulationModel
from gemini.db.models.associations import ExperimentPopulationModel, PlotPopulationModel
from gemini.db.models.views.experiment_views import ExperimentPopulationsViewModel
from gemini.db.models.views.plot_population_view import PlotPopulationViewModel
from gemini.db.models.views.plant_view import PlantViewModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.plot import Plot
    from gemini.api.plant import Plant

logger = logging.getLogger(__name__)

class Population(APIBase):
    """
    Represents a population, a specific variety of a plant species.

    Attributes:
        id (Optional[ID]): The unique identifier of the population.
        population_name (str): The population of the population.
        population_accession (Optional[str]): The accession number of the population.
        population_info (Optional[dict]): Additional information about the population.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "population_id"))

    population_name: str
    population_accession: Optional[str] = None
    population_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Population object."""
        return f"Population(population_name={self.population_name}, population_accession={self.population_accession}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the Population object."""
        return f"Population(population_name={self.population_name}, population_accession={self.population_accession}, id={self.id})"

    @classmethod
    def exists(
        cls,
        population_name: str,
        population_accession: str,
    ) -> bool:
        """
        Check if a population with the given population and accession exists.

        Examples:
            >>> Population.exists("Wheat", "Accession123")
            True

            >>> Population.exists("Corn", "Accession456")
            False

        Args:
            population_name (str): The population of the population.
            population_accession (str): The accession number of the population.

        Returns:
            bool: True if the population exists, False otherwise.
        """
        try:
            exists = PopulationModel.exists(
                population_name=population_name,
                population_accession=population_accession,
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking the existence of population: {e}")
            return False

    @classmethod
    def create(
        cls,
        population_name: str,
        population_accession: str,
        population_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Population"]:
        """
        Create a new population. If the population already exists, it will return the existing one.

        Examples:
            >>> population = Population.create("Wheat", "Accession123")
            >>> print(population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))

            >>> population = Population.create("Corn", "Accession456", {"info": "test"}, "Experiment1")
            >>> print(population)
            Population(population_name=Corn, population_accession=Accession456, id=UUID(...))

        Args:
            population_name (str): The population of the population.
            population_accession (str): The accession number of the population.
            population_info (dict, optional): Additional information about the population. Defaults to {}.
            experiment_name (str, optional): The name of the experiment to associate the population with. Defaults to None.

        Returns:
            Optional["Population"]: The created population, or None if an error occurred.
        """
        try:
            db_instance = PopulationModel.get_or_create(
                population_name=population_name,
                population_accession=population_accession,
                population_info=population_info,
            )
            population = cls.model_validate(db_instance)
            # Associate with experiment if provided
            if experiment_name:
                population.associate_experiment(experiment_name)
            return population
        except Exception as e:
            logger.error(f"Error creating population: {e}")
            return None
        
    @classmethod
    def get(cls, population_name: str, population_accession: str, experiment_name: str = None) -> Optional["Population"]:
        """
        Get a population by its population, accession, and optionally, experiment name.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> print(population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))

            >>> population = Population.get("Corn", "Accession456", "Experiment1")
            >>> print(population)
            Population(population_name=Corn, population_accession=Accession456, id=UUID(...))

        Args:
            population_name (str): The population of the population.
            population_accession (str): The accession number of the population.
            experiment_name (str, optional): The name of the experiment. Defaults to None.

        Returns:
            Optional["Population"]: The population, or None if not found.
        """
        try:
            db_instance = ExperimentPopulationsViewModel.get_by_parameters(
                population_accession=population_accession,
                population_name=population_name,
                experiment_name=experiment_name,
            )
            if not db_instance:
                logger.debug(f"Population with accession {population_accession} and population {population_name} not found.")
                return None
            population = cls.model_validate(db_instance)
            return population
        except Exception as e:
            logger.error(f"Error getting population: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Population"]:
        """
        Get a population by its ID.

        Examples:
            >>> population = Population.get_by_id(UUID(...))
            >>> print(population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the population.

        Returns:
            Optional["Population"]: The population, or None if not found.
        """
        try:
            db_instance = PopulationModel.get(id)
            if not db_instance:
                logger.warning(f"Population with ID {id} does not exist.")
                return None
            population = cls.model_validate(db_instance)
            return population
        except Exception as e:
            logger.error(f"Error getting population by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Population"]]:
        """
        Get all populations.

        Examples:
            >>> populations = Population.get_all()
            >>> for population in populations:
            ...     print(population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))
            Population(population_name=Corn, population_accession=Accession456, id=UUID(...))


        Returns:
            Optional[List["Population"]]: A list of all populations, or None if an error occurred.
        """
        try:
            populations = PopulationModel.all(limit=limit, offset=offset)
            if not populations or len(populations) == 0:
                logger.info("No populations found.")
                return None
            populations = [cls.model_validate(population) for population in populations]
            return populations
        except Exception as e:
            logger.error(f"Error getting all populations: {e}")
            return None
        
    @classmethod
    def search(
        cls, 
        population_name: str = None,
        population_accession: str = None,
        population_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Population"]]:
        """
        Search for populations based on various criteria.

        Examples:
            >>> populations = Population.search(population_name="Wheat")
            >>> for population in populations:
            ...     print(population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))
            Population(population_name=Wheat, population_accession=Accession456, id=UUID(...))

        Args:
            population_name (str, optional): The population of the population. Defaults to None.
            population_accession (str, optional): The accession number of the population. Defaults to None.
            population_info (dict, optional): Additional information about the population. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.

        Returns:
            Optional[List["Population"]]: A list of matching populations, or None if an error occurred.
        """
        try:
            if not any([experiment_name, population_name, population_accession, population_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            populations = ExperimentPopulationsViewModel.search(
                experiment_name=experiment_name,
                population_name=population_name,
                population_accession=population_accession,
                population_info=population_info,
            )
            if not populations or len(populations) == 0:
                logger.info("No populations found with the provided search parameters.")
                return None
            populations = [cls.model_validate(population) for population in populations]
            return populations
        except Exception as e:
            logger.error(f"Error searching populations: {e}")
            return None
        
    def update(
        self,
        population_accession: str = None,
        population_name: str = None,
        population_info: dict = None,
    ) -> Optional["Population"]:
        """
        Update the details of the population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> updated_population = population.update(population_accession="NewAccession")
            >>> print(updated_population)
            Population(population_name=Wheat, population_accession=NewAccession, id=UUID(...))
            

        Args:
            population_accession (str, optional): The new accession number. Defaults to None.
            population_name (str, optional): The new population. Defaults to None.
            population_info (dict, optional): The new information. Defaults to None.

        Returns:
            Optional["Population"]: The updated population, or None if an error occurred.
        """
        try:
            if not any([population_accession, population_name, population_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            
            current_id = self.id
            population = PopulationModel.get(current_id)
            if not population:
                logger.warning(f"Population with ID {current_id} does not exist.")
                return None
            population = PopulationModel.update(
                population,
                population_accession=population_accession,
                population_name=population_name,
                population_info=population_info,
            )
            population = self.model_validate(population)
            self.refresh()
            return population
        except Exception as e:
            logger.error(f"Error updating population: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> success = population.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the population was deleted successfully, False otherwise.
        """
        try:
            current_id = self.id
            population = PopulationModel.get(current_id)
            if not population:
                logger.warning(f"Population with ID {current_id} does not exist.")
                return False
            PopulationModel.delete(population)
            return True
        except Exception as e:
            return False
        
    
    def refresh(self) -> Optional["Population"]:
        """
        Refresh the population's data from the database. It is rarely needed to be called by the user,
        as the data is automatically refreshed when accessed.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> refreshed_population = population.refresh()
            >>> print(refreshed_population)
            Population(population_name=Wheat, population_accession=Accession123, id=UUID(...))

        Returns:
            Optional["Population"]: The refreshed population, or None if an error occurred.
        """
        try:
            db_instance = PopulationModel.get(self.id)
            if not db_instance:
                logger.warning(f"Population with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing population: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> info = population.get_info()
            >>> print(info)
            {'key1': 'value1', 'key2': 'value2'}

        Returns:
            Optional[dict]: The population's information, or None if not found.
        """
        try:
            current_id = self.id
            population = PopulationModel.get(current_id)
            if not population:
                logger.warning(f"Population with ID {current_id} does not exist.")
                return None
            population_info = population.population_info
            if not population_info:
                logger.info("Population info is empty.")
                return None
            return population_info
        except Exception as e:
            logger.error(f"Error getting population info: {e}")
            return None
        
    def set_info(self, population_info: dict) -> Optional["Population"]:
        """
        Set the additional information of the population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> updated_population = population.set_info({"key1": "value1", "key2": "value2"})
            >>> print(updated_population.get_info())
            {'key1': 'value1', 'key2': 'value2'}

        Args:
            population_info (dict): The new information to set.

        Returns:
            Optional["Population"]: The updated population, or None if an error occurred.
        """
        try:
            current_id = self.id
            population = PopulationModel.get(current_id)
            if not population:
                logger.warning(f"Population with ID {current_id} does not exist.")
                return None
            population = PopulationModel.update(
                population,
                population_info=population_info
            )
            population = self.model_validate(population)
            self.refresh()
            return population
        except Exception as e:
            logger.error(f"Error setting population info: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with the population. Which are the experiments
        that have this population as part of their population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> experiments = population.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=Experiment1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))
        

        Returns:
            A list of associated experiments, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            current_id = self.id
            experiment_populations = ExperimentPopulationsViewModel.search(population_id=current_id)
            if not experiment_populations or len(experiment_populations) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(experiment_population) for experiment_population in experiment_populations]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate the population with an experiment. If the population is already associated with the experiment,
        it will return the experiment without creating a new association.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> experiment = population.associate_experiment("Experiment1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to associate with.

        Returns:
            The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentPopulationModel.get_by_parameters(
                experiment_id=experiment.id,
                population_id=self.id
            )
            if existing_association:
                logger.info(f"Population {self.population_name} is already associated with experiment {experiment_name}.")
                return experiment
            new_association = ExperimentPopulationModel.get_or_create(
                experiment_id=experiment.id,
                population_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate population {self.population_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating population with experiment: {e}")
            return None
        
    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate the population from an experiment. If the population is not associated with the experiment,
        it will return None without making any changes.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> experiment = population.unassociate_experiment("Experiment1")
            >>> print(experiment)
            Experiment(experiment_name=Experiment1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to unassociate from.

        Returns:
            The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentPopulationModel.get_by_parameters(
                experiment_id=experiment.id,
                population_id=self.id
            )
            if not existing_association:
                logger.info(f"Population {self.population_name} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentPopulationModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate population {self.population_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating population from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if the population belongs to a specific experiment.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> belongs = population.belongs_to_experiment("Experiment1")
            >>> print(belongs)
            True

            >>> belongs = population.belongs_to_experiment("NonExistentExperiment")
            >>> print(belongs)
            False 

        Args:
            experiment_name (str): The name of the experiment.

        Returns:
            bool: True if the population belongs to the experiment, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentPopulationModel.exists(
                experiment_id=experiment.id,
                population_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if population belongs to experiment: {e}")
            return False

    def get_associated_plots(self) -> Optional[List["Plot"]]:
        """
        Get all plots associated with the population. Which are the plots that have this population
        as part of their population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> plots = population.get_associated_plots()
            >>> for plot in plots:
            ...     print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))
            Plot(plot_number=2, plot_row_number=1, plot_column_number=2, id=UUID(...))

        Returns:
            A list of associated plots, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            current_id = self.id
            plot_populations = PlotPopulationViewModel.search(population_id=current_id)
            if not plot_populations or len(plot_populations) == 0:
                logger.info("No associated plots found.")
                return None
            plots = [Plot.model_validate(plot_population) for plot_population in plot_populations]
            return plots
        except Exception as e:
            logger.error(f"Error getting associated plots: {e}")
            return None

    def associate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> Optional["Plot"]:
        """
        Associate the population with a plot.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> plot = population.associate_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The number of the plot.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.

        Returns:
            The associated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return None
            existing_association = PlotPopulationModel.get_by_parameters(
                plot_id=plot.id,
                population_id=self.id
            )
            if existing_association:
                logger.info(f"Population {self.population_name} is already associated with plot {plot_number}.")
                return plot
            new_association = PlotPopulationModel.get_or_create(
                plot_id=plot.id,
                population_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate population {self.population_name} with plot {plot_number}.")
                return None
            self.refresh()
            return plot
        except Exception as e:
            logger.error(f"Error associating population with plot: {e}")
            return None

    def unassociate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> Optional["Plot"]:
        """
        Unassociate the population from a plot.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> plot = population.unassociate_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The number of the plot.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.

        Returns:
            The unassociated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return None
            existing_association = PlotPopulationModel.get_by_parameters(
                plot_id=plot.id,
                population_id=self.id
            )
            if not existing_association:
                logger.info(f"Population {self.population_name} is not associated with plot {plot_number}.")
                return None
            is_deleted = PlotPopulationModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate population {self.population_name} from plot {plot_number}.")
                return None
            self.refresh()
            return plot
        except Exception as e:
            logger.error(f"Error unassociating population from plot: {e}")
            return None

    def belongs_to_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> bool:
        """
        Check if the population belongs to a specific plot.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> belongs = population.belongs_to_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
            >>> print(belongs)
            True

        Args:
            plot_number (int): The number of the plot.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.

        Returns:
            bool: True if the population belongs to the plot, False otherwise.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return False
            association_exists = PlotPopulationModel.exists(
                plot_id=plot.id,
                population_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if population belongs to plot: {e}")
            return False
        
    def get_associated_plants(self) -> Optional[List["Plant"]]:
        """
        Get all plants associated with the population. Which are the plants that have this population
        as part of their population.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> plants = population.get_associated_plants()
            >>> for plant in plants:
            ...     print(plant)
            Plant(plot_id=UUID(...), plant_number=1, plant_info={...}, id=UUID(...))
            Plant(plot_id=UUID(...), plant_number=2, plant_info={...}, id=UUID(...))
           

        Returns:
            A list of associated plants, or None if an error occurred.
        """
        try:
            from gemini.api.plant import Plant
            current_id = self.id
            population_plants = PlantViewModel.search(population_id=current_id)
            if not population_plants or len(population_plants) == 0:
                logger.info("No associated plants found.")
                return None
            plants = [Plant.model_validate(population_plant) for population_plant in population_plants]
            return plants
        except Exception as e:
            logger.error(f"Error getting associated plants: {e}")
            return None


    def belongs_to_plant(
        self,
        plant_number: int,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> bool:
        """
        Check if the population belongs to a specific plant.

        Examples:
            >>> population = Population.get("Wheat", "Accession123")
            >>> belongs = population.belongs_to_plant(1, 1, 1, 1, "Experiment1", "Season1", "Site1")
            >>> print(belongs)
            True

        Args:
            plant_number (int): The number of the plant.
            plot_number (int, optional): The number of the plot. Defaults to None.
            plot_row_number (int, optional): The row number of the plot. Defaults to None.
            plot_column_number (int, optional): The column number of the plot. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.

        Returns:
            bool: True if the population belongs to the plant, False otherwise.
        """
        try:
            from gemini.api.plant import Plant
            plant = Plant.get(
                plant_number=plant_number,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not plant:
                logger.warning(f"Plant {plant_number} does not exist.")
                return False
            association_exists = PlantViewModel.exists(
                plant_id=plant.id,
                population_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if population belongs to plant: {e}")
            return False
