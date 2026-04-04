"""
This module defines the Plant class, which represents a plant entity, including its metadata, associations to populations and plots, and related operations.

It includes methods for creating, retrieving, updating, and deleting plants, as well as methods for checking existence, searching, and managing associations with populations and plots.

This module includes the following methods:

- `exists`: Check if a plant with the given parameters exists.
- `create`: Create a new plant.
- `get`: Retrieve a plant by its parameters.
- `get_by_id`: Retrieve a plant by its ID.
- `get_all`: Retrieve all plants.
- `search`: Search for plants based on various criteria.
- `update`: Update the details of a plant.
- `delete`: Delete a plant.
- `refresh`: Refresh the plant's data from the database.
- `get_info`: Get the additional information of the plant.
- `set_info`: Set the additional information of the plant.
- Association methods for populations and plots.

"""

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.population import Population
from gemini.db.models.plants import PlantModel
from gemini.db.models.views.plant_view import PlantViewModel

if TYPE_CHECKING:
    from gemini.api.plot import Plot
    from gemini.api.population import Population

logger = logging.getLogger(__name__)

class Plant(APIBase):
    """
    Represents a plant entity, including its metadata, associations to populations and plots, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the plant.
        plant_number (int): The number of the plant within the plot.
        plant_info (Optional[dict]): Additional information about the plant.
        plot_id (Optional[UUID]): The ID of the associated plot.
        population_id (Optional[UUID]): The ID of the associated population.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "plant_id"))

    plant_number: int
    plant_info: Optional[dict] = None
    plot_id: Optional[UUID] = None
    population_id: Optional[UUID] = None

    def __str__(self):
        """Return a string representation of the Plant object."""
        return f"Plant(plot_id={self.plot_id}, plant_number={self.plant_number}, plant_info={self.plant_info}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the Plant object."""
        return f"Plant(plot_id={self.plot_id}, plant_number={self.plant_number}, plant_info={self.plant_info}, id={self.id})"

    @classmethod
    def exists(
        cls,
        plant_number: int,
        population_accession: str = None,
        population_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
    ) -> bool:
        """
        Check if a plant with the given parameters exists.

        Examples:
            >>> Plant.exists(plant_number=1)
            True
            >>> Plant.exists(plant_number=1, population_accession="AC123")
            True
            >>> Plant.exists(plant_number=1, plot_number=2, plot_row_number=3, plot_column_number=4)
            False

        Args:
            plant_number (int): The number of the plant within the plot.
            population_accession (str, optional): The accession of the population. Defaults to None.
            population_name (str, optional): The population of the population. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            bool: True if the plant exists, False otherwise.
        """
        try:
            exists = PlantViewModel.exists(
                plant_number=plant_number,
                population_accession=population_accession,
                population_name=population_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of plant: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        plant_number: int,
        plant_info: dict = None,
        population_accession: str = None,
        population_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> "Plant":
        """
        Create a new plant and associate it with population and plot if provided.

        Examples:
            >>> plant = Plant.create(plant_number=1, plant_info={"height": 100})
            >>> plant
            Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...))

        Args:
            plant_number (int): The number of the plant within the plot.
            plant_info (dict, optional): Additional information about the plant. Defaults to None.
            population_accession (str, optional): The accession of the population. Defaults to None.
            population_name (str, optional): The population of the population. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Plant: The created plant instance, or None if an error occurred.
        """
        try:
            db_instance = PlantModel.get_or_create(
                plant_number=plant_number,
                plant_info=plant_info
            )
            plant = cls.model_validate(db_instance)
            if all([population_accession, population_name]):
                plant.associate_population(
                    population_accession=population_accession,
                    population_name=population_name
                )
            if all([plot_number, plot_row_number, plot_column_number, experiment_name, season_name, site_name]):
                plant.associate_plot(
                    plot_number=plot_number,
                    plot_row_number=plot_row_number,
                    plot_column_number=plot_column_number,
                    experiment_name=experiment_name,
                    season_name=season_name,
                    site_name=site_name
                )
            return plant
        except Exception as e:
            logger.error(f"Error creating plant: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        plant_number: int,
        population_accession: str = None,
        population_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> Optional["Plant"]:
        """
        Retrieve a plant by its parameters.

        Examples:
            >>> plant = Plant.get(plant_number=1)
            >>> plant
            Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...))

        Args:
            plant_number (int): The number of the plant within the plot.
            population_accession (str, optional): The accession of the population. Defaults to None.
            population_name (str, optional): The population of the population. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            Optional[Plant]: The plant instance, or None if not found.
        """
        try:
            db_instance = PlantViewModel.get_by_parameters(
                plant_number=plant_number,
                population_accession=population_accession,
                population_name=population_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            if not db_instance:
                logger.debug(f"Plant with number {plant_number} not found.")
                return None
            plant = cls.model_validate(db_instance) if db_instance else None
            return plant
        except Exception as e:
            logger.error(f"Error getting plant: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Plant"]:
        """
        Retrieve a plant by its ID.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> plant
            Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the plant.
        Returns:
            Optional[Plant]: The plant instance, or None if not found.
        """
        try:
            db_instance = PlantModel.get(id)
            if not db_instance:
                logger.warning(f"Plant with ID {id} does not exist.")
                return None
            plant = cls.model_validate(db_instance) if db_instance else None
            return plant
        except Exception as e:
            logger.error(f"Error getting plant by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Plant"]]:
        """
        Retrieve all plants.

        Examples:
            >>> plants = Plant.get_all()
            >>> plants
            [Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...)), ...]

        Returns:
            Optional[List[Plant]]: A list of all plants, or None if not found.
        """
        try:
            plants = PlantModel.all(limit=limit, offset=offset)
            if not plants or len(plants) == 0:
                logger.info("No plants found.")
                return None
            plants = [cls.model_validate(plant) for plant in plants]
            return plants
        except Exception as e:
            logger.error(f"Error getting all plants: {e}")
            return None
        
    @classmethod
    def search(
        cls, 
        plant_number: int = None,
        population_accession: str = None,
        population_name: str = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None
    ) -> Optional[List["Plant"]]:
        """
        Search for plants based on various criteria.

        Examples:
            >>> plants = Plant.search(plant_number=1)
            >>> plants
            [Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...)), ...]

        Args:
            plant_number (int, optional): The number of the plant within the plot. Defaults to None.
            population_accession (str, optional): The accession of the population. Defaults to None.
            population_name (str, optional): The population of the population. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The plot row number. Defaults to None.
            plot_column_number (int, optional): The plot column number. Defaults to None.
        Returns:
            Optional[List[Plant]]: A list of matching plants, or None if not found.
        """
        try:
            if not any([plant_number, population_accession, population_name, experiment_name, season_name, site_name, plot_number, plot_row_number, plot_column_number]):
                logger.warning("At least one search parameter must be provided.")
                return None
            plants = PlantViewModel.search(
                plant_number=plant_number,
                population_accession=population_accession,
                population_name=population_name,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number
            )
            if not plants or len(plants) == 0:
                logger.info("No plants found with the provided search parameters.")
                return None
            plants = [cls.model_validate(plant) for plant in plants]
            return plants
        except Exception as e:
            logger.error(f"Error searching for plants: {e}")
            return None
        
    def update(
        self,
        plant_number: int = None,
        plant_info: dict = None
    ) -> Optional["Plant"]:
        """
        Update the details of the plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> updated_plant = plant.update(plant_number=2, plant_info={"height": 150})
            >>> updated_plant
            Plant(plot_id=UUID(...), plant_number=2, plant_info={'height': 150}, id=UUID(...))

        Args:
            plant_number (int, optional): The new plant number. Defaults to None.
            plant_info (dict, optional): The new plant information. Defaults to None.
        Returns:
            Optional[Plant]: The updated plant instance, or None if an error occurred.
        """
        try:
            if not plant_info and not plant_number:
                logger.warning("At least one parameter must be provided for update.")
                return None
            current_id = self.id
            plant = PlantModel.get(current_id)
            if not plant:
                logger.warning(f"Plant with ID {current_id} does not exist.")
                return None
            plant = PlantModel.update(
                plant,
                plant_number=plant_number,
                plant_info=plant_info
            )
            plant = self.model_validate(plant)
            self.refresh()  # Update the current instance
            return plant
        except Exception as e:
            logger.error(f"Error updating plant: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> deleted = plant.delete()
            >>> deleted
            True

        Returns:
            bool: True if the plant was deleted, False otherwise.
        """
        try:
            current_id = self.id
            plant = PlantModel.get(current_id)
            if not plant:
                logger.warning(f"Plant with ID {current_id} does not exist.")
                return False
            PlantModel.delete(plant)
            return True
        except Exception as e:
            logger.error(f"Error deleting plant: {e}")
            return False

    def refresh(self) -> Optional["Plant"]:
        """
        Refresh the plant's data from the database.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> refreshed_plant = plant.refresh()
            >>> refreshed_plant
            Plant(plot_id=UUID(...), plant_number=1, plant_info={'height': 100}, id=UUID(...))

        Returns:
            Optional[Plant]: The refreshed plant instance, or None if an error occurred.
        """
        try:
            db_instance = PlantModel.get(self.id)
            if not db_instance:
                logger.warning(f"Plant with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing plant: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> plant_info = plant.get_info()
            >>> plant_info
            {'height': 100, 'width': 50}

        Returns:
            Optional[dict]: The plant's info, or None if not found.
        """
        try:
            current_id = self.id
            plant = PlantModel.get(current_id)
            if not plant:
                logger.warning(f"Plant with ID {current_id} does not exist.")
                return None
            plant_info = plant.plant_info
            if not plant_info:
                logger.info("Plant info is empty.")
                return None
            return plant_info
        except Exception as e:
            logger.error(f"Error getting plant info: {e}")
            return None
        
    def set_info(self, plant_info: dict) -> Optional["Plant"]:
        """
        Set the additional information of the plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> updated_plant = plant.set_info({"height": 150, "width": 75})
            >>> updated_plant.get_info()
            {'height': 150, 'width': 75}

        Args:
            plant_info (dict): The new information to set.
        Returns:
            Optional[Plant]: The updated plant instance, or None if an error occurred.
        """
        try:
            current_id = self.id
            plant = PlantModel.get(current_id)
            if not plant:
                logger.warning(f"Plant with ID {current_id} does not exist.")
                return None
            plant = PlantModel.update(
                plant,
                plant_info=plant_info
            )
            plant = self.model_validate(plant)
            self.refresh()  # Update the current instance
            return plant
        except Exception as e:
            logger.error(f"Error setting plant info: {e}")
            return None
    
    def get_associated_population(self) -> Optional["Population"]:
        """
        Get the population associated with this plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> population = plant.get_associated_population()
            >>> population
            Population(id=UUID(...), population_accession='AC123', population_name='Population1')

        Returns:
            Optional[Population]: The associated population, or None if not found.
        """
        try:
            from gemini.api.population import Population
            if not self.population_id:
                logger.info("No population assigned to this plant.")
                return None
            population = Population.get_by_id(self.population_id)
            if not population:
                logger.warning(f"Population with ID {self.population_id} does not exist.")
                return None
            return population
        except Exception as e:
            logger.error(f"Error getting population: {e}")
            return None

    def associate_population(
        self,
        population_accession: str,
        population_name: str
    ) -> Optional["Population"]:
        """
        Associate this plant with a population.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> population = plant.associate_population(population_accession="AC123", population_name="Population1")
            >>> population
            Population(id=UUID(...), population_accession='AC123', population_name='Population1')

        Args:
            population_accession (str): The accession of the population.
            population_name (str): The population of the population.
        Returns:
            Optional[Population]: The associated population, or None if an error occurred.
        """
        try:
            from gemini.api.population import Population
            population = Population.get(
                population_accession=population_accession,
                population_name=population_name
            )
            if not population:
                logger.debug(f"Population with accession {population_accession} and population {population_name} not found.")
                return None
            existing_association = PlantModel.exists(
                id=self.id,
                population_id=population.id
            )
            if existing_association:
                logger.info(f"Plant with ID {self.id} already has population {population.id} assigned.")
                return None
            db_plant = PlantModel.get(self.id)
            db_plant = PlantModel.update_parameter(
                db_plant,
                "population_id",
                population.id
            )
            logger.info(f"Assigned population {population.id} to plant {self.id}.")
            self.refresh()
            return population
        except Exception as e:
            logger.error(f"Error assigning population: {e}")
            return None

    def belongs_to_population(
        self,
        population_accession: str = None,
        population_name: str = None
    ) -> bool:
        """
        Check if this plant is associated with a specific population.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> is_associated = plant.belongs_to_population(population_accession="AC123", population_name="Population1")
            >>> is_associated
            True

        Args:
            population_accession (str, optional): The accession of the population. Defaults to None.
            population_name (str, optional): The population of the population. Defaults to None.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.population import Population
            population = Population.get(
                population_accession=population_accession,
                population_name=population_name
            )
            if not population:
                logger.debug("Population not found.")
                return False
            association_exists = PlantModel.exists(
                id=self.id,
                population_id=population.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking population assignment: {e}")
            return False

    def unassociate_population(self) -> Optional["Population"]:
        """
        Unassociate this plant from its population.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> population = plant.unassociate_population()
            >>> population
            Population(id=UUID(...), population_accession='AC123', population_name='Population1')

        Returns:
            Optional[Population]: The unassociated population, or None if an error occurred.
        """
        try:
            from gemini.api.population import Population
            if not self.population_id:
                logger.info("No population assigned to this plant.")
                return False
            population = Population.get_by_id(self.population_id)
            db_plant = PlantModel.get(self.id)
            db_plant = PlantModel.update_parameter(
                db_plant,
                "population_id",
                None
            )
            self.refresh()  # Update the current instance
            return population
        except Exception as e:
            logger.error(f"Error unassigning population: {e}")
            return False

    def get_associated_plot(self) -> Optional["Plot"]:
        """
        Get the plot associated with this plant.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> plot = plant.get_associated_plot()
            >>> plot
            Plot(id=UUID(...), plot_number=1, plot_row_number=2, plot_column_number=3)

        Returns:
            Optional[Plot]: The associated plot, or None if not found.
        """
        try:
            from gemini.api.plot import Plot
            if not self.plot_id:
                logger.info("No plot assigned to this plant.")
                return None
            plot = Plot.get_by_id(self.plot_id)
            if not plot:
                logger.warning(f"Plot with ID {self.plot_id} does not exist.")
                return None
            return plot
        except Exception as e:
            logger.error(f"Error getting plot: {e}")
            return None

    def associate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
    ) -> Optional["Plot"]:
        """
        Associate this plant with a plot.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> plot = plant.associate_plot(plot_number=1, plot_row_number=2, plot_column_number=3, experiment_name="Experiment1", season_name="Season1", site_name="Site1")
            >>> plot
            Plot(id=UUID(...), plot_number=1, plot_row_number=2, plot_column_number=3)

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The plot row number.
            plot_column_number (int): The plot column number.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Optional[Plot]: The associated plot, or None if an error occurred.
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
                logger.debug("Plot not found.")
                return None
            existing_association = PlantModel.get_by_parameters(
                id=self.id,
                plot_id=plot.id
            )
            if existing_association:
                logger.info(f"Plant with ID {self.id} already has plot {plot.id} assigned.")
                return None
            db_plant = PlantModel.get(self.id)
            db_plant = PlantModel.update_parameter(
                db_plant,
                "plot_id",
                plot.id
            )
            self.refresh()  # Update the current instance
            return plot
        except Exception as e:
            logger.error(f"Error assigning plot: {e}")
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
        Check if this plant is associated with a specific plot.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> is_associated = plant.belongs_to_plot(plot_number=1, plot_row_number=2, plot_column_number=3, experiment_name="Experiment1", season_name="Season1", site_name="Site1")
            >>> is_associated
            True

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The plot row number.
            plot_column_number (int): The plot column number.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            bool: True if associated, False otherwise.
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
                logger.debug("Plot not found.")
                return False
            association_exists = PlantModel.exists(
                id=self.id,
                plot_id=plot.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking plot assignment: {e}")
            return False

    def unassociate_plot(self) -> Optional["Plot"]:
        """
        Unassociate this plant from its plot.

        Examples:
            >>> plant = Plant.get_by_id(UUID('...'))
            >>> plot = plant.unassociate_plot()
            >>> plot
            Plot(id=UUID(...), plot_number=1, plot_row_number=2, plot_column_number=3)

        Returns:
            Optional[Plot]: The unassociated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            if not self.plot_id:
                logger.info("No plot assigned to this plant.")
                return None
            # Assuming we want to unassign the plot by setting plot_id to None
            plot = Plot.get_by_id(self.plot_id)
            db_plant = PlantModel.get(self.id)
            db_plant = PlantModel.update_parameter(
                db_plant,
                "plot_id",
                None
            )
            self.refresh()  # Update the current instance
            return plot
        except Exception as e:
            logger.error(f"Error unassigning plot: {e}")
            return None
