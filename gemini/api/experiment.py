"""
This module defines the Experiment class, which represents an experiment entity, including its metadata and associations to seasons, populations, procedures, scripts, models, sensors, sites, datasets, traits, and plots.

It includes methods for creating, retrieving, updating, and deleting experiments, as well as methods for checking existence, searching, and managing associations with related entities.

This module includes the following methods:

- `exists`: Check if an experiment with the given name exists.
- `create`: Create a new experiment.
- `get`: Retrieve an experiment by its name.
- `get_by_id`: Retrieve an experiment by its ID.
- `get_all`: Retrieve all experiments.
- `search`: Search for experiments based on various criteria.
- `update`: Update the details of an experiment.
- `delete`: Delete an experiment.
- `refresh`: Refresh the experiment's data from the database.
- `get_info`: Get the additional information of the experiment.
- `set_info`: Set the additional information of the experiment.
- Association methods for seasons, populations, procedures, scripts, models, sensors, sensor platforms, sites, datasets, traits, and plots.

"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID

from gemini.api.base import APIBase
from gemini.api.enums import (
    GEMINIDataFormat,
    GEMINIDatasetType,
    GEMINIDataType,
    GEMINISensorType,
    GEMINITraitLevel
)

from gemini.db.models.experiments import ExperimentModel
from gemini.db.models.views.experiment_views import (
    ExperimentPopulationsViewModel,
    ExperimentProceduresViewModel,
    ExperimentScriptsViewModel,
    ExperimentModelsViewModel,
    ExperimentSensorsViewModel,
    ExperimentSitesViewModel,
    ExperimentSeasonsViewModel,
    ExperimentTraitsViewModel,
    ExperimentSensorPlatformsViewModel,
    ExperimentDatasetsViewModel
)
from gemini.db.models.views.plot_view import PlotViewModel

from datetime import date

if TYPE_CHECKING:
    from gemini.api.population import Population
    from gemini.api.procedure import Procedure
    from gemini.api.script import Script
    from gemini.api.model import Model
    from gemini.api.sensor import Sensor
    from gemini.api.sensor_platform import SensorPlatform
    from gemini.api.site import Site
    from gemini.api.season import Season
    from gemini.api.dataset import Dataset
    from gemini.api.trait import Trait
    from gemini.api.plot import Plot


logger = logging.getLogger(__name__)

class Experiment(APIBase):
    """
    Represents an experiment entity, including its metadata and associations to seasons, populations, procedures, scripts, models, sensors, sites, datasets, traits, and plots.

    Attributes:
        id (Optional[ID]): The unique identifier of the experiment.
        experiment_name (str): The name of the experiment.
        experiment_info (Optional[dict]): Additional information about the experiment.
        experiment_start_date (Optional[date]): The start date of the experiment.
        experiment_end_date (Optional[date]): The end date of the experiment.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "experiment_id"))

    experiment_name: str
    experiment_info: Optional[dict] = None
    experiment_start_date: Optional[date] = None
    experiment_end_date: Optional[date] = None

    def __str__(self):
        """Return a string representation of the Experiment object."""
        return f"Experiment(experiment_name={self.experiment_name}, experiment_start_date={self.experiment_start_date}, experiment_end_date={self.experiment_end_date}, id={self.id})"
    
    def __repr__(self):
        """Return a detailed string representation of the Experiment object."""
        return f"Experiment(experiment_name={self.experiment_name}, experiment_start_date={self.experiment_start_date}, experiment_end_date={self.experiment_end_date}, id={self.id})"
    
    @classmethod
    def exists(
        cls,
        experiment_name: str
    ) -> bool:
        """
        Check if an experiment with the given name exists.

        Examples:
            >>> Experiment.exists("My Experiment")
            True
            >>> Experiment.exists("Nonexistent Experiment")
            False

        Args:
            experiment_name (str): The name of the experiment.
        Returns:
            bool: True if the experiment exists, False otherwise.
        """
        try:
            exists = ExperimentModel.exists(experiment_name=experiment_name)
            return exists
        except Exception as e:
            logger.error(f"Error checking existence of experiment: {e}")
            return False
        
    @classmethod
    def create(
        cls,
        experiment_name: str,
        experiment_info: dict = None,
        experiment_start_date: date = date.today(),
        experiment_end_date: date = date.today(),
    ) -> Optional["Experiment"]:
        """
        Create a new experiment. If an experiment with the same name already exists, it will return the existing one.

        Examples:
            >>> experiment = Experiment.create("My Experiment", {"description": "Test experiment"})
            >>> print(experiment)
            Experiment(experiment_name=My Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment.
            experiment_info (dict, optional): Additional information about the experiment. Defaults to {{}}.
            experiment_start_date (date, optional): The start date. Defaults to today.
            experiment_end_date (date, optional): The end date. Defaults to today.
        Returns:
            Optional["Experiment"]: The created experiment, or None if an error occurred.
        """
        try:
            db_instance = ExperimentModel.get_or_create(
                experiment_name=experiment_name,
                experiment_info=experiment_info,
                experiment_start_date=experiment_start_date,
                experiment_end_date=experiment_end_date,
            )
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating experiment: {e}")
            return None
        
    @classmethod
    def get(cls, experiment_name: str) -> Optional["Experiment"]:
        """
        Retrieve an experiment by its name.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> print(experiment)
            Experiment(experiment_name=My Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Args:
            experiment_name (str): The name of the experiment.
        Returns:
            Optional["Experiment"]: The experiment, or None if not found.
        """
        try:
            db_instance = ExperimentModel.get_by_parameters(
                experiment_name=experiment_name,
            )
            if not db_instance:
                logger.debug(f"Experiment with name {experiment_name} not found.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting experiment: {e}")
            return None
        
    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Experiment"]:
        """
        Retrieve an experiment by its ID.

        Examples:
            >>> experiment = Experiment.get_by_id(UUID('...'))
            >>> print(experiment)
            Experiment(experiment_name=My Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Args:
            id (UUID | int | str): The ID of the experiment.
        Returns:
            Optional["Experiment"]: The experiment, or None if not found.
        """
        try:
            db_instance = ExperimentModel.get(id)
            if not db_instance:
                logger.warning(f"Experiment with ID {id} does not exist.")
                return None
            instance = cls.model_validate(db_instance)
            return instance
        except Exception as e:
            logger.error(f"Error getting experiment by ID: {e}")
            return None
        
    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Experiment"]]:
        """
        Retrieve all experiments.

        Examples:
            >>> experiments = Experiment.get_all()
            >>> for exp in experiments:
            ...     print(exp)
            Experiment(experiment_name=Experiment 1, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Returns:
            Optional[List["Experiment"]]: A list of all experiments, or None if an error occurred.
        """
        try:
            experiments = ExperimentModel.all(limit=limit, offset=offset)
            if not experiments or len(experiments) == 0:
                logger.info("No experiments found.")
                return None
            experiments = [cls.model_validate(experiment) for experiment in experiments]
            return experiments
        except Exception as e:
            logger.error(f"Error getting all experiments: {e}")
            return None
        
    @classmethod
    def search(
        cls,
        experiment_name: str = None,
        experiment_info: dict = None,
        experiment_start_date: date = None,
        experiment_end_date: date = None
    ) -> Optional[List["Experiment"]]:
        """
        Search for experiments based on various criteria.

        Examples:
            >>> experiments = Experiment.search(experiment_name="My Experiment")
            >>> for exp in experiments:
            ...     print(exp)
            Experiment(experiment_name=My Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Args:
            experiment_name (str, optional): The name of the experiment. Defaults to None.
            experiment_info (dict, optional): Additional information. Defaults to None.
            experiment_start_date (date, optional): The start date. Defaults to None.
            experiment_end_date (date, optional): The end date. Defaults to None.
        Returns:
            Optional[List["Experiment"]]: A list of matching experiments, or None if an error occurred.
        """
        try:
            if not any([experiment_name, experiment_info, experiment_start_date, experiment_end_date]):
                logger.warning("At least one parameter must be provided for search.")
                return None
            experiments = ExperimentModel.search(
                experiment_name=experiment_name,
                experiment_info=experiment_info,
                experiment_start_date=experiment_start_date,
                experiment_end_date=experiment_end_date
            )
            if not experiments or len(experiments) == 0:
                logger.info("No experiments found with the provided search parameters.")
                return None
            experiments = [cls.model_validate(experiment) for experiment in experiments]
            return experiments
        except Exception as e:
            logger.error(f"Error searching experiments: {e}")
            return None
        
    def update(
        self,
        experiment_name: str = None, 
        experiment_info: dict = None,
        experiment_start_date: date = None,
        experiment_end_date: date = None
    ) -> Optional["Experiment"]:
        """
        Update the details of the experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> updated_experiment = experiment.update(experiment_name="Updated Experiment")
            >>> print(updated_experiment)
            Experiment(experiment_name=Updated Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Args:
            experiment_name (str, optional): The new name. Defaults to None.
            experiment_info (dict, optional): The new information. Defaults to None.
            experiment_start_date (date, optional): The new start date. Defaults to None.
            experiment_end_date (date, optional): The new end date. Defaults to None.
        Returns:
            Optional["Experiment"]: The updated experiment, or None if an error occurred.
        """
        try:
            if not any([experiment_name, experiment_info, experiment_start_date, experiment_end_date]):
                logger.warning("At least one parameter must be provided for update.")
                return None

            current_id = self.id
            experiment = ExperimentModel.get(current_id)
            if not experiment:
                logger.warning(f"Experiment with ID {current_id} does not exist.")
                return None
            
            updated_experiment = ExperimentModel.update(
                experiment,
                experiment_name=experiment_name,
                experiment_info=experiment_info,
                experiment_start_date=experiment_start_date,
                experiment_end_date=experiment_end_date
            )
            updated_experiment = self.model_validate(updated_experiment)
            self.refresh()
            return updated_experiment
        except Exception as e:
            logger.error(f"Error updating experiment: {e}")
            return None
        
    def delete(self) -> bool:
        """
        Delete the experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> success = experiment.delete()
            >>> print(success)
            True

        Returns:
            bool: True if the experiment was deleted, False otherwise.
        """
        try:
            current_id = self.id
            experiment = ExperimentModel.get(current_id)
            if not experiment:
                logger.warning(f"Experiment with ID {current_id} does not exist.")
                return False
            ExperimentModel.delete(experiment)
            return True
        except Exception as e:
            logger.error(f"Error deleting experiment: {e}")
            return False
        
    def refresh(self) -> Optional["Experiment"]:
        """
        Refresh the experiment's data from the database. It is rarely called by the user
        as it is automatically called on access.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> refreshed_experiment = experiment.refresh()
            >>> print(refreshed_experiment)
            Experiment(experiment_name=My Experiment, experiment_start_date=2023-10-01, experiment_end_date=2023-10-01, id=UUID(...))

        Returns:
            Optional["Experiment"]: The refreshed experiment, or None if an error occurred.
        """
        try:
            db_instance = ExperimentModel.get(self.id)
            if not db_instance:
                logger.warning(f"Experiment with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing experiment: {e}")
            return None
        
    def get_info(self) -> Optional[dict]:
        """
        Get the additional information of the experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> info = experiment.get_info()
            >>> print(info)
            {'description': 'Test experiment', 'created_by': 'user'}

        Returns:
            Optional[dict]: The experiment's info, or None if not found.
        """
        try:
            current_id = self.id
            experiment = ExperimentModel.get(current_id)
            if not experiment:
                logger.warning(f"Experiment with ID {current_id} does not exist.")
                return None
            experiment_info = experiment.experiment_info
            if not experiment_info:
                logger.info("Experiment info is empty.")
                return None
            return experiment_info
        except Exception as e:
            logger.error(f"Error getting experiment info: {e}")
            return None
        
    def set_info(self, experiment_info: dict) -> Optional["Experiment"]:
        """
        Set the additional information of the experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> updated_experiment = experiment.set_info({"description": "Updated description"})
            >>> print(updated_experiment.get_info())
            {'description': 'Updated description'}

        Args:
            experiment_info (dict): The new information to set.
        Returns:
            Optional["Experiment"]: The updated experiment, or None if an error occurred.
        """
        try:
            current_id = self.id
            experiment = ExperimentModel.get(current_id)
            if not experiment:
                logger.warning(f"Experiment with ID {current_id} does not exist.")
                return None
            updated_experiment = ExperimentModel.update(
                experiment,
                experiment_info=experiment_info,
            )
            updated_experiment = self.model_validate(updated_experiment)
            self.refresh()
            return updated_experiment
        except Exception as e:
            logger.error(f"Error setting experiment info: {e}")
            return None

    # region Season

    def get_associated_seasons(self) -> Optional[List["Season"]]:
        """
        Get all seasons associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> seasons = experiment.get_associated_seasons()
            >>> for season in seasons:
            ...     print(season)
            Season(season_name=Spring 2024, season_start_date=2024-03-01, season_end_date=2024-05-31, id=UUID(...))
            Season(season_name=Summer 2024, season_start_date=2024-06-01, season_end_date=2024-08-31, id=UUID(...))

        Returns:
            Optional[List["Season"]]: A list of associated seasons, or None if not found.
        """
        try:
            from gemini.api.season import Season
            experiment_seasons = ExperimentSeasonsViewModel.search(experiment_id=self.id)
            if not experiment_seasons or len(experiment_seasons) == 0:
                logger.info("No seasons found for this experiment.")
                return None
            seasons = [Season.model_validate(season) for season in experiment_seasons]
            return seasons
        except Exception as e:
            logger.error(f"Error getting associated seasons: {e}")
            return None

    def create_new_season(
        self,
        season_name: str,
        season_info: dict = None,
        season_start_date: date = date.today(),
        season_end_date: date = date.today(),
    ) -> Optional["Season"]:
        """
        Create and associate a new season with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_season = experiment.create_new_season("Spring 2024", {"description": "Spring season"})
            >>> print(new_season)
            Season(season_name=Spring 2024, season_start_date=2024-03-01, season_end_date=2024-05-31, id=UUID(...))

        Args:
            season_name (str): The name of the new season.
            season_info (dict, optional): Additional information about the season. Defaults to {{}}.
            season_start_date (date, optional): The start date of the season. Defaults to today.
            season_end_date (date, optional): The end date of the season. Defaults to today.
        Returns:
            Optional["Season"]: The created and associated season, or None if an error occurred.
        """
        try:
            from gemini.api.season import Season
            new_season = Season.create(
                season_name=season_name,
                season_info=season_info,
                season_start_date=season_start_date,
                season_end_date=season_end_date,
                experiment_name=self.experiment_name
            )
            if not new_season:
                logger.error("Error creating new season.")
                return None
            return new_season
        except Exception as e:
            logger.error(f"Error creating new season: {e}")
            return None

    # endregion

    # region Population
    def get_associated_populations(self) -> Optional[List["Population"]]:
        """
        Get all populations associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> populations = experiment.get_associated_populations()
            >>> for population in populations:
            ...     print(population)
            Population(population_name=Population A, population_type=breeding, species=Triticum aestivum, id=UUID(...))

        Returns:
            Optional[List["Population"]]: A list of associated populations, or None if not found.
        """
        try:
            from gemini.api.population import Population
            experiment_populations = ExperimentPopulationsViewModel.search(experiment_id=self.id)
            if not experiment_populations or len(experiment_populations) == 0:
                logger.info("No populations found for this experiment.")
                return None
            populations = [Population.model_validate(population) for population in experiment_populations]
            return populations
        except Exception as e:
            logger.error(f"Error getting associated populations: {e}")
            return None

    def create_new_population(
        self,
        population_name: str,
        population_type: str = None,
        species: str = None,
        population_info: dict = None,
    ) -> Optional["Population"]:
        try:
            from gemini.api.population import Population
            new_population = Population.create(
                population_name=population_name,
                population_type=population_type,
                species=species,
                population_info=population_info,
                experiment_name=self.experiment_name,
            )
            if not new_population:
                logger.error("Error creating new population.")
                return None
            return new_population
        except Exception as e:
            logger.error(f"Error creating new population: {e}")
            return None

    def associate_population(self, population_name: str) -> Optional["Population"]:
        try:
            from gemini.api.population import Population
            population = Population.get(population_name=population_name)
            if not population:
                logger.debug("Population not found.")
                return None
            population.associate_experiment(experiment_name=self.experiment_name)
            return population
        except Exception as e:
            logger.error(f"Error associating population: {e}")
            return None

    def unassociate_population(self, population_name: str) -> Optional["Population"]:
        try:
            from gemini.api.population import Population
            population = Population.get(population_name=population_name)
            if not population:
                logger.debug("Population not found.")
                return None
            population.unassociate_experiment(experiment_name=self.experiment_name)
            return population
        except Exception as e:
            logger.error(f"Error unassociating population: {e}")
            return None

    def belongs_to_population(self, population_name: str) -> bool:
        try:
            from gemini.api.population import Population
            population = Population.get(population_name=population_name)
            if not population:
                logger.debug("Population not found.")
                return False
            return population.belongs_to_experiment(experiment_name=self.experiment_name)
        except Exception as e:
            logger.error(f"Error checking if belongs to population: {e}")
            return False

    # endregion

    # region Procedure
    def get_associated_procedures(self) -> Optional[List["Procedure"]]:
        """
        Get all procedures associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> procedures = experiment.get_associated_procedures()
            >>> for procedure in procedures:
            ...     print(procedure)
            Procedure(procedure_name=Procedure 1, id=UUID(...))
            Procedure(procedure_name=Procedure 2, id=UUID(...))

        Returns:
            Optional[List["Procedure"]]: A list of associated procedures, or None if not found.
        """
        try:
            from gemini.api.procedure import Procedure
            experiment_procedures = ExperimentProceduresViewModel.search(experiment_id=self.id)
            if not experiment_procedures or len(experiment_procedures) == 0:
                logger.info("No procedures found for this experiment.")
                return None
            procedures = [Procedure.model_validate(procedure) for procedure in experiment_procedures]
            return procedures
        except Exception as e:
            logger.error(f"Error getting associated procedures: {e}")
            return None
        
    def create_new_procedure(
        self,
        procedure_name: str,
        procedure_info: dict = None
    ) -> Optional["Procedure"]:
        """
        Create and associate a new procedure with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_procedure = experiment.create_new_procedure("Procedure 1", {"description": "Test procedure"})
            >>> print(new_procedure)
            Procedure(procedure_name=Procedure 1, id=UUID(...))

        Args:
            procedure_name (str): The name of the new procedure.
            procedure_info (dict, optional): Additional information about the procedure. Defaults to {{}}.
        Returns:
            Optional["Procedure"]: The created and associated procedure, or None if an error occurred.
        """
        try:
            from gemini.api.procedure import Procedure
            new_procedure = Procedure.create(
                procedure_name=procedure_name,
                procedure_info=procedure_info,
                experiment_name=self.experiment_name
            )
            if not new_procedure:
                logger.error("Error creating new procedure.")
                return None
            return new_procedure
        except Exception as e:
            logger.error(f"Error creating new procedure: {e}")
            return None
        
    def associate_procedure(
        self,
        procedure_name: str,
    ) -> Optional["Procedure"]:
        """
        Associate an existing procedure with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> procedure = experiment.associate_procedure("Procedure 1")
            >>> print(procedure)
            Procedure(procedure_name=Procedure 1, id=UUID(...))

        Args:
            procedure_name (str): The name of the procedure.
        Returns:
            Optional["Procedure"]: The associated procedure, or None if an error occurred.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure = Procedure.get(procedure_name=procedure_name)
            if not procedure:
                logger.debug("Procedure not found.")
                return None
            procedure.associate_experiment(experiment_name=self.experiment_name)
            return procedure
        except Exception as e:
            logger.error(f"Error associating procedure: {e}")
            return None
        
    def unassociate_procedure(
        self,
        procedure_name: str,
    ) -> Optional["Procedure"]:
        """
        Unassociate a procedure from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> procedure = experiment.unassociate_procedure("Procedure 1")
            >>> print(procedure)
            Procedure(procedure_name=Procedure 1, id=UUID(...))

        Args:
            procedure_name (str): The name of the procedure.
        Returns:
            Optional["Procedure"]: The unassociated procedure, or None if an error occurred.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure = Procedure.get(procedure_name=procedure_name)
            if not procedure:
                logger.debug("Procedure not found.")
                return None
            procedure.unassociate_experiment(experiment_name=self.experiment_name)
            return procedure
        except Exception as e:
            logger.error(f"Error unassociating procedure: {e}")
            return None
        
    def belongs_to_procedure(
        self,
        procedure_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific procedure.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_procedure("Procedure 1")
            >>> print(is_associated)
            True

        Args:
            procedure_name (str): The name of the procedure.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.procedure import Procedure
            procedure = Procedure.get(procedure_name=procedure_name)
            if not procedure:
                logger.debug("Procedure not found.")
                return False
            association_exists = procedure.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to procedure: {e}")
            return False
        
    # endregion

    # region Script
    def get_associated_scripts(self) -> Optional[List["Script"]]:
        """
        Get all scripts associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> scripts = experiment.get_associated_scripts()
            >>> for script in scripts:
            ...     print(script)
            Script(script_name=Script 1, script_url='http://example.com/script1', script_extension='.py', id=UUID(...))
            Script(script_name=Script 2, script_url='http://example.com/script2', script_extension='.js', id=UUID(...))

        Returns:
            Optional[List["Script"]]: A list of associated scripts, or None if not found.
        """
        try:
            from gemini.api.script import Script
            experiment_scripts = ExperimentScriptsViewModel.search(experiment_id=self.id)
            if not experiment_scripts or len(experiment_scripts) == 0:
                logger.info("No scripts found for this experiment.")
                return None
            scripts = [Script.model_validate(script) for script in experiment_scripts]
            return scripts
        except Exception as e:
            logger.error(f"Error getting associated scripts: {e}")
            return None
        
    def create_new_script(
        self,
        script_name: str,
        script_extension: str = None,
        script_url: str = None,
        script_info: dict = None
    ) -> Optional["Script"]:
        """
        Create and associate a new script with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_script = experiment.create_new_script("Script 1", script_extension=".py", script_url="http://example.com/script1", script_info={"description": "Test script"})
            >>> print(new_script)
            Script(script_name=Script 1, script_url='http://example.com/script1', script_extension='.py', id=UUID(...))

        Args:
            script_name (str): The name of the new script.
            script_extension (str, optional): The extension of the script. Defaults to None.
            script_url (str, optional): The URL of the script. Defaults to None.
            script_info (dict, optional): Additional information about the script. Defaults to {{}}.
        Returns:
            Optional["Script"]: The created and associated script, or None if an error occurred.
        """
        try:
            from gemini.api.script import Script
            new_script = Script.create(
                script_name=script_name,
                script_url=script_url,
                script_info=script_info,
                script_extension=script_extension,
                experiment_name=self.experiment_name
            )
            if not new_script:
                logger.error("Error creating new script.")
                return None
            return new_script
        except Exception as e:
            logger.error(f"Error creating new script: {e}")
            return None
        
    def associate_script(
        self,
        script_name: str,
    ) -> Optional["Script"]:
        """
        Associate an existing script with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> script = experiment.associate_script("Script 1")
            >>> print(script)
            Script(script_name=Script 1, script_url='http://example.com/script1', script_extension='.py', id=UUID(...))

        Args:
            script_name (str): The name of the script.
        Returns:
            Optional["Script"]: The associated script, or None if an error occurred.
        """
        try:
            from gemini.api.script import Script
            script = Script.get(script_name=script_name)
            if not script:
                logger.debug("Script not found.")
                return None
            script.associate_experiment(experiment_name=self.experiment_name)
            return script
        except Exception as e:
            logger.error(f"Error associating script: {e}")
            return None
        
    def unassociate_script(
        self,
        script_name: str,
    ) -> Optional["Script"]:
        """
        Unassociate a script from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> script = experiment.unassociate_script("Script 1")
            >>> print(script)
            Script(script_name=Script 1, script_url='http://example.com/script1', script_extension='.py', id=UUID(...))

        Args:
            script_name (str): The name of the script.
        Returns:
            Optional["Script"]: The unassociated script, or None if an error occurred.
        """
        try:
            from gemini.api.script import Script
            script = Script.get(script_name=script_name)
            if not script:
                logger.debug("Script not found.")
                return None
            script.unassociate_experiment(experiment_name=self.experiment_name)
            return script
        except Exception as e:
            logger.error(f"Error unassociating script: {e}")
            return None
        
    def belongs_to_script(
        self,
        script_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific script.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_script("Script 1")
            >>> print(is_associated)
            True

        Args:
            script_name (str): The name of the script.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.script import Script
            script = Script.get(script_name=script_name)
            if not script:
                logger.debug("Script not found.")
                return False
            association_exists = script.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to script: {e}")
            return False
    # endregion

    # region Model
    def get_associated_models(self) -> Optional[List["Model"]]:
        """
        Get all models associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> models = experiment.get_associated_models()
            >>> for model in models:
            ...     print(model)
            Model(model_name=Model 1, model_url='http://example.com/model1', id=UUID(...))
            Model(model_name=Model 2, model_url='http://example.com/model2', id=UUID(...))

        Returns:
            Optional[List["Model"]]: A list of associated models, or None if not found.
        """
        try:
            from gemini.api.model import Model
            experiment_models = ExperimentModelsViewModel.search(experiment_id=self.id)
            if not experiment_models or len(experiment_models) == 0:
                logger.info("No models found for this experiment.")
                return None
            models = [Model.model_validate(model) for model in experiment_models]
            return models
        except Exception as e:
            logger.error(f"Error getting associated models: {e}")
            return None
        
    def create_new_model(
        self,
        model_name: str,
        model_url: str = None,
        model_info: dict = None
    ) -> Optional["Model"]:
        """
        Create and associate a new model with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_model = experiment.create_new_model("Model 1", model_url="http://example.com/model1", model_info={"description": "Test model"})
            >>> print(new_model)
            Model(model_name=Model 1, model_url='http://example.com/model1', id=UUID(...))

        Args:
            model_name (str): The name of the new model.
            model_url (str, optional): The URL of the model. Defaults to None.
            model_info (dict, optional): Additional information about the model. Defaults to {{}}.
        Returns:
            Optional["Model"]: The created and associated model, or None if an error occurred.
        """
        try:
            from gemini.api.model import Model
            new_model = Model.create(
                model_name=model_name,
                model_info=model_info,
                model_url=model_url,
                experiment_name=self.experiment_name
            )
            if not new_model:
                logger.error("Error creating new model.")
                return None
            return new_model
        except Exception as e:
            logger.error(f"Error creating new model: {e}")
            return None
        
    def associate_model(
        self,
        model_name: str,
    ) -> Optional["Model"]:
        """
        Associate an existing model with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> model = experiment.associate_model("Model 1")
            >>> print(model)
            Model(model_name=Model 1, model_url='http://example.com/model1', id=UUID(...))

        Args:
            model_name (str): The name of the model.
        Returns:
            Optional["Model"]: The associated model, or None if an error occurred.
        """
        try:
            from gemini.api.model import Model
            model = Model.get(model_name=model_name)
            if not model:
                logger.debug("Model not found.")
                return None
            model.associate_experiment(experiment_name=self.experiment_name)
            return model
        except Exception as e:
            logger.error(f"Error associating model: {e}")
            return None
        
    def unassociate_model(
        self,
        model_name: str,
    ) -> Optional["Model"]:
        """
        Unassociate a model from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> model = experiment.unassociate_model("Model 1")
            >>> print(model)
            Model(model_name=Model 1, model_url='http://example.com/model1', id=UUID(...))

        Args:
            model_name (str): The name of the model.
        Returns:
            Optional["Model"]: The unassociated model, or None if an error occurred.
        """
        try:
            from gemini.api.model import Model
            model = Model.get(model_name=model_name)
            if not model:
                logger.debug("Model not found.")
                return None
            model.unassociate_experiment(experiment_name=self.experiment_name)
            return model
        except Exception as e:
            logger.error(f"Error unassociating model: {e}")
            return None
        
    def belongs_to_model(
        self,
        model_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific model.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_model("Model 1")
            >>> print(is_associated)
            True

        Args:
            model_name (str): The name of the model.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.model import Model
            model = Model.get(model_name=model_name)
            if not model:
                logger.debug("Model not found.")
                return False
            association_exists = model.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to model: {e}")
            return False
    # endregion

    # region Sensor
    def get_associated_sensors(self) -> Optional[List["Sensor"]]:
        """
        Get all sensors associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensors = experiment.get_associated_sensors()
            >>> for sensor in sensors:
            ...     print(sensor)
            Sensor(sensor_name=Sensor 1, id=UUID(...))
            Sensor(sensor_name=Sensor 2, id=UUID(...))

        Returns:
            Optional[List["Sensor"]]: A list of associated sensors, or None if not found.
        """
        try:
            from gemini.api.sensor import Sensor
            experiment_sensors = ExperimentSensorsViewModel.search(experiment_id=self.id)
            if not experiment_sensors or len(experiment_sensors) == 0:
                logger.info("No sensors found for this experiment.")
                return None
            sensors = [Sensor.model_validate(sensor) for sensor in experiment_sensors]
            return sensors
        except Exception as e:
            logger.error(f"Error getting associated sensors: {e}")
            return None
        
    def create_new_sensor(
        self,
        sensor_name: str,
        sensor_type: GEMINISensorType = GEMINISensorType.Default,
        sensor_data_type: GEMINIDataType = GEMINIDataType.Default,
        sensor_data_format: GEMINIDataFormat = GEMINIDataFormat.Default,
        sensor_info: dict = None,
        sensor_platform_name: str = None
    ) -> Optional["Sensor"]:
        """
        Create and associate a new sensor with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_sensor = experiment.create_new_sensor("Sensor 1", sensor_type=GEMINISensorType.RGB, sensor_data_type=GEMINIDataType.Sensor, sensor_data_format=GEMINIDataFormat.Default, sensor_info={"description": "Test sensor"}, sensor_platform_name="Platform 1")
            >>> print(new_sensor)
            Sensor(sensor_name=Sensor 1, id=UUID(...))

        Args:
            sensor_name (str): The name of the new sensor.
            sensor_type (GEMINISensorType, optional): The type of the sensor. Defaults to Default.
            sensor_data_type (GEMINIDataType, optional): The data type. Defaults to Default.
            sensor_data_format (GEMINIDataFormat, optional): The data format. Defaults to Default.
            sensor_info (dict, optional): Additional information about the sensor. Defaults to {{}}.
            sensor_platform_name (str, optional): The name of the sensor platform. Defaults to None.
        Returns:
            Optional["Sensor"]: The created and associated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            new_sensor = Sensor.create(
                sensor_name=sensor_name,
                sensor_type=sensor_type,
                sensor_data_type=sensor_data_type,
                sensor_data_format=sensor_data_format,
                sensor_info=sensor_info,
                experiment_name=self.experiment_name,
                sensor_platform_name=sensor_platform_name
            )
            if not new_sensor:
                logger.error("Error creating new sensor.")
                return None
            return new_sensor
        except Exception as e:
            logger.error(f"Error creating new sensor: {e}")
            return None
        
    def associate_sensor(
        self,
        sensor_name: str,
    ) -> Optional["Sensor"]:
        """
        Associate an existing sensor with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensor = experiment.associate_sensor("Sensor 1")
            >>> print(sensor)
            Sensor(sensor_name=Sensor 1, id=UUID(...))
            
        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            Optional["Sensor"]: The associated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug("Sensor not found.")
                return None
            sensor.associate_experiment(experiment_name=self.experiment_name)
            return sensor
        except Exception as e:
            logger.error(f"Error associating sensor: {e}")
            return None
    
    def unassociate_sensor(
        self,
        sensor_name: str,
    ) -> Optional["Sensor"]:
        """
        Unassociate a sensor from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensor = experiment.unassociate_sensor("Sensor 1")
            >>> print(sensor)
            Sensor(sensor_name=Sensor 1, id=UUID(...))
            
        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            Optional["Sensor"]: The unassociated sensor, or None if an error occurred.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug("Sensor not found.")
                return None
            sensor.unassociate_experiment(experiment_name=self.experiment_name)
            return sensor
        except Exception as e:
            logger.error(f"Error unassociating sensor: {e}")
            return None
        
    def belongs_to_sensor(
        self,
        sensor_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific sensor.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_sensor("Sensor 1")
            >>> print(is_associated)
            True

        Args:
            sensor_name (str): The name of the sensor.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.sensor import Sensor
            sensor = Sensor.get(sensor_name=sensor_name)
            if not sensor:
                logger.debug("Sensor not found.")
                return False
            association_exists = sensor.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to sensor: {e}")
            return False
    # endregion

    # region Sensor Platform
    def get_associated_sensor_platforms(self) -> Optional[List["SensorPlatform"]]:
        """
        Get all sensor platforms associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensor_platforms = experiment.get_associated_sensor_platforms()
            >>> for sensor_platform in sensor_platforms:
            ...     print(sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID(...))
            SensorPlatform(sensor_platform_name=Platform 2, id=UUID(...))

        Returns:
            Optional[List["SensorPlatform"]]: A list of associated sensor platforms, or None if not found.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            experiment_sensor_platforms = ExperimentSensorPlatformsViewModel.search(experiment_id=self.id)
            if not experiment_sensor_platforms or len(experiment_sensor_platforms) == 0:
                logger.info("No sensor platforms found for this experiment.")
                return None
            sensor_platforms = [SensorPlatform.model_validate(sensor_platform) for sensor_platform in experiment_sensor_platforms]
            return sensor_platforms
        except Exception as e:
            logger.error(f"Error getting associated sensor platforms: {e}")
            return None
        
    def create_new_sensor_platform(
        self,
        sensor_platform_name: str,
        sensor_platform_info: dict = None
    ) -> Optional["SensorPlatform"]:
        """
        Create and associate a new sensor platform with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_sensor_platform = experiment.create_new_sensor_platform("Platform 1", {"description": "Test platform"})
            >>> print(new_sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID(...))

        Args:
            sensor_platform_name (str): The name of the new sensor platform.
            sensor_platform_info (dict, optional): Additional information about the sensor platform. Defaults to {{}}.
        Returns:
            Optional["SensorPlatform"]: The created and associated sensor platform, or None if an error occurred.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            new_sensor_platform = SensorPlatform.create(
                sensor_platform_name=sensor_platform_name,
                sensor_platform_info=sensor_platform_info,
                experiment_name=self.experiment_name
            )
            if not new_sensor_platform:
                logger.error("Error creating new sensor platform.")
                return None
            return new_sensor_platform
        except Exception as e:
            logger.error(f"Error creating new sensor platform: {e}")
            return None
        
    def associate_sensor_platform(
        self,
        sensor_platform_name: str,
    ) -> Optional["SensorPlatform"]:
        """
        Associate an existing sensor platform with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensor_platform = experiment.associate_sensor_platform("Platform 1")
            >>> print(sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID(...))

        Args:
            sensor_platform_name (str): The name of the sensor platform.
        Returns:
            Optional["SensorPlatform"]: The associated sensor platform, or None if an error occurred.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.debug("Sensor platform not found.")
                return None
            sensor_platform.associate_experiment(experiment_name=self.experiment_name)
            return sensor_platform
        except Exception as e:
            logger.error(f"Error associating sensor platform: {e}")
            return None
        
    def unassociate_sensor_platform(
        self,
        sensor_platform_name: str,
    ) -> Optional["SensorPlatform"]:
        """
        Unassociate a sensor platform from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sensor_platform = experiment.unassociate_sensor_platform("Platform 1")
            >>> print(sensor_platform)
            SensorPlatform(sensor_platform_name=Platform 1, id=UUID(...))

        Args:
            sensor_platform_name (str): The name of the sensor platform.
        Returns:
            Optional["SensorPlatform"]: The unassociated sensor platform, or None if an error occurred.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.debug("Sensor platform not found.")
                return None
            sensor_platform.unassociate_experiment(experiment_name=self.experiment_name)
            return sensor_platform
        except Exception as e:
            logger.error(f"Error unassociating sensor platform: {e}")
            return None
        
    def belongs_to_sensor_platform(
        self,
        sensor_platform_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific sensor platform.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_sensor_platform("Platform 1")
            >>> print(is_associated)
            True

        Args:
            sensor_platform_name (str): The name of the sensor platform.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.sensor_platform import SensorPlatform
            sensor_platform = SensorPlatform.get(sensor_platform_name=sensor_platform_name)
            if not sensor_platform:
                logger.debug("Sensor platform not found.")
                return False
            association_exists = sensor_platform.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to sensor platform: {e}")
            return False
    # endregion

    # region Site
    def get_associated_sites(self) -> Optional[List["Site"]]:
        """
        Get all sites associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> sites = experiment.get_associated_sites()
            >>> for site in sites:
            ...     print(site)
            Site(site_name=Site 1, id=UUID(...))
            Site(site_name=Site 2, id=UUID(...))

        Returns:
            Optional[List["Site"]]: A list of associated sites, or None if not found.
        """
        try:
            from gemini.api.site import Site
            experiment_sites = ExperimentSitesViewModel.search(experiment_id=self.id)
            if not experiment_sites or len(experiment_sites) == 0:
                logger.info("No sites found for this experiment.")
                return None
            sites = [Site.model_validate(site) for site in experiment_sites]
            return sites
        except Exception as e:
            logger.error(f"Error getting associated sites: {e}")
            return None
        
    def create_new_site(
        self,
        site_name: str,
        site_city: str = None,
        site_state: str = None,
        site_country: str = None,
        site_info: dict = None
    ) -> Optional["Site"]:
        """
        Create and associate a new site with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_site = experiment.create_new_site("Site 1", site_city="City", site_state="State", site_country="Country", site_info={"description": "Test site"})
            >>> print(new_site)
            Site(site_name=Site 1, id=UUID(...))
            
        Args:
            site_name (str): The name of the new site.
            site_city (str, optional): The city of the site. Defaults to None.
            site_state (str, optional): The state of the site. Defaults to None.
            site_country (str, optional): The country of the site. Defaults to None.
            site_info (dict, optional): Additional information about the site. Defaults to {{}}.
        Returns:
            Optional["Site"]: The created and associated site, or None if an error occurred.
        """
        try:
            from gemini.api.site import Site
            new_site = Site.create(
                site_name=site_name,
                site_city=site_city,
                site_state=site_state,
                site_country=site_country,
                site_info=site_info,
                experiment_name=self.experiment_name
            )
            if not new_site:
                logger.error("Error creating new site.")
                return None
            return new_site
        except Exception as e:
            logger.error(f"Error creating new site: {e}")
            return None
        
    def associate_site(
        self,
        site_name: str,
    ) -> Optional["Site"]:
        """
        Associate an existing site with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> site = experiment.associate_site("Site 1")
            >>> print(site)
            Site(site_name=Site 1, id=UUID(...))
            
        Args:
            site_name (str): The name of the site.
        Returns:
            Optional["Site"]: The associated site, or None if an error occurred.
        """
        try:
            from gemini.api.site import Site
            site = Site.get(site_name=site_name)
            if not site:
                logger.debug("Site not found.")
                return None
            site.associate_experiment(experiment_name=self.experiment_name)
            return site
        except Exception as e:
            logger.error(f"Error associating site: {e}")
            return None
        
    def unassociate_site(
        self,
        site_name: str,
    ) -> Optional["Site"]:
        """
        Unassociate a site from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> site = experiment.unassociate_site("Site 1")
            >>> print(site)
            Site(site_name=Site 1, id=UUID(...))
            
        Args:
            site_name (str): The name of the site.
        Returns:
            Optional["Site"]: The unassociated site, or None if an error occurred.
        """
        try:
            from gemini.api.site import Site
            site = Site.get(site_name=site_name)
            if not site:
                logger.debug("Site not found.")
                return None
            site.unassociate_experiment(experiment_name=self.experiment_name)
            return site
        except Exception as e:
            logger.error(f"Error unassociating site: {e}")
            return None
        
    def belongs_to_site(
        self,
        site_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific site.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_site("Site 1")
            >>> print(is_associated)
            True

        Args:
            site_name (str): The name of the site.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.site import Site
            site = Site.get(site_name=site_name)
            if not site:
                logger.debug("Site not found.")
                return False
            association_exists = site.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to site: {e}")
            return False
    # endregion

    # region Dataset
    def get_associated_datasets(self) -> Optional[List["Dataset"]]:
        """
        Get all datasets associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> datasets = experiment.get_associated_datasets()
            >>> for dataset in datasets:
            ...     print(dataset)
            Dataset(dataset_name=Dataset 1, collection_date=date(2023, 10, 1), dataset_type=Default, id=UUID(...))
            Dataset(dataset_name=Dataset 2, collection_date=date(2023, 10, 2), dataset_type=Default, id=UUID(...))

        Returns:
            Optional[List["Dataset"]]: A list of associated datasets, or None if not found.
        """
        try:
            from gemini.api.dataset import Dataset
            experiment_datasets = ExperimentDatasetsViewModel.search(experiment_id=self.id)
            if not experiment_datasets or len(experiment_datasets) == 0:
                logger.info("No datasets found for this experiment.")
                return None
            datasets = [Dataset.model_validate(dataset) for dataset in experiment_datasets]
            return datasets
        except Exception as e:
            logger.error(f"Error getting associated datasets: {e}")
            return None
        
    def create_new_dataset(
        self,
        dataset_name: str,
        dataset_info: dict = None,
        dataset_type: GEMINIDatasetType = GEMINIDatasetType.Default,
        collection_date: date = date.today()
    ) -> Optional["Dataset"]:
        """
        Create and associate a new dataset with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_dataset = experiment.create_new_dataset("Dataset 1", dataset_info={"description": "Test dataset"}, dataset_type=GEMINIDatasetType.Default, collection_date=date.today())
            >>> print(new_dataset)
            Dataset(dataset_name=Dataset 1, collection_date=date(2023, 10, 1), dataset_type=Default, id=UUID(...))


        Args:
            dataset_name (str): The name of the new dataset.
            dataset_info (dict, optional): Additional information about the dataset. Defaults to {{}}.
            dataset_type (GEMINIDatasetType, optional): The type of the dataset. Defaults to Default.
            collection_date (date, optional): The collection date. Defaults to today.
        Returns:
            Optional["Dataset"]: The created and associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            new_dataset = Dataset.create(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                dataset_type=dataset_type,
                collection_date=collection_date,
                experiment_name=self.experiment_name
            )
            if not new_dataset:
                logger.error("Error creating new dataset.")
                return None
            return new_dataset
        except Exception as e:
            logger.error(f"Error creating new dataset: {e}")
            return None
        
    def associate_dataset(
        self,
        dataset_name: str,
    ) -> Optional["Dataset"]:
        """
        Associate an existing dataset with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> dataset = experiment.associate_dataset("Dataset 1")
            >>> print(dataset)
            Dataset(dataset_name=Dataset 1, collection_date=date(2023, 10, 1), dataset_type=Default, id=UUID(...))

        Args:
            dataset_name (str): The name of the dataset.
        Returns:
            Optional["Dataset"]: The associated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name=dataset_name)
            if not dataset:
                logger.debug("Dataset not found.")
                return None
            dataset.associate_experiment(experiment_name=self.experiment_name)
            return dataset
        except Exception as e:
            logger.error(f"Error associating dataset: {e}")
            return None
        
    def unassociate_dataset(
        self,
        dataset_name: str,
    ) -> Optional["Dataset"]:
        """
        Unassociate a dataset from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> dataset = experiment.unassociate_dataset("Dataset 1")
            >>> print(dataset)
            Dataset(dataset_name=Dataset 1, collection_date=date(2023, 10, 1), dataset_type=Default, id=UUID(...))
            
        Args:
            dataset_name (str): The name of the dataset.
        Returns:
            Optional["Dataset"]: The unassociated dataset, or None if an error occurred.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name=dataset_name)
            if not dataset:
                logger.debug("Dataset not found.")
                return None
            dataset.unassociate_experiment(experiment_name=self.experiment_name)
            return dataset
        except Exception as e:
            logger.error(f"Error unassociating dataset: {e}")
            return None
        
    def belongs_to_dataset(
        self,
        dataset_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific dataset.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_dataset("Dataset 1")
            >>> print(is_associated)
            True


        Args:
            dataset_name (str): The name of the dataset.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.dataset import Dataset
            dataset = Dataset.get(dataset_name=dataset_name)
            if not dataset:
                logger.debug("Dataset not found.")
                return False
            association_exists = dataset.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to dataset: {e}")
            return False
        
    # endregion

    # region Trait
    def get_associated_traits(self) -> Optional[List["Trait"]]:
        """
        Get all traits associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> traits = experiment.get_associated_traits()
            >>> for trait in traits:
            ...     print(trait)
            Trait(trait_name=Trait 1, id=UUID(...))
            Trait(trait_name=Trait 2, id=UUID(...))

        Returns:
            Optional[List["Trait"]]: A list of associated traits, or None if not found.
        """
        try:
            from gemini.api.trait import Trait
            experiment_traits = ExperimentTraitsViewModel.search(experiment_id=self.id)
            if not experiment_traits or len(experiment_traits) == 0:
                logger.info("No traits found for this experiment.")
                return None
            traits = [Trait.model_validate(trait) for trait in experiment_traits]
            return traits
        except Exception as e:
            logger.error(f"Error getting associated traits: {e}")
            return None
        
    def create_new_trait(
        self,
        trait_name: str,
        trait_units: str = None,
        trait_metrics: dict = None,
        trait_level: GEMINITraitLevel = GEMINITraitLevel.Default,
        trait_info: dict = None,
    ) -> Optional["Trait"]:
        """
        Create and associate a new trait with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_trait = experiment.create_new_trait("Trait 1", trait_units="kg", trait_metrics={"metric1": 1.0}, trait_level=GEMINITraitLevel.Default, trait_info={"description": "Test trait"})
            >>> print(new_trait)
            Trait(trait_name=Trait 1, id=UUID(...))
            
        Args:
            trait_name (str): The name of the new trait.
            trait_units (str, optional): The units of the trait. Defaults to None.
            trait_metrics (dict, optional): Metrics for the trait. Defaults to {{}}.
            trait_level (GEMINITraitLevel, optional): The level of the trait. Defaults to Default.
            trait_info (dict, optional): Additional information about the trait. Defaults to {{}}.
        Returns:
            Optional["Trait"]: The created and associated trait, or None if an error occurred.
        """
        try:
            from gemini.api.trait import Trait
            new_trait = Trait.create(
                trait_name=trait_name,
                trait_units=trait_units,
                trait_metrics=trait_metrics,
                trait_level=trait_level,
                trait_info=trait_info,
                experiment_name=self.experiment_name
            )
            if not new_trait:
                logger.error("Error creating new trait.")
                return None
            return new_trait
        except Exception as e:
            logger.error(f"Error creating new trait: {e}")
            return None
        
    def associate_trait(
        self,
        trait_name: str,
    ) -> Optional["Trait"]:
        """
        Associate an existing trait with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> trait = experiment.associate_trait("Trait 1")
            >>> print(trait)
            Trait(trait_name=Trait 1, id=UUID(...))
            
        Args:
            trait_name (str): The name of the trait.
        Returns:
            Optional["Trait"]: The associated trait, or None if an error occurred.
        """
        try:
            from gemini.api.trait import Trait
            trait = Trait.get(trait_name=trait_name)
            if not trait:
                logger.debug("Trait not found.")
                return None
            trait.associate_experiment(experiment_name=self.experiment_name)
            return trait
        except Exception as e:
            logger.error(f"Error associating trait: {e}")
            return None
        
    def unassociate_trait(
        self,
        trait_name: str,
    ) -> Optional["Trait"]:
        """
        Unassociate a trait from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> trait = experiment.unassociate_trait("Trait 1")
            >>> print(trait)
            Trait(trait_name=Trait 1, id=UUID(...))
            
        Args:
            trait_name (str): The name of the trait.
        Returns:
            Optional["Trait"]: The unassociated trait, or None if an error occurred.
        """
        try:
            from gemini.api.trait import Trait
            trait = Trait.get(trait_name=trait_name)
            if not trait:
                logger.debug("Trait not found.")
                return None
            trait.unassociate_experiment(experiment_name=self.experiment_name)
            return trait
        except Exception as e:
            logger.error(f"Error unassociating trait: {e}")
            return None
        
    def belongs_to_trait(
        self,
        trait_name: str,
    ) -> bool:
        """
        Check if the experiment is associated with a specific trait.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_trait("Trait 1")
            >>> print(is_associated)
            True

        Args:
            trait_name (str): The name of the trait.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.trait import Trait
            trait = Trait.get(trait_name=trait_name)
            if not trait:
                logger.debug("Trait not found.")
                return False
            association_exists = trait.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to trait: {e}")
            return False
    # endregion

    # region Plot
    
    def get_associated_plots(self) -> Optional[List["Plot"]]:
        """
        Get all plots associated with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> plots = experiment.get_associated_plots()
            >>> for plot in plots:
            ...     print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))
            Plot(plot_number=2, plot_row_number=1, plot_column_number=2, id=UUID(...))


        Returns:
            Optional[List["Plot"]]: A list of associated plots, or None if not found.
        """
        try:
            from gemini.api.plot import Plot
            plots = PlotViewModel.search(experiment_id=self.id)
            if not plots or len(plots) == 0:
                logger.info("No plots found for this experiment.")
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
        season_name: str = None,
        site_name: str = None,
        plot_info: dict = None
    ) -> Optional["Plot"]:
        """
        Create and associate a new plot with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> new_plot = experiment.create_new_plot(1, 1, 1, season_name="Spring", site_name="Site 1", plot_info={"description": "Test plot"})
            >>> print(new_plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
            plot_info (dict, optional): Additional information about the plot. Defaults to {{}}.
        Returns:
            Optional["Plot"]: The created and associated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            new_plot = Plot.create(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                season_name=season_name,
                site_name=site_name,
                plot_info=plot_info,
                experiment_name=self.experiment_name
            )
            if not new_plot:
                logger.error("Error creating new plot.")
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
        season_name: str = None,
        site_name: str = None,
    ) -> Optional["Plot"]:
        """
        Associate an existing plot with this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> plot = experiment.associate_plot(1, 1, 1, season_name="Spring", site_name="Site 1")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
        Returns:
            Optional["Plot"]: The associated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.debug("Plot not found.")
                return None
            plot.associate_experiment(experiment_name=self.experiment_name)
            return plot
        except Exception as e:
            logger.error(f"Error associating plot: {e}")
            return None
        
    def unassociate_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        season_name: str = None,
        site_name: str = None,
    ) -> Optional["Plot"]:
        """
        Unassociate a plot from this experiment.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> plot = experiment.unassociate_plot(1, 1, 1, season_name="Spring", site_name="Site 1")
            >>> print(plot)
            Plot(plot_number=1, plot_row_number=1, plot_column_number=1, id=UUID(...))
            
        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
        Returns:
            Optional["Plot"]: The unassociated plot, or None if an error occurred.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.debug("Plot not found.")
                return None
            plot.unassociate_experiment()
            return plot
        except Exception as e:
            logger.error(f"Error unassociating plot: {e}")
            return None
        
    def belongs_to_plot(
        self,
        plot_number: int,
        plot_row_number: int,
        plot_column_number: int,
        season_name: str = None,
        site_name: str = None,
    ) -> bool:
        """
        Check if the experiment is associated with a specific plot.

        Examples:
            >>> experiment = Experiment.get("My Experiment")
            >>> is_associated = experiment.belongs_to_plot(1, 1, 1, season_name="Spring", site_name="Site 1")
            >>> print(is_associated)
            True

        Args:
            plot_number (int): The plot number.
            plot_row_number (int): The row number of the plot.
            plot_column_number (int): The column number of the plot.
            season_name (str, optional): The season name. Defaults to None.
            site_name (str, optional): The site name. Defaults to None.
        Returns:
            bool: True if associated, False otherwise.
        """
        try:
            from gemini.api.plot import Plot
            plot = Plot.get(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                season_name=season_name,
                site_name=site_name
            )
            if not plot:
                logger.debug("Plot not found.")
                return False
            association_exists = plot.belongs_to_experiment(experiment_name=self.experiment_name)
            return association_exists
        except Exception as e:
            logger.error(f"Error checking if belongs to plot: {e}")
            return False
    # endregion


