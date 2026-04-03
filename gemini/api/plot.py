"""
This module defines the Plot class, which represents a plot entity, including its metadata, associations to experiments, seasons, sites, cultivars, and plants, and related operations.

It includes methods for creating, retrieving, updating, and deleting plots, as well as methods for checking existence, searching, and managing associations with experiments, seasons, sites, cultivars, and plants.

This module includes the following methods:

- `exists`: Check if a plot with the given parameters exists.
- `create`: Create a new plot.
- `get`: Retrieve a plot by its parameters.
- `get_by_id`: Retrieve a plot by its ID.
- `get_all`: Retrieve all plots.
- `search`: Search for plots based on various criteria.
- `update`: Update the details of a plot.
- `delete`: Delete a plot.
- `refresh`: Refresh the plot's data from the database.
- `get_info`: Get the additional information of the plot.
- `set_info`: Set the additional information of the plot.
- Association methods for experiments, seasons, sites, cultivars, and plants.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.api.cultivar import Cultivar
from gemini.db.models.plots import PlotModel
from gemini.db.models.associations import PlotCultivarModel
from gemini.db.models.views.plot_cultivar_view import PlotCultivarViewModel
from gemini.db.models.views.plot_view import PlotViewModel


if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.season import Season
    from gemini.api.site import Site
    from gemini.api.cultivar import Cultivar

logger = logging.getLogger(__name__)

class Plot(APIBase):
    """
    Represents a plot entity, including its metadata, associations to experiments, seasons, sites, cultivars, and plants, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the plot.
        plot_number (int): The number of the plot.
        plot_row_number (int): The row number of the plot.
        plot_column_number (int): The column number of the plot.
        plot_geometry_info (Optional[dict]): Geometry information about the plot.
        plot_info (Optional[dict]): Additional information about the plot.
        experiment_id (Optional[ID]): The ID of the associated experiment.
        season_id (Optional[ID]): The ID of the associated season.
        site_id (Optional[ID]): The ID of the associated site.
        experiment_name (Optional[str]): The name of the associated experiment.
        season_name (Optional[str]): The name of the associated season.
        site_name (Optional[str]): The name of the associated site.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "plot_id"))
    plot_number: int
    plot_row_number: int
    plot_column_number: int
    plot_geometry_info: Optional[dict] = None
    plot_info: Optional[dict] = None
    experiment_id: Optional[ID] = None
    season_id: Optional[ID] = None
    site_id: Optional[ID] = None

    experiment_name: Optional[str] = Field(None, exclude=True)
    season_name: Optional[str] = Field(None, exclude=True)
    site_name: Optional[str] = Field(None, exclude=True)

    def __str__(self):
        """Return a string representation of the Plot object."""
        return f"Plot(plot_number={self.plot_number}, plot_row_number={self.plot_row_number}, plot_column_number={self.plot_column_number}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Plot object."""
        return f"Plot(plot_number={self.plot_number}, plot_row_number={self.plot_row_number}, plot_column_number={self.plot_column_number}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None
    ) -> bool:
        """
        Check if a plot with the given parameters exists.

        Examples:
            >>> Plot.exists(plot_number=1, plot_row_number=2, plot_column_number=3)
            True
            >>> Plot.exists(plot_number=1, plot_row_number=2, plot_column_number=3, experiment_name="Experiment 1")
            False

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            bool: True if the plot exists, False otherwise.
        """
        try:
            exists = PlotViewModel.exists(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of plot: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        plot_info: dict = None,
        plot_geometry_info: dict = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        cultivar_accession: str = None,
        cultivar_population: str = None
    ) -> Optional["Plot"]:
        """
        Create a new plot and associate it with experiment, season, site, and cultivar if provided.

        Examples:
            >>> plot = Plot.create(plot_number=1, plot_row_number=2, plot_column_number=3)
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID(...))   

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            plot_info (dict, optional): Additional information about the plot. Defaults to {{}}.
            plot_geometry_info (dict, optional): Geometry information about the plot. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            cultivar_accession (str, optional): The accession of the cultivar. Defaults to None.
            cultivar_population (str, optional): The population of the cultivar. Defaults to None.
        Returns:
            Optional[Plot]: The created plot instance, or None if an error occurred.
        """
        try:
            db_instance = PlotModel.get_or_create(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                plot_info=plot_info,
                plot_geometry_info=plot_geometry_info,
            )
            plot = cls.model_validate(db_instance)
            if experiment_name:
                plot.associate_experiment(experiment_name)
            if season_name:
                plot.associate_season(season_name, experiment_name)
            if site_name:
                plot.associate_site(site_name)
            if cultivar_accession and cultivar_population:
                plot.associate_cultivar(cultivar_accession, cultivar_population)
            return plot
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
    ) -> Optional["Plot"]:
        """
        Retrieve a plot by its parameters.

        Examples:
            >>> plot = Plot.get(plot_number=1, plot_row_number=2, plot_column_number=3)
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
        Returns:
            Optional[Plot]: The plot instance, or None if not found.
        """
        try:
            plot = PlotViewModel.get_by_parameters(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.debug(f"Plot with number {plot_number}, row {plot_row_number}, column {plot_column_number} not found.")
                return None
            plot = cls.model_validate(plot)
            return plot
        except Exception as e:
            logger.error(f"Error getting plot: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Plot"]:
        """
        Retrieve a plot by its ID.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID('...'))
            
        Args:
            id (UUID | int | str): The ID of the plot.
        Returns:
            Optional[Plot]: The plot instance, or None if not found.
        """
        try:
            plot = PlotViewModel.get_by_parameters(plot_id=id)
            if not plot:
                logger.warning(f"Plot with ID {id} does not exist.")
                return None
            plot = cls.model_validate(plot)
            return plot
        except Exception as e:
            logger.error(f"Error getting plot by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Plot"]]:
        """
        Retrieve all plots.

        Examples:
            >>> plots = Plot.get_all()
            >>> for plot in plots:
            ...     print(plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID(...))
            Plot(plot_number=2, plot_row_number=3, plot_column_number=4, id=UUID(...))


        Returns:
            Optional[List[Plot]]: A list of all plots, or None if not found.
        """
        try:
            plots = PlotModel.all(limit=limit, offset=offset)
            if not plots or len(plots) == 0:
                logger.info("No plots found.")
                return None
            plots = [cls.model_validate(plot) for plot in plots]
            return plots
        except Exception as e:
            logger.error(f"Error getting all plots: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        experiment_name: str = None,
        season_name: str = None,
        site_name: str = None,
        cultivar_accession: str = None,
        cultivar_population: str = None
    ) -> Optional[List["Plot"]]:
        """
        Search for plots based on various criteria.

        Examples:
            >>> plots = Plot.search(plot_number=1, plot_row_number=2)
            >>> for plot in plots:
            ...     print(plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID(...))

        Args:
            plot_number (int, optional): The plot number. Defaults to None.
            plot_row_number (int, optional): The row number of the plot. Defaults to None.
            plot_column_number (int, optional): The column number of the plot. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            site_name (str, optional): The name of the site. Defaults to None.
            cultivar_accession (str, optional): The accession of the cultivar. Defaults to None.
            cultivar_population (str, optional): The population of the cultivar. Defaults to None.
        Returns:
            Optional[List[Plot]]: A list of matching plots, or None if not found.
        """
        try:
            if not any([plot_number, plot_row_number, plot_column_number, experiment_name, season_name, site_name]):
                logger.warning("At least one search parameter must be provided.")
                return None

            plots = PlotViewModel.search(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population
            )
            if not plots or len(plots) == 0:
                logger.info("No plots found with the provided search parameters.")
                return None
            plots = [cls.model_validate(plot) for plot in plots]
            return plots if plots else None
        except Exception as e:
            logger.error(f"Error searching plots: {e}")
            return None
        
    def update(
        self,
        plot_number: int = None,
        plot_row_number: int = None,
        plot_column_number: int = None,
        plot_info: dict = None,
        plot_geometry_info: dict = None
    ) -> Optional["Plot"]:
        """
        Update the details of the plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> updated_plot = plot.update(plot_number=2, plot_row_number=3)
            >>> print(updated_plot)
            Plot(plot_number=2, plot_row_number=3, plot_column_number=3, id=UUID('...'))

        Args:
            plot_number (int, optional): The new plot number. Defaults to None.
            plot_row_number (int, optional): The new row number. Defaults to None.
            plot_column_number (int, optional): The new column number. Defaults to None.
            plot_info (dict, optional): The new plot information. Defaults to None.
            plot_geometry_info (dict, optional): The new geometry information. Defaults to None.
        Returns:
            Optional[Plot]: The updated plot instance, or None if an error occurred.
        """
        try:
            if not any([plot_number, plot_row_number, plot_column_number, plot_info, plot_geometry_info]):
                logger.warning("At least one parameter must be provided.")
                return None

            current_id = self.id
            plot = PlotModel.get(current_id)
            if not plot:
                logger.warning(f"Plot with ID {current_id} does not exist.")
                return None
            plot = PlotModel.update(
                plot,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                plot_info=plot_info,
                plot_geometry_info=plot_geometry_info
            )
            plot = self.model_validate(plot)
            self.refresh()
            return plot
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            return None
        
    def refresh(self) -> Optional["Plot"]:
        """
        Refresh the plot's data from the database.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> refreshed_plot = plot.refresh()
            >>> print(refreshed_plot)
            Plot(plot_number=1, plot_row_number=2, plot_column_number=3, id=UUID('...'))

        Returns:
            Optional[Plot]: The refreshed plot instance, or None if an error occurred.
        """
        try:
            db_instance = PlotViewModel.get_by_parameters(plot_id=self.id)
            if not db_instance:
                logger.warning(f"Plot with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            instance_dict = dict(instance)
            for key, value in instance_dict.items():
                if hasattr(self, key) and key != "id":
                    value = getattr(instance, key)
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing plot: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> deleted = plot.delete()
            >>> print(deleted)
            True

        Returns:
            bool: True if the plot was deleted, False otherwise.
        """
        try:
            current_id = self.id
            plot = PlotModel.get(current_id)
            if not plot:
                logger.warning(f"Plot with ID {current_id} does not exist.")
                return False
            PlotModel.delete(plot)
            return True
        except Exception as e:
            logger.error(f"Error deleting plot: {e}")
            return False
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> plot_info = plot.get_info()
            >>> print(plot_info)
            {'key': 'value'}

        Returns:
            Optional[dict]: The plot's info, or None if not found.
        """
        try:
            current_id = self.id
            plot = PlotModel.get(current_id)
            if not plot:
                logger.warning(f"Plot with ID {current_id} does not exist.")
                return None
            plot_info = plot.plot_info
            if not plot_info:
                logger.info("Plot info is empty.")
                return None
            return plot_info
        except Exception as e:
            logger.error(f"Error getting plot info: {e}")
            return None
        
    def set_info(self, plot_info: dict) -> Optional["Plot"]:
        """
        Set the additional information of the plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> updated_plot = plot.set_info({'key': 'new_value'})
            >>> print(updated_plot.get_info())
            {'key': 'new_value'}

        Args:
            plot_info (dict): The new information to set.
        Returns:
            Optional[Plot]: The updated plot instance, or None if an error occurred.
        """
        try:
            current_id = self.id
            plot = PlotModel.get(current_id)
            if not plot:
                logger.warning(f"Plot with ID {current_id} does not exist.")
                return None
            plot = PlotModel.update(
                plot,
                plot_info=plot_info
            )
            plot = self.model_validate(plot)
            self.refresh()
            return self
        except Exception as e:
            logger.error(f"Error setting plot info: {e}")  
            return None
        
    def get_associated_experiment(self) -> Optional["Experiment"]:
        """
        Get the experiment associated with this plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> experiment = plot.get_associated_experiment()
            >>> print(experiment)
            Experiment(experiment_name='Experiment 1', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID(...))

        Returns:
            Optional[Experiment]: The associated experiment, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            if not self.experiment_id:
                logger.info("Plot does not belong to any experiment.")
                return None
            experiment = Experiment.get_by_id(self.experiment_id)
            if not experiment:
                logger.warning(f"Experiment with ID {self.experiment_id} does not exist.")
                return None
            return experiment
        except Exception as e:
            logger.error(f"Error getting experiment: {e}")
            return None


    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this plot is associated with a specific experiment.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> is_associated = plot.belongs_to_experiment("Experiment 1")
            >>> print(is_associated)
            True

        Args:
            experiment_name (str): The name of the experiment to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment with name {experiment_name} does not exist.")
                return False
            association_exists = PlotViewModel.exists(
                plot_id=self.id,
                experiment_id=experiment.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if plot belongs to experiment: {e}")
            return False

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this plot with an experiment.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> experiment = plot.associate_experiment("Experiment 1")
            >>> print(experiment)
            Experiment(experiment_name='Experiment 1', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional[Experiment]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment with name {experiment_name} does not exist.")
                return None
            existing_association = PlotViewModel.get_by_parameters(
                plot_id=self.id,
                experiment_id=experiment.id
            )
            if existing_association:
                logger.info(f"Plot {self.id} is already associated with experiment {experiment_name}.")
                return self
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "experiment_id",
                experiment.id
            )
            logger.info(f"Plot {self.id} associated with experiment {experiment_name}.")
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error assigning experiment to plot: {e}")
            return None

    def unassociate_experiment(self) -> Optional["Experiment"]:
        """
        Unassociate this plot from its experiment.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> experiment = plot.unassociate_experiment()
            >>> print(experiment)
            Experiment(experiment_name='Experiment 1', experiment_start_date='2023-01-01', experiment_end_date='2023-12-31', id=UUID(...))

        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            if not self.experiment_id:
                logger.info("Plot does not belong to any experiment.")
                return None
            experiment = Experiment.get_by_id(self.experiment_id)
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "experiment_id",
                None
            )
            self.refresh()
            return experiment   
        except Exception as e:
            logger.error(f"Error unassigning experiment from plot: {e}")
            return None

    def get_associated_season(self) -> Optional["Season"]:
        """
        Get the season associated with this plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> season = plot.get_associated_season()
            >>> print(season)
            Season(season_name='Season 1', season_start_date='2023-01-01', season_end_date='2023-12-31', id=UUID(...))

        Returns:
            Optional[Season]: The associated season, or None if not found.
        """
        try:
            from gemini.api.season import Season
            if not self.season_id:
                logger.info("Plot does not belong to any season.")
                return None
            season = Season.get_by_id(self.season_id)
            if not season:
                logger.warning(f"Season with ID {self.season_id} does not exist.")
                return None
            return season
        except Exception as e:
            logger.error(f"Error getting season: {e}")
            return None
        

    def belongs_to_season(self, season_name: str, experiment_name: str) -> bool:
        """
        Check if this plot is associated with a specific season.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> is_associated = plot.belongs_to_season("Season 1", "Experiment 1")
            >>> print(is_associated)
            True

        Args:
            season_name (str): The name of the season to check.
            experiment_name (str): The name of the experiment.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.season import Season
            from gemini.api.experiment import Experiment
            season = Season.get(season_name=season_name, experiment_name=experiment_name)
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment or not season:
                logger.warning(f"Experiment with name {experiment_name} or season with name {season_name} does not exist.")
                return False
            association_exists = PlotViewModel.exists(
                plot_id=self.id,
                season_id=self.season_id,
                experiment_id=experiment.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if plot belongs to season: {e}")
            return False

    def associate_season(self, season_name: str, experiment_name: str) -> Optional["Season"]:
        """
        Associate this plot with a season.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> season = plot.associate_season("Season 1", "Experiment 1")
            >>> print(season)
            Season(season_name='Season 1', season_start_date='2023-01-01', season_end_date='2023-12-31', id=UUID(...))

        Args:
            season_name (str): The name of the season to associate.
            experiment_name (str): The name of the experiment.
        Returns:
            Optional[Season]: The associated season, or None if an error occurred.
        """
        try:
            from gemini.api.season import Season
            season = Season.get(season_name=season_name, experiment_name=experiment_name)
            if not season:
                logger.warning(f"Season with name {season_name} does not exist.")
                return None
            existing_association = PlotViewModel.get_by_parameters(
                plot_id=self.id,
                season_id=season.id,
                experiment_id=season.experiment_id
            )
            if existing_association:
                logger.info(f"Plot {self.id} is already associated with season {season_name}.")
                return self
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "season_id",
                season.id
            )
            logger.info(f"Plot {self.id} associated with season {season_name}.")
            self.refresh()
            return season
        except Exception as e:
            logger.error(f"Error assigning season to plot: {e}")
            return None

    def unassociate_season(self) -> Optional["Season"]:
        """
        Unassociate this plot from its season.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> season = plot.unassociate_season()
            >>> print(season)
            Season(season_name='Season 1', season_start_date='2023-01-01', season_end_date='2023-12-31', id=UUID(...))

        Returns:
            Optional[Season]: The unassociated season, or None if an error occurred.
        """
        try:
            from gemini.api.season import Season
            if not self.season_id:
                logger.info("Plot does not belong to any season.")
                return None
            season = Season.get_by_id(self.season_id)
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "season_id",
                None
            )
            self.refresh()
            return season
        except Exception as e:
            logger.error(f"Error unassigning season from plot: {e}")
            return None
        
    def get_associated_site(self) -> Optional["Site"]:
        """
        Get the site associated with this plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> site = plot.get_associated_site()
            >>> print(site)
            Site(site_name='Site 1', id=UUID(...))

        Returns:
            Optional[Site]: The associated site, or None if not found.
        """
        try:
            from gemini.api.site import Site
            if not self.site_id:
                logger.info("Plot does not belong to any site.")
                return None
            site = Site.get_by_id(self.site_id)
            if not site:
                logger.warning(f"Site with ID {self.site_id} does not exist.")
                return None
            return site
        except Exception as e:
            logger.error(f"Error getting site: {e}")
            return None

    def belongs_to_site(self, site_name: str) -> bool:
        """
        Check if this plot is associated with a specific site.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> is_associated = plot.belongs_to_site("Site 1")
            >>> print(is_associated)
            True

        Args:
            site_name (str): The name of the site to check.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.site import Site
            site = Site.get(site_name=site_name)
            if not site:
                logger.warning(f"Site with name {site_name} does not exist.")
                return False
            association_exists = PlotViewModel.exists(
                plot_id=self.id,
                site_id=site.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if plot belongs to site: {e}")
            return False

    def associate_site(self, site_name: str) -> Optional["Site"]:
        """
        Associate this plot with a site.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> site = plot.associate_site("Site 1")
            >>> print(site)
            Site(site_name='Site 1', id=UUID(...))

        Args:
            site_name (str): The name of the site to associate.
        Returns:
            Optional[Site]: The associated site, or None if an error occurred.
        """
        try:
            from gemini.api.site import Site
            site = Site.get(site_name=site_name)
            if not site:
                logger.warning(f"Site with name {site_name} does not exist.")
                return None
            existing_association = PlotViewModel.get_by_parameters(
                plot_id=self.id,
                site_id=site.id
            )
            if existing_association:
                logger.info(f"Plot {self.id} is already associated with site {site_name}.")
                return self
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "site_id",
                site.id
            )
            logger.info(f"Plot {self.id} associated with site {site_name}.")
            self.refresh()
            return site
        except Exception as e:
            logger.error(f"Error assigning site to plot: {e}")
            return None

    def unassociate_site(self) -> Optional["Site"]:
        """
        Unassociate this plot from its site.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> site = plot.unassociate_site()
            >>> print(site)
            Site(site_name='Site 1', id=UUID(...))

        Returns:
            Optional[Site]: The unassociated site, or None if an error occurred.
        """
        try:
            from gemini.api.site import Site
            if not self.site_id:
                logger.info("Plot does not belong to any site.")
                return None
            site = Site.get_by_id(self.site_id)
            db_plot = PlotModel.get(self.id)
            db_plot = PlotModel.update_parameter(
                db_plot,
                "site_id",
                None
            )
            self.refresh()
            return site
        except Exception as e:
            logger.error(f"Error unassigning site from plot: {e}")
            return None

    def get_associated_cultivars(self) -> Optional[List["Cultivar"]]:
        """
        Get all cultivars associated with this plot.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> cultivars = plot.get_associated_cultivars()
            >>> for cultivar in cultivars:
            ...     print(cultivar)
            Cultivar(cultivar_accession='Accession 1', cultivar_population='Population 1', id=UUID(...))

        Returns:
            Optional[List[Cultivar]]: A list of associated cultivars, or None if not found.
        """
        try:
            from gemini.api.cultivar import Cultivar
            cultivars = PlotCultivarViewModel.search(plot_id=self.id)
            if not cultivars or len(cultivars) == 0:
                logger.info("No associated cultivars found for this plot.")
                return None
            cultivars = [Cultivar.model_validate(cultivar) for cultivar in cultivars]
            return cultivars
        except Exception as e:
            logger.error(f"Error getting associated cultivars: {e}")
            return None

    def associate_cultivar(
        self,
        cultivar_accession: str,
        cultivar_population: str
    ) -> Optional["Cultivar"]:
        """
        Associate this plot with a cultivar.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> cultivar = plot.associate_cultivar("Accession 1", "Population 1")
            >>> print(cultivar)
            Cultivar(cultivar_accession='Accession 1', cultivar_population='Population 1', id=UUID(...))

        Args:
            cultivar_accession (str): The accession of the cultivar.
            cultivar_population (str): The population of the cultivar.
        Returns:
            Optional[Cultivar]: The associated cultivar, or None if an error occurred.
        """
        try:
            from gemini.api.cultivar import Cultivar
            cultivar = Cultivar.get(
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population
            )
            if not cultivar:
                logger.warning(f"Cultivar {cultivar_accession} {cultivar_population} does not exist.")
                return None
            existing_association = PlotCultivarViewModel.get_by_parameters(
                plot_id=self.id,
                cultivar_id=cultivar.id
            )
            if existing_association:
                logger.info(f"Cultivar {cultivar_accession} {cultivar_population} is already assigned to this plot.")
                return self
            new_association = PlotCultivarModel.get_or_create(
                plot_id=self.id,
                cultivar_id=cultivar.id
            )
            if not new_association:
                logger.info(f"Failed to assign cultivar {cultivar_accession} {cultivar_population} to plot {self.id}.")
                return None
            self.refresh()
            return cultivar
        except Exception as e:
            logger.error(f"Error assigning cultivar to plot: {e}")
            return None

    def unassociate_cultivar(
        self,
        cultivar_accession: str,
        cultivar_population: str
    ) -> Optional["Cultivar"]:
        """
        Unassociate this plot from a cultivar.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> cultivar = plot.unassociate_cultivar("Accession 1", "Population 1")
            >>> print(cultivar)
            Cultivar(cultivar_accession='Accession 1', cultivar_population='Population 1', id=UUID(...))

        Args:
            cultivar_accession (str): The accession of the cultivar.
            cultivar_population (str): The population of the cultivar.
        Returns:
            Optional[Cultivar]: The unassociated cultivar, or None if an error occurred.
        """
        try:
            from gemini.api.cultivar import Cultivar
            cultivar = Cultivar.get(
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population
            )
            if not cultivar:
                logger.warning(f"Cultivar {cultivar_accession} {cultivar_population} does not exist.")
                return None
            existing_association = PlotCultivarModel.get_by_parameters(
                plot_id=self.id,
                cultivar_id=cultivar.id
            )
            if not existing_association:
                logger.info(f"Cultivar {cultivar_accession} {cultivar_population} is not assigned to this plot.")
                return None
            is_deleted = PlotCultivarModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassign cultivar {cultivar_accession} {cultivar_population} from plot {self.id}.")
                return None
            self.refresh()
            return cultivar
        except Exception as e:
            logger.error(f"Error unassigning cultivar from plot: {e}")
            return None

    def belongs_to_cultivar(
        self,
        cultivar_accession: str,
        cultivar_population: str
    ) -> bool:
        """
        Check if this plot is associated with a specific cultivar.

        Examples:
            >>> plot = Plot.get_by_id(UUID('...'))
            >>> is_associated = plot.belongs_to_cultivar("Accession 1", "Population 1")
            >>> print(is_associated)
            True

        Args:
            cultivar_accession (str): The accession of the cultivar.
            cultivar_population (str): The population of the cultivar.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.cultivar import Cultivar
            cultivar = Cultivar.get(
                cultivar_accession=cultivar_accession,
                cultivar_population=cultivar_population
            )
            if not cultivar:
                logger.warning(f"Cultivar {cultivar_accession} {cultivar_population} does not exist.")
                return False
            association_exists = PlotCultivarViewModel.exists(
                plot_id=self.id,
                cultivar_id=cultivar.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if plot has cultivar: {e}")
            return False