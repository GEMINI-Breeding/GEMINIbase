"""

This module defines the Cultivar class, which represents a cultivar in the Gemini API.

It provides methods to create, retrieve, update, delete, and manage cultivars,
as well as to associate them with experiments, plots, and plants.

The module includes the following methods:

- `exists`: Check if a cultivar exists by population and accession.
- `create`: Create a new cultivar with optional experiment association.
- `get`: Retrieve a cultivar by population, accession, and optional experiment name.
- `get_by_id`: Retrieve a cultivar by its ID.
- `get_all`: Retrieve all cultivars.
- `search`: Search for cultivars based on various criteria.
- `update`: Update the details of a cultivar.
- `delete`: Delete a cultivar. 
- `refresh`: Refresh the cultivar's data from the database.
- `get_info`: Get additional information about the cultivar.
- `set_info`: Set additional information for the cultivar.
- `get_associated_experiments`: Get all experiments associated with the cultivar.
- `associate_experiment`: Associate the cultivar with an experiment.
- `unassociate_experiment`: Unassociate the cultivar from an experiment.
- `belongs_to_experiment`: Check if the cultivar belongs to a specific experiment.
- `get_associated_plots`: Get all plots associated with the cultivar.
- `associate_plot`: Associate the cultivar with a plot.
- `unassociate_plot`: Unassociate the cultivar from a plot.
- `belongs_to_plot`: Check if the cultivar belongs to a specific plot.
- `get_associated_plants`: Get all plants associated with the cultivar.
- `belongs_to_plant`: Check if the cultivar belongs to a specific plant.

"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.cultivars import CultivarModel
from gemini.db.models.associations import ExperimentCultivarModel, PlotCultivarModel
from gemini.db.models.views.experiment_views import ExperimentCultivarsViewModel
from gemini.db.models.views.plot_cultivar_view import PlotCultivarViewModel
from gemini.db.models.views.plant_view import PlantViewModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.plot import Plot
    from gemini.api.plant import Plant

logger = logging.getLogger(__name__)

class Cultivar(APIBase):
    """
    Represents a cultivar, a specific variety of a plant species.

    Attributes:
        id (Optional[ID]): The unique identifier of the cultivar.
        cultivar_population (str): The population of the cultivar.
        cultivar_accession (Optional[str]): The accession number of the cultivar.
        cultivar_info (Optional[dict]): Additional information about the cultivar.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "cultivar_id"))

    cultivar_population: str
    cultivar_accession: Optional[str] = None
    cultivar_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Cultivar object."""
        return f"Cultivar(cultivar_population={self.cultivar_population}, cultivar_accession={self.cultivar_accession}, id={self.id})"

    def __repr__(self):
        """Return a detailed string representation of the Cultivar object."""
        return f"Cultivar(cultivar_population={self.cultivar_population}, cultivar_accession={self.cultivar_accession}, id={self.id})"

    @classmethod
    def exists(
        cls,
        cultivar_population: str,
        cultivar_accession: str,
    ) -> bool:
        """
        Check if a cultivar with the given population and accession exists.

        Examples:
            >>> Cultivar.exists("Wheat", "Accession123")
            True

            >>> Cultivar.exists("Corn", "Accession456")
            False

        Args:
            cultivar_population (str): The population of the cultivar.
            cultivar_accession (str): The accession number of the cultivar.

        Returns:
            bool: True if the cultivar exists, False otherwise.
        """
        try:
            exists = CultivarModel.exists(
                cultivar_population=cultivar_population,
                cultivar_accession=cultivar_accession,
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking the existence of cultivar: {e}")
            return False

    @classmethod
    def create(
        cls,
        cultivar_population: str,
        cultivar_accession: str,
        cultivar_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Cultivar"]:
        """
        Create a new cultivar. If the cultivar already exists, it will return the existing one.

        Examples:
            >>> cultivar = Cultivar.create("Wheat", "Accession123")
            >>> print(cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))

            >>> cultivar = Cultivar.create("Corn", "Accession456", {"info": "test"}, "Experiment1")
            >>> print(cultivar)
            Cultivar(cultivar_population=Corn, cultivar_accession=Accession456, id=UUID(...))

        Args:
            cultivar_population (str): The population of the cultivar.
            cultivar_accession (str): The accession number of the cultivar.
            cultivar_info (dict, optional): Additional information about the cultivar. Defaults to {}.
            experiment_name (str, optional): The name of the experiment to associate the cultivar with. Defaults to None.

        Returns:
            Optional["Cultivar"]: The created cultivar, or None if an error occurred.
        """
        try:
            db_instance = CultivarModel.get_or_create(
                cultivar_population=cultivar_population,
                cultivar_accession=cultivar_accession,
                cultivar_info=cultivar_info,
            )
            cultivar = cls.model_validate(db_instance)
            # Associate with experiment if provided
            if experiment_name:
                cultivar.associate_experiment(experiment_name)
            return cultivar
        except Exception as e:
            logger.error(f"Error creating cultivar: {e}")
            return None
        
    @classmethod
    def get(cls, cultivar_population: str, cultivar_accession: str, experiment_name: str = None) -> Optional["Cultivar"]:
        """
        Get a cultivar by its population, accession, and optionally, experiment name.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> print(cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))

            >>> cultivar = Cultivar.get("Corn", "Accession456", "Experiment1")
            >>> print(cultivar)
            Cultivar(cultivar_population=Corn, cultivar_accession=Accession456, id=UUID(...))

        Args:
            cultivar_population (str): The population of the cultivar.
            cultivar_accession (str): The accession number of the cultivar.
            experiment_name (str, optional): The name of the experiment. Defaults to None.

        Returns:
            Optional["Cultivar"]: The cultivar, or None if not found.
        """
        try:
            db_instance = ExperimentCultivarsViewModel.get_by_parameters(
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population,
                experiment_name=experiment_name,
            )
            if not db_instance:
                logger.debug(f"Cultivar with accession {cultivar_accession} and population {cultivar_population} not found.")
                return None
            cultivar = cls.model_validate(db_instance)
            return cultivar
        except Exception as e:
            logger.error(f"Error getting cultivar: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Cultivar"]:
        """
        Get a cultivar by its ID.

        Examples:
            >>> cultivar = Cultivar.get_by_id(UUID(...))
            >>> print(cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the cultivar.

        Returns:
            Optional["Cultivar"]: The cultivar, or None if not found.
        """
        try:
            db_instance = CultivarModel.get(id)
            if not db_instance:
                logger.warning(f"Cultivar with ID {id} does not exist.")
                return None
            cultivar = cls.model_validate(db_instance)
            return cultivar
        except Exception as e:
            logger.error(f"Error getting cultivar by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Cultivar"]]:
        """
        Get all cultivars.

        Examples:
            >>> cultivars = Cultivar.get_all()
            >>> for cultivar in cultivars:
            ...     print(cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))
            Cultivar(cultivar_population=Corn, cultivar_accession=Accession456, id=UUID(...))


        Returns:
            Optional[List["Cultivar"]]: A list of all cultivars, or None if an error occurred.
        """
        try:
            cultivars = CultivarModel.all(limit=limit, offset=offset)
            if not cultivars or len(cultivars) == 0:
                logger.info("No cultivars found.")
                return None
            cultivars = [cls.model_validate(cultivar) for cultivar in cultivars]
            return cultivars
        except Exception as e:
            logger.error(f"Error getting all cultivars: {e}")
            return None
        
    @classmethod
    def search(
        cls, 
        cultivar_population: str = None,
        cultivar_accession: str = None,
        cultivar_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Cultivar"]]:
        """
        Search for cultivars based on various criteria.

        Examples:
            >>> cultivars = Cultivar.search(cultivar_population="Wheat")
            >>> for cultivar in cultivars:
            ...     print(cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession456, id=UUID(...))

        Args:
            cultivar_population (str, optional): The population of the cultivar. Defaults to None.
            cultivar_accession (str, optional): The accession number of the cultivar. Defaults to None.
            cultivar_info (dict, optional): Additional information about the cultivar. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.

        Returns:
            Optional[List["Cultivar"]]: A list of matching cultivars, or None if an error occurred.
        """
        try:
            if not any([experiment_name, cultivar_population, cultivar_accession, cultivar_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            cultivars = ExperimentCultivarsViewModel.search(
                experiment_name=experiment_name,
                cultivar_population=cultivar_population,
                cultivar_accession=cultivar_accession,
                cultivar_info=cultivar_info,
            )
            if not cultivars or len(cultivars) == 0:
                logger.info("No cultivars found with the provided search parameters.")
                return None
            cultivars = [cls.model_validate(cultivar) for cultivar in cultivars]
            return cultivars
        except Exception as e:
            logger.error(f"Error searching cultivars: {e}")
            return None
        
    def update(
        self,
        cultivar_accession: str = None,
        cultivar_population: str = None,
        cultivar_info: dict = None,
    ) -> Optional["Cultivar"]:
        """
        Update the details of the cultivar.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> updated_cultivar = cultivar.update(cultivar_accession="NewAccession")
            >>> print(updated_cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=NewAccession, id=UUID(...))
            

        Args:
            cultivar_accession (str, optional): The new accession number. Defaults to None.
            cultivar_population (str, optional): The new population. Defaults to None.
            cultivar_info (dict, optional): The new information. Defaults to None.

        Returns:
            Optional["Cultivar"]: The updated cultivar, or None if an error occurred.
        """
        try:
            if not any([cultivar_accession, cultivar_population, cultivar_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            
            current_id = self.id
            cultivar = CultivarModel.get(current_id)
            if not cultivar:
                logger.warning(f"Cultivar with ID {current_id} does not exist.")
                return None
            cultivar = CultivarModel.update(
                cultivar,
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population,
                cultivar_info=cultivar_info,
            )
            cultivar = self.model_validate(cultivar)
            self.refresh()
            return cultivar
        except Exception as e:
            logger.error(f"Error updating cultivar: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the cultivar.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> success = cultivar.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the cultivar was deleted successfully, False otherwise.
        """
        try:
            current_id = self.id
            cultivar = CultivarModel.get(current_id)
            if not cultivar:
                logger.warning(f"Cultivar with ID {current_id} does not exist.")
                return False
            CultivarModel.delete(cultivar)
            return True
        except Exception as e:
            return False
        
    
    def refresh(self) -> Optional["Cultivar"]:
        """
        Refresh the cultivar's data from the database. It is rarely needed to be called by the user,
        as the data is automatically refreshed when accessed.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> refreshed_cultivar = cultivar.refresh()
            >>> print(refreshed_cultivar)
            Cultivar(cultivar_population=Wheat, cultivar_accession=Accession123, id=UUID(...))

        Returns:
            Optional["Cultivar"]: The refreshed cultivar, or None if an error occurred.
        """
        try:
            db_instance = CultivarModel.get(self.id)
            if not db_instance:
                logger.warning(f"Cultivar with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing cultivar: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the cultivar.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> info = cultivar.get_info()
            >>> print(info)
            {'key1': 'value1', 'key2': 'value2'}

        Returns:
            Optional[dict]: The cultivar's information, or None if not found.
        """
        try:
            current_id = self.id
            cultivar = CultivarModel.get(current_id)
            if not cultivar:
                logger.warning(f"Cultivar with ID {current_id} does not exist.")
                return None
            cultivar_info = cultivar.cultivar_info
            if not cultivar_info:
                logger.info("Cultivar info is empty.")
                return None
            return cultivar_info
        except Exception as e:
            logger.error(f"Error getting cultivar info: {e}")
            return None
        
    def set_info(self, cultivar_info: dict) -> Optional["Cultivar"]:
        """
        Set the additional information of the cultivar.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> updated_cultivar = cultivar.set_info({"key1": "value1", "key2": "value2"})
            >>> print(updated_cultivar.get_info())
            {'key1': 'value1', 'key2': 'value2'}

        Args:
            cultivar_info (dict): The new information to set.

        Returns:
            Optional["Cultivar"]: The updated cultivar, or None if an error occurred.
        """
        try:
            current_id = self.id
            cultivar = CultivarModel.get(current_id)
            if not cultivar:
                logger.warning(f"Cultivar with ID {current_id} does not exist.")
                return None
            cultivar = CultivarModel.update(
                cultivar,
                cultivar_info=cultivar_info
            )
            cultivar = self.model_validate(cultivar)
            self.refresh()
            return cultivar
        except Exception as e:
            logger.error(f"Error setting cultivar info: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with the cultivar. Which are the experiments
        that have this cultivar as part of their population.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> experiments = cultivar.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=Experiment1, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))
        

        Returns:
            A list of associated experiments, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            current_id = self.id
            experiment_cultivars = ExperimentCultivarsViewModel.search(cultivar_id=current_id)
            if not experiment_cultivars or len(experiment_cultivars) == 0:
                logger.info("No associated experiments found.")
                return None
            experiments = [Experiment.model_validate(experiment_cultivar) for experiment_cultivar in experiment_cultivars]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate the cultivar with an experiment. If the cultivar is already associated with the experiment,
        it will return the experiment without creating a new association.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> experiment = cultivar.associate_experiment("Experiment1")
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
            existing_association = ExperimentCultivarModel.get_by_parameters(
                experiment_id=experiment.id,
                cultivar_id=self.id
            )
            if existing_association:
                logger.info(f"Cultivar {self.cultivar_population} is already associated with experiment {experiment_name}.")
                return experiment
            new_association = ExperimentCultivarModel.get_or_create(
                experiment_id=experiment.id,
                cultivar_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate cultivar {self.cultivar_population} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating cultivar with experiment: {e}")
            return None
        
    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate the cultivar from an experiment. If the cultivar is not associated with the experiment,
        it will return None without making any changes.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> experiment = cultivar.unassociate_experiment("Experiment1")
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
            existing_association = ExperimentCultivarModel.get_by_parameters(
                experiment_id=experiment.id,
                cultivar_id=self.id
            )
            if not existing_association:
                logger.info(f"Cultivar {self.cultivar_population} is not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentCultivarModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate cultivar {self.cultivar_population} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating cultivar from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if the cultivar belongs to a specific experiment.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> belongs = cultivar.belongs_to_experiment("Experiment1")
            >>> print(belongs)
            True

            >>> belongs = cultivar.belongs_to_experiment("NonExistentExperiment")
            >>> print(belongs)
            False 

        Args:
            experiment_name (str): The name of the experiment.

        Returns:
            bool: True if the cultivar belongs to the experiment, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentCultivarModel.exists(
                experiment_id=experiment.id,
                cultivar_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if cultivar belongs to experiment: {e}")
            return False

    def get_associated_plots(self) -> Optional[List["Plot"]]:
        """
        Get all plots associated with the cultivar. Which are the plots that have this cultivar
        as part of their population.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> plots = cultivar.get_associated_plots()
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
            plot_cultivars = PlotCultivarViewModel.search(cultivar_id=current_id)
            if not plot_cultivars or len(plot_cultivars) == 0:
                logger.info("No associated plots found.")
                return None
            plots = [Plot.model_validate(plot_cultivar) for plot_cultivar in plot_cultivars]
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
        Associate the cultivar with a plot.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> plot = cultivar.associate_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
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
            existing_association = PlotCultivarModel.get_by_parameters(
                plot_id=plot.id,
                cultivar_id=self.id
            )
            if existing_association:
                logger.info(f"Cultivar {self.cultivar_population} is already associated with plot {plot_number}.")
                return plot
            new_association = PlotCultivarModel.get_or_create(
                plot_id=plot.id,
                cultivar_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate cultivar {self.cultivar_population} with plot {plot_number}.")
                return None
            self.refresh()
            return plot
        except Exception as e:
            logger.error(f"Error associating cultivar with plot: {e}")
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
        Unassociate the cultivar from a plot.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> plot = cultivar.unassociate_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
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
            existing_association = PlotCultivarModel.get_by_parameters(
                plot_id=plot.id,
                cultivar_id=self.id
            )
            if not existing_association:
                logger.info(f"Cultivar {self.cultivar_population} is not associated with plot {plot_number}.")
                return None
            is_deleted = PlotCultivarModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate cultivar {self.cultivar_population} from plot {plot_number}.")
                return None
            self.refresh()
            return plot
        except Exception as e:
            logger.error(f"Error unassociating cultivar from plot: {e}")
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
        Check if the cultivar belongs to a specific plot.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> belongs = cultivar.belongs_to_plot(1, 1, 1, "Experiment1", "Season1", "Site1")
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
            bool: True if the cultivar belongs to the plot, False otherwise.
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
            association_exists = PlotCultivarModel.exists(
                plot_id=plot.id,
                cultivar_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if cultivar belongs to plot: {e}")
            return False
        
    def get_associated_plants(self) -> Optional[List["Plant"]]:
        """
        Get all plants associated with the cultivar. Which are the plants that have this cultivar
        as part of their population.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> plants = cultivar.get_associated_plants()
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
            cultivar_plants = PlantViewModel.search(cultivar_id=current_id)
            if not cultivar_plants or len(cultivar_plants) == 0:
                logger.info("No associated plants found.")
                return None
            plants = [Plant.model_validate(cultivar_plant) for cultivar_plant in cultivar_plants]
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
        Check if the cultivar belongs to a specific plant.

        Examples:
            >>> cultivar = Cultivar.get("Wheat", "Accession123")
            >>> belongs = cultivar.belongs_to_plant(1, 1, 1, 1, "Experiment1", "Season1", "Site1")
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
            bool: True if the cultivar belongs to the plant, False otherwise.
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
                cultivar_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if cultivar belongs to plant: {e}")
            return False
