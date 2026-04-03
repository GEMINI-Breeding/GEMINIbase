"""
This module defines the Site class, which represents a geographical site entity, including its metadata, associations to experiments and plots, and related operations.

It includes methods for creating, retrieving, updating, and deleting sites, as well as methods for checking existence, searching, and managing associations with experiments and plots.

This module includes the following methods:

- `exists`: Check if a site with the given name exists.
- `create`: Create a new site.
- `get`: Retrieve a site by its name and experiment.
- `get_by_id`: Retrieve a site by its ID.
- `get_all`: Retrieve all sites.
- `search`: Search for sites based on various criteria.
- `update`: Update the details of a site.
- `delete`: Delete a site.
- `refresh`: Refresh the site's data from the database.
- `get_info`: Get the additional information of the site.
- `set_info`: Set the additional information of the site.
- Association methods for experiments and plots.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.sites import SiteModel
from gemini.db.models.associations import ExperimentSiteModel
from gemini.db.models.views.experiment_views import ExperimentSitesViewModel
from gemini.db.models.views.plot_view import PlotViewModel

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.plot import Plot

logger = logging.getLogger(__name__)

class Site(APIBase):
    """
    Represents a geographical site entity, including its metadata, associations to experiments and plots, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the site.
        site_name (str): The name of the site.
        site_city (Optional[str]): The city where the site is located.
        site_state (Optional[str]): The state where the site is located.
        site_country (Optional[str]): The country where the site is located.
        site_info (Optional[dict]): Additional information about the site.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "site_id"))

    site_name: str
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_country: Optional[str] = None
    site_info: Optional[dict] = None

    def __str__(self):
        """Return a string representation of the Site object."""
        return f"Site(site_name={self.site_name}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Site object."""
        return f"Site(site_name={self.site_name}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        site_name: str
    ) -> bool:
        """
        Check if a site with the given name exists.

        Examples:
            >>> Site.exists("Test Site")
            True
            >>> Site.exists("Nonexistent Site")
            False

        Args:
            site_name (str): The name of the site.
        Returns:
            bool: True if the site exists, False otherwise.
        """
        try:
            exists = SiteModel.exists(site_name=site_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of site: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        site_name: str,
        site_city: str = None,
        site_state: str = None,
        site_country: str = None,
        site_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Site"]:
        """
        Create a new site and associate it with an experiment if provided.

        Examples:
            >>> site = Site.create("Test Site", "Test City", "Test State", "Test Country", {"info": "test"}, "Test Experiment")
            >>> print(site)
            Site(site_name=Test Site, id=UUID(...))

        Args:
            site_name (str): The name of the site.
            site_city (str, optional): The city. Defaults to None.
            site_state (str, optional): The state. Defaults to None.
            site_country (str, optional): The country. Defaults to None.
            site_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[Site]: The created site, or None if an error occurred.
        """
        try:
            db_instance = SiteModel.get_or_create(
                site_name=site_name,
                site_city=site_city,
                site_state=site_state,
                site_country=site_country,
                site_info=site_info,
            )
            site = cls.model_validate(db_instance)
            if experiment_name:
                site.associate_experiment(experiment_name)
            return site
        except Exception as e:
            logger.error(f"Error creating site: {e}")
            return None
    
    @classmethod
    def get(
        cls,
        site_name: str,
        experiment_name: str = None
    ) -> Optional["Site"]:
        """
        Retrieve a site by its name and experiment.

        Examples:
            >>> site = Site.get("Test Site", "Test Experiment")
            >>> print(site)
            Site(site_name=Test Site, id=UUID(...))

        Args:
            site_name (str): The name of the site.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Site]: The site, or None if not found.
        """
        try:
            db_instance = ExperimentSitesViewModel.get_by_parameters(
                site_name=site_name,
                experiment_name=experiment_name
            )
            if not db_instance:
                logger.debug(f"Site with name {site_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting site: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Site"]:
        """
        Retrieve a site by its ID.


        Examples:
            >>> site = Site.get_by_id(UUID('...'))
            >>> print(site)
            Site(site_name=Test Site, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the site.
        Returns:
            Optional[Site]: The site, or None if not found.
        """
        try:
            db_instance = SiteModel.get(id)
            if not db_instance:
                logger.warning(f"Site with ID {id} does not exist.")
                return None
            site = cls.model_validate(db_instance)
            return site
        except Exception as e:
            logger.error(f"Error getting site by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Site"]]:
        """
        Retrieve all sites.

        Examples:
            >>> sites = Site.get_all()
            >>> print(sites)
            [Site(site_name=Site1, id=UUID(...)), Site(site_name=Site2, id=UUID(...))]

        Returns:
            Optional[List[Site]]: List of all sites, or None if not found.
        """
        try:
            sites = SiteModel.all(limit=limit, offset=offset)
            if not sites or len(sites) == 0:
                logger.info("No sites found.")
                return None
            sites = [cls.model_validate(site) for site in sites]
            return sites
        except Exception as e:
            logger.error(f"Error getting all sites: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        site_name: str = None,
        site_city: str = None,
        site_state: str = None,
        site_country: str = None,
        site_info: dict = None,
        experiment_name: str = None
    ) -> Optional[List["Site"]]:
        """
        Search for sites based on various criteria.

        Examples:
            >>> sites = Site.search(site_name="Test Site")
            >>> print(sites)
            [Site(site_name=Test Site, id=UUID(...))]

        Args:
            site_name (str, optional): The name of the site. Defaults to None.
            site_city (str, optional): The city. Defaults to None.
            site_state (str, optional): The state. Defaults to None.
            site_country (str, optional): The country. Defaults to None.
            site_info (dict, optional): Additional information. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[List[Site]]: List of matching sites, or None if not found.
        """
        try:
            if not any([site_name, site_city, site_state, site_country, site_info, experiment_name]):
                logger.info("No search parameters provided.")
                return None

            sites = ExperimentSitesViewModel.search(
                site_name=site_name,
                site_city=site_city,
                site_state=site_state,
                site_country=site_country,
                site_info=site_info,
                experiment_name=experiment_name
            )
            if not sites or len(sites) == 0:
                logger.info("No sites found matching the search criteria.")
                return None
            sites = [cls.model_validate(site) for site in sites]
            return sites
        except Exception as e:
            logger.error(f"Error searching sites: {e}")
            return None
        
    def update(
        self,
        site_name: str = None,
        site_city: str = None,
        site_state: str = None,
        site_country: str = None,
        site_info: dict = None
    ) -> Optional["Site"]:
        """
        Update the details of the site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> updated_site = site.update(site_city="New City", site_state="New State")
            >>> print(updated_site)
            Site(site_name=Test Site, id=UUID(...))

        Args:
            site_name (str, optional): The new name. Defaults to None.
            site_city (str, optional): The new city. Defaults to None.
            site_state (str, optional): The new state. Defaults to None.
            site_country (str, optional): The new country. Defaults to None.
            site_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[Site]: The updated site, or None if an error occurred.
        """
        try:
            if not any([site_city, site_state, site_country, site_info, site_name]):
                raise ValueError("At least one update parameter must be provided.")
            
            current_id = self.id
            site = SiteModel.get(current_id)
            if not site:
                logger.warning(f"Site with ID {current_id} does not exist.")
                return None
            
            updated_site = SiteModel.update(
                site,
                site_name=site_name,
                site_city=site_city,
                site_state=site_state,
                site_country=site_country,
                site_info=site_info
            )
            updated_site = self.model_validate(updated_site)
            self.refresh()
            return updated_site
        except Exception as e:
            logger.error(f"Error updating site: {e}")
            return None
    
    def delete(self) -> bool:
        """
        Delete the site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> deleted = site.delete()
            >>> print(deleted)
            True

        Returns:
            bool: True if the site was deleted, False otherwise.
        """
        try:
            current_id = self.id
            site = SiteModel.get(current_id)
            if not site:
                logger.warning(f"Site with ID {current_id} does not exist.")
                return False
            
            SiteModel.delete(site)
            return True
        except Exception as e:
            logger.error(f"Error deleting site: {e}")
            return False
        
    def refresh(self) -> Optional["Site"]:
        """
        Refresh the site's data from the database.

        Examples:
            >>> site = Site.get("Test Site")
            >>> refreshed_site = site.refresh()
            >>> print(refreshed_site)
            Site(site_name=Test Site, id=UUID(...))

        Returns:
            Optional[Site]: The refreshed site, or None if an error occurred.
        """
        try:
            db_instance = SiteModel.get(self.id)
            if not db_instance:
                logger.warning(f"Site with ID {self.id} does not exist.")
                return self
            
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing site: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> site_info = site.get_info()
            >>> print(site_info)
            {'info': 'test'}

        Returns:
            Optional[dict]: The site's info, or None if not found.
        """
        try:
            current_id = self.id
            site = SiteModel.get(current_id)
            if not site:
                logger.warning(f"Site with ID {current_id} does not exist.")
                return None
            
            site_info = site.site_info
            if not site_info:
                logger.info("Site info is empty.")
                return None
            return site_info
        except Exception as e:
            logger.error(f"Error getting site info: {e}")
            return None
        
    def set_info(self, site_info: dict) -> Optional["Site"]:
        """
        Set the additional information of the site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> updated_site = site.set_info({"new_info": "updated"})
            >>> print(updated_site.site_info)
            {'new_info': 'updated'}

        Args:
            site_info (dict): The new information to set.
        Returns:
            Optional[Site]: The updated site, or None if an error occurred.
        """
        try:
            current_id = self.id
            site = SiteModel.get(current_id)
            if not site:
                logger.warning(f"Site with ID {current_id} does not exist.")
                return None
            
            updated_site = SiteModel.update(
                site,
                site_info=site_info
            )
            updated_site = self.model_validate(updated_site)
            self.refresh()
            return updated_site
        except Exception as e:
            logger.error(f"Error setting site info: {e}")
            return None
        
    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        """
        Get all experiments associated with this site.
        
        Examples:
            >>> site = Site.get("Test Site")
            >>> experiments = site.get_associated_experiments()
            >>> for experiment in experiments:
            ...     print(experiment)
            Experiment(experiment_name=Test Experiment, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))
            Experiment(experiment_name=Another Experiment, experiment_start_date=2023-02-01, experiment_end_date=2023-11-30, id=UUID(...))

        Returns:
            Optional[List[Experiment]]: A list of associated experiments, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment_sites = ExperimentSitesViewModel.search(site_id=self.id)
            if not experiment_sites or len(experiment_sites) == 0:
                logger.info(f"No associated experiments found for site {self.site_name}.")
                return None
            experiments = [Experiment.model_validate(experiment) for experiment in experiment_sites]
            return experiments
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this site with an experiment.

        Examples:
            >>> site = Site.get("Test Site")
            >>> experiment = site.associate_experiment("Test Experiment")
            >>> print(experiment)
            Experiment(experiment_name=Test Experiment, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to associate.
        Returns:
            Optional[Experiment]: The associated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentSiteModel.get_by_parameters(
                experiment_id=experiment.id,
                site_id=self.id
            )
            if existing_association:
                logger.info(f"Site {self.site_name} already associated with experiment {experiment_name}.")
                return None
            new_association = ExperimentSiteModel.get_or_create(
                experiment_id=experiment.id,
                site_id=self.id
            )
            if not new_association:
                logger.info(f"Failed to associate site {self.site_name} with experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Unassociate this site from an experiment.

        Examples:
            >>> site = Site.get("Test Site")
            >>> experiment = site.unassociate_experiment("Test Experiment")
            >>> print(experiment)
            Experiment(experiment_name=Test Experiment, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment to unassociate.
        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing_association = ExperimentSiteModel.get_by_parameters(
                experiment_id=experiment.id,
                site_id=self.id
            )
            if not existing_association:
                logger.info(f"Site {self.site_name} not associated with experiment {experiment_name}.")
                return None
            is_deleted = ExperimentSiteModel.delete(existing_association)
            if not is_deleted:
                logger.info(f"Failed to unassociate site {self.site_name} from experiment {experiment_name}.")
                return None
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this site is associated with a specific experiment.

        Examples:
            >>> site = Site.get("Test Site")
            >>> is_associated = site.belongs_to_experiment("Test Experiment")
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
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return False
            association_exists = ExperimentSiteModel.exists(
                experiment_id=experiment.id,
                site_id=self.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking experiment membership: {e}")
            return False

    def get_associated_plots(self) -> Optional[List["Plot"]]:
        """
        Get all plots associated with this site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> plots = site.get_associated_plots()
            >>> for plot in plots:
            ...     print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))
            Plot(plot_number=2, plot_row_number=1, plot_column_number=2, id=UUID(...))

        Returns:
            Optional[List[Plot]]: A list of associated plots, or None if not found.
        """
        try:
            from gemini.api.plot import Plot
            plots = PlotViewModel.search(site_id=self.id)
            if not plots or len(plots) == 0:
                logger.info(f"No associated plots found for site {self.site_name}.")
                return None
            plots = [Plot.model_validate(plot) for plot in plots]
            return plots
        except Exception as e:
            logger.error(f"Error getting associated plots: {e}")
            return None
        
    def create_new_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None,
        plot_info: dict = None
    ) -> Optional["Plot"]:
        """
        Create and associate a new plot with this site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> new_plot = site.create_new_plot(1, 1, 1, "Test Experiment", "2023 Season", {"info": "test"})
            >>> print(new_plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
            plot_info (dict, optional): Additional information. Defaults to {{}}.
        Returns:
            Optional[Plot]: The created and associated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            new_plot = Plot.create(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=self.site_name,
                plot_info=plot_info
            )
            if not new_plot:
                logger.info(f"Failed to create new plot {plot_number}.")
                return None
            return new_plot
        except Exception as e:
            logger.error(f"Error creating new plot: {e}")
            return None

    def associate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None
    ) -> Optional["Plot"]:
        """
        Associate an existing plot with this site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> plot = site.associate_plot(1, 1, 1, "Test Experiment", "2023 Season")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
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
                season_name=season_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return None
            plot.associate_site(site_name=self.site_name)
            return plot
        except Exception as e:
            logger.error(f"Error associating plot: {e}")
            return None
            

    def unassociate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None
    ) -> Optional["Plot"]:
        """
        Unassociate a plot from this site.

        Examples:
            >>> site = Site.get("Test Site")
            >>> plot = site.unassociate_plot(1, 1, 1, "Test Experiment", "2023 Season")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
        Returns:
            Optional[Plot]: The unassociated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return None
            plot.unassociate_site()
            return plot
        except Exception as e:
            logger.error(f"Error unassociating plot: {e}")
            return None
        

    def belongs_to_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        experiment_name: str = None,
        season_name: str = None
    ) -> bool:
        """
        Check if this site is associated with a specific plot.

        Examples:
            >>> site = Site.get("Test Site")
            >>> is_associated = site.belongs_to_plot(1, 1, 1, "Test Experiment", "2023 Season")
            >>> print(is_associated)
            True

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_name (str, optional): The name of the season. Defaults to None.
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
                season_name=season_name
            )
            if not plot:
                logger.warning(f"Plot {plot_number} does not exist.")
                return False
            association_exists = PlotViewModel.exists(
                site_id=self.id,
                plot_id=plot.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking plot membership: {e}")
            return False

