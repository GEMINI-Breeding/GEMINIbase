"""
This module defines the Season class, which represents a season entity, including its metadata, associations to experiments, and related operations.

It includes methods for creating, retrieving, updating, and deleting seasons, as well as methods for checking existence, searching, and managing associations with experiments.

This module includes the following methods:

- `exists`: Check if a season with the given name and experiment exists.
- `create`: Create a new season.
- `get`: Retrieve a season by its name and experiment.
- `get_by_id`: Retrieve a season by its ID.
- `get_all`: Retrieve all seasons.
- `search`: Search for seasons based on various criteria.
- `update`: Update the details of a season.
- `delete`: Delete a season.
- `refresh`: Refresh the season's data from the database.
- `get_info`: Get the additional information of the season.
- `set_info`: Set the additional information of the season.
- Association methods for experiments.

"""

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.seasons import SeasonModel
from gemini.db.models.views.experiment_views import ExperimentSeasonsViewModel
from datetime import date, timedelta

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment

logger = logging.getLogger(__name__)

class Season(APIBase):
    """
    Represents a season entity, including its metadata, associations to experiments, and related operations.

    Attributes:
        id (Optional[ID]): The unique identifier of the season.
        season_name (str): The name of the season.
        season_start_date (date): The start date of the season.
        season_end_date (date): The end date of the season.
        season_info (Optional[dict]): Additional information about the season.
        experiment_id (Optional[ID]): The ID of the associated experiment.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "season_id"))

    season_name: str
    season_start_date: date
    season_end_date: date
    season_info: Optional[dict] = None
    experiment_id: Optional[ID] = None

    def __str__(self):
        """Return a string representation of the Season object."""
        return f"Season(season_name={self.season_name}, season_start_date={self.season_start_date}, season_end_date={self.season_end_date}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Season object."""
        return f"Season(id={self.id}, season_name={self.season_name}, season_start_date={self.season_start_date}, season_end_date={self.season_end_date})"

    @classmethod
    def exists(
        cls,
        season_name: str,
        experiment_name: str,
    ) -> bool:
        """
        Check if a season with the given name and experiment exists.

        Examples:
            >>> Season.exists(season_name="Summer 2023", experiment_name="Experiment A")
            True
            >>> Season.exists(season_name="Winter 2023", experiment_name="Experiment B")
            False

        Args:
            season_name (str): The name of the season.
            experiment_name (str): The name of the experiment.
        Returns:
            bool: True if the season exists, False otherwise.
        """
        try:
            exists = ExperimentSeasonsViewModel.exists(
                season_name=season_name,
                experiment_name=experiment_name,
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of season: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        season_name: str,
        season_start_date: date = date.today(),
        season_end_date: date = date.today() + timedelta(days=30),
        season_info: dict = None,
        experiment_name: str = None
    ) -> Optional["Season"]:
        """
        Create a new season.

        Examples:
            >>> season = Season.create(season_name="Summer 2023", season_start_date=date(2023, 6, 1), season_end_date=date(2023, 8, 31), season_info={"description": "Summer season"})
            >>> print(season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))

        Args:
            season_name (str): The name of the season.
            season_start_date (date, optional): The start date. Defaults to today.
            season_end_date (date, optional): The end date. Defaults to today + 30 days.
            season_info (dict, optional): Additional information. Defaults to {{}}.
            experiment_name (str, optional): The name of the experiment to associate. Defaults to None.
        Returns:
            Optional[Season]: The created season, or None if an error occurred.
        """
        try:
            db_instance = SeasonModel.get_or_create(
                season_name=season_name,
                season_start_date=season_start_date,
                season_end_date=season_end_date,
                season_info=season_info,
            )
            season = cls.model_validate(db_instance)
            if experiment_name:
                season.associate_experiment(experiment_name=experiment_name)
            return season
        except Exception as e:
            logger.error(f"Error creating season: {e}")
            return None
        
    @classmethod
    def get(
        cls,
        season_name: str,
        experiment_name: str = None
    ) -> Optional["Season"]:
        """
        Retrieve a season by its name and experiment.

        Examples:
            >>> season = Season.get(season_name="Summer 2023", experiment_name="Experiment A")
            >>> print(season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))

        Args:
            season_name (str): The name of the season.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
        Returns:
            Optional[Season]: The season, or None if not found.
        """
        try:
            db_instance = ExperimentSeasonsViewModel.get_by_parameters(
                season_name=season_name,
                experiment_name=experiment_name,
            )
            if not db_instance:
                logger.warning(f"Season with name {season_name} does not exist.")
                return None
            season = cls.model_validate(db_instance)
            return season
        except Exception as e:
            logger.error(f"Error retrieving season: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Season"]:
        """
        Retrieve a season by its ID.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> print(season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the season.
        Returns:
            Optional[Season]: The season, or None if not found.
        """
        try:
            db_instance = SeasonModel.get(id)
            if not db_instance:
                logger.warning(f"Season with ID {id} does not exist.")
                return None
            season = cls.model_validate(db_instance)
            return season
        except Exception as e:
            logger.error(f"Error retrieving season by ID: {e}")
            return None
        

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Season"]]:
        """
        Retrieve all seasons.

        Examples:
            >>> seasons = Season.get_all()
            >>> for season in seasons:
            ...     print(season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))

        Returns:
            Optional[List[Season]]: List of all seasons, or None if not found.
        """
        try:
            seasons = SeasonModel.all(limit=limit, offset=offset)
            if not seasons or len(seasons) == 0:
                logger.info("No seasons found.")
                return None
            seasons = [cls.model_validate(season) for season in seasons]
            return seasons
        except Exception as e:
            logger.error(f"Error retrieving all seasons: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        season_name: str = None,
        experiment_name: str = None,
        season_start_date: date = None,
        season_end_date: date = None,
        season_info: dict = None
    ) -> Optional[List["Season"]]:
        """
        Search for seasons based on various criteria.

        Examples:
            >>> seasons = Season.search(season_name="Summer 2023")
            >>> for season in seasons:
            ...     print(season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))
            Season(season_name=Summer 2023, season_start_date=2023-07-01, season_end_date=2023-09-30, id=UUID(...))

        Args:
            season_name (str, optional): The name of the season. Defaults to None.
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            season_start_date (date, optional): The start date. Defaults to None.
            season_end_date (date, optional): The end date. Defaults to None.
            season_info (dict, optional): Additional information. Defaults to None.
        Returns:
            Optional[List[Season]]: List of matching seasons, or None if not found.
        """
        try:
            if not any([season_name, experiment_name, season_start_date, season_end_date, season_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            seasons = ExperimentSeasonsViewModel.search(
                season_name=season_name,
                experiment_name=experiment_name,
                season_start_date=season_start_date,
                season_end_date=season_end_date,
                season_info=season_info
            )
            if not seasons or len(seasons) == 0:
                logger.info("No seasons found matching the search criteria.")
                return None
            seasons = [cls.model_validate(season) for season in seasons]
            return seasons
        except Exception as e:
            logger.error(f"Error searching for seasons: {e}")
            return None
        
    def update(
        self,
        season_name: str = None,
        season_start_date: date = None,
        season_end_date: date = None,
        season_info: dict = None
    ) -> Optional["Season"]:
        """
        Update the details of the season.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> updated_season = season.update(season_name="Updated Summer 2023", season_start_date=date(2023, 6, 15))
            >>> print(updated_season)
            Season(season_name=Updated Summer 2023, season_start_date=2023-06-15, season_end_date=2023-08-31, id=UUID(...))

        Args:
            season_name (str, optional): The new name. Defaults to None.
            season_start_date (date, optional): The new start date. Defaults to None.
            season_end_date (date, optional): The new end date. Defaults to None.
            season_info (dict, optional): The new information. Defaults to None.
        Returns:
            Optional[Season]: The updated season, or None if an error occurred.
        """
        try:
            if not any([season_start_date, season_end_date, season_info, season_name]):
                logger.warning("At least one update parameter must be provided.")
                return None
            current_id = self.id
            season = SeasonModel.get(current_id)
            if not season:
                logger.warning(f"Season with ID {current_id} does not exist.")
                return None
            rename = season_name is not None and season_name != season.season_name
            season = SeasonModel.update(
                season,
                season_name=season_name,
                season_start_date=season_start_date,
                season_end_date=season_end_date,
                season_info=season_info
            )
            if rename:
                from gemini.api._rename_cascade import cascade_rename
                cascade_rename(current_id, "season_id", "season_name", season_name)
            updated_season = self.model_validate(season)
            self.refresh()  # Update the current instance
            return updated_season
        except Exception as e:
            logger.error(f"Error updating season: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the season.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> success = season.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the season was deleted, False otherwise.
        """
        try:
            current_id = self.id
            season = SeasonModel.get(current_id)
            if not season:
                logger.warning(f"Season with ID {current_id} does not exist.")
                return False
            SeasonModel.delete(season)
            return True
        except Exception as e:
            logger.error(f"Error deleting season: {e}")
            return False
        
    def refresh(self) -> Optional["Season"]:
        """
        Refresh the season's data from the database.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> refreshed_season = season.refresh()
            >>> print(refreshed_season)
            Season(season_name=Summer 2023, season_start_date=2023-06-01, season_end_date=2023-08-31, id=UUID(...))

        Returns:
            Optional[Season]: The refreshed season, or None if an error occurred.
        """
        try:
            db_instance = SeasonModel.get(self.id)
            if not db_instance:
                logger.warning(f"Season with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing season: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the season.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> season_info = season.get_info()
            >>> print(season_info)
            {'description': 'Summer season', 'temperature': 'warm'}

        Returns:
            Optional[dict]: The season's info, or None if not found.
        """
        try:
            current_id = self.id
            season = SeasonModel.get(current_id)
            if not season:
                logger.warning(f"Season with ID {current_id} does not exist.")
                return None
            season_info = season.season_info
            if not season_info:
                logger.info("Season info is empty.")
                return None
            return season_info
        except Exception as e:
            logger.error(f"Error retrieving season info: {e}")
            return None
        
    def set_info(self, season_info: dict) -> Optional["Season"]:
        """
        Set the additional information of the season.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> updated_season = season.set_info({"description": "Updated summer season", "temperature": "hot"})
            >>> print(updated_season.get_info())
            {'description': 'Updated summer season', 'temperature': 'hot'}

        Args:
            season_info (dict): The new information to set.
        Returns:
            Optional[Season]: The updated season, or None if an error occurred.
        """
        try:
            current_id = self.id
            season = SeasonModel.get(current_id)
            if not season:
                logger.warning(f"Season with ID {current_id} does not exist.")
                return None
            season = SeasonModel.update(
                season,
                season_info=season_info
            )
            updated_season = self.model_validate(season)
            self.refresh()  # Update the current instance
            return updated_season
        except Exception as e:
            logger.error(f"Error setting season info: {e}")
            return None

    def get_associated_experiment(self) -> Optional["Experiment"]:
        """
        Get the experiment associated with this season.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> experiment = season.get_associated_experiment()
            >>> print(experiment)
            Experiment(experiment_name=Experiment A, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Returns:
            Optional[Experiment]: The associated experiment, or None if not found.
        """
        try:
            from gemini.api.experiment import Experiment
            if not self.experiment_id:
                logger.info("This season is not assigned to any experiment.")
                return None
            experiment = Experiment.get_by_id(self.experiment_id)
            if not experiment:
                logger.warning(f"Experiment with ID {self.experiment_id} does not exist.")
                return None
            return experiment
        except Exception as e:
            logger.error(f"Error retrieving experiment for season: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        """
        Associate this season with an experiment.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> experiment = season.associate_experiment(experiment_name="Experiment A")
            >>> print(experiment)
            Experiment(experiment_name=Experiment A, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

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
            existing_association = ExperimentSeasonsViewModel.exists(
                season_id=self.id,
                experiment_id=experiment.id
            )
            if existing_association:
                logger.info(f"Season {self.season_name} is already assigned to experiment {experiment_name}.")
                return self
            db_season = SeasonModel.get(self.id)
            db_season = SeasonModel.update(
                db_season,
                experiment_id=experiment.id
            )
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error assigning experiment to season: {e}")
            return None

    def unassociate_experiment(self) -> Optional["Experiment"]:
        """
        Unassociate this season from its experiment.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> experiment = season.unassociate_experiment()
            >>> print(experiment)
            Experiment(experiment_name=Experiment A, experiment_start_date=2023-01-01, experiment_end_date=2023-12-31, id=UUID(...))

        Returns:
            Optional[Experiment]: The unassociated experiment, or None if an error occurred.
        """
        try:
            from gemini.api.experiment import Experiment
            if not self.experiment_id:
                logger.info("This season is not assigned to any experiment.")
                return None
            db_season = SeasonModel.get(self.id)
            if not db_season:
                logger.warning(f"Season with ID {self.id} does not exist.")
                return None
            experiment = Experiment.get_by_id(self.experiment_id)
            db_season = SeasonModel.update(
                db_season,
                experiment_id=None
            )
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassigning experiment from season: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        """
        Check if this season is associated with a specific experiment.

        Examples:
            >>> season = Season.get_by_id(UUID('...'))
            >>> is_associated = season.belongs_to_experiment(experiment_name="Experiment A")
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
            association_exists = ExperimentSeasonsViewModel.exists(
                season_id=self.id,
                experiment_id=experiment.id
            )
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if season belongs to experiment: {e}")
            return False

