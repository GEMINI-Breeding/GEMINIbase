"""
This module defines the Population class, which represents a named germplasm
grouping (e.g. a diversity panel, RIL population) in the Gemini API.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.populations import PopulationModel
from gemini.db.models.associations import ExperimentPopulationModel, PopulationAccessionModel
from gemini.db.models.views.experiment_views import ExperimentPopulationsViewModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment
    from gemini.api.accession import Accession

logger = logging.getLogger(__name__)

class Population(APIBase):

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "population_id"))

    population_name: str
    population_type: Optional[str] = None
    species: Optional[str] = None
    population_info: Optional[dict] = None

    def __str__(self):
        return f"Population(population_name={self.population_name}, id={self.id})"

    def __repr__(self):
        return f"Population(population_name={self.population_name}, id={self.id})"

    @classmethod
    def exists(
        cls,
        population_name: str,
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
            population_name (str): The accession number of the population.

        Returns:
            bool: True if the population exists, False otherwise.
        """
        try:
            return PopulationModel.exists(population_name=population_name)
        except Exception as e:
            logger.error(f"Error checking the existence of population: {e}")
            return False

    @classmethod
    def create(
        cls,
        population_name: str,
        population_type: str = None,
        species: str = None,
        population_info: dict = None,
        experiment_name: str = None,
    ) -> Optional["Population"]:
        """
        Create a new population. If the population already exists, it will return the existing one.

        Examples:
            >>> population = Population.create("Wheat", "Accession123")
            >>> print(population)
            Population(population_name=Wheat, population_name=Accession123, id=UUID(...))

            >>> population = Population.create("Corn", "Accession456", {"info": "test"}, "Experiment1")
            >>> print(population)
            Population(population_name=Corn, population_name=Accession456, id=UUID(...))

        Args:
            population_name (str): The population of the population.
            population_name (str): The accession number of the population.
            population_info (dict, optional): Additional information about the population. Defaults to {}.
            experiment_name (str, optional): The name of the experiment to associate the population with. Defaults to None.

        Returns:
            Optional["Population"]: The created population, or None if an error occurred.
        """
        try:
            db_instance = PopulationModel.get_or_create(
                population_name=population_name,
                population_type=population_type,
                species=species,
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
    def get(cls, population_name: str, experiment_name: str = None) -> Optional["Population"]:
        try:
            db_instance = ExperimentPopulationsViewModel.get_by_parameters(
                population_name=population_name,
                experiment_name=experiment_name,
            )
            if not db_instance:
                logger.debug(f"Population with name {population_name} not found.")
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
            Population(population_name=Wheat, population_name=Accession123, id=UUID(...))

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
            Population(population_name=Wheat, population_name=Accession123, id=UUID(...))
            Population(population_name=Corn, population_name=Accession456, id=UUID(...))


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
        population_type: str = None,
        species: str = None,
        population_info: dict = None,
        experiment_name: str = None,
    ) -> Optional[List["Population"]]:
        try:
            if not any([experiment_name, population_name, population_type, species, population_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            populations = ExperimentPopulationsViewModel.search(
                experiment_name=experiment_name,
                population_name=population_name,
                population_type=population_type,
                species=species,
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
        population_name: str = None,
        population_type: str = None,
        species: str = None,
        population_info: dict = None,
    ) -> Optional["Population"]:
        try:
            if not any([population_name, population_type, species, population_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            current_id = self.id
            population = PopulationModel.get(current_id)
            if not population:
                logger.warning(f"Population with ID {current_id} does not exist.")
                return None
            population = PopulationModel.update(
                population,
                population_name=population_name,
                population_type=population_type,
                species=species,
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
            Population(population_name=Wheat, population_name=Accession123, id=UUID(...))

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

    def get_associated_accessions(self) -> Optional[List["Accession"]]:
        try:
            from gemini.api.accession import Accession
            from gemini.db.models.accessions import AccessionModel
            assocs = PopulationAccessionModel.search(population_id=self.id)
            if not assocs or len(assocs) == 0:
                return None
            accessions = []
            for assoc in assocs:
                acc = AccessionModel.get(assoc.accession_id)
                if acc:
                    accessions.append(Accession.model_validate(acc))
            return accessions if accessions else None
        except Exception as e:
            logger.error(f"Error getting associated accessions: {e}")
            return None

    def associate_accession(self, accession_name: str) -> Optional["Accession"]:
        try:
            from gemini.api.accession import Accession
            accession = Accession.get(accession_name=accession_name)
            if not accession:
                logger.warning(f"Accession {accession_name} does not exist.")
                return None
            existing = PopulationAccessionModel.get_by_parameters(
                population_id=self.id,
                accession_id=accession.id,
            )
            if existing:
                return accession
            PopulationAccessionModel.get_or_create(
                population_id=self.id,
                accession_id=accession.id,
            )
            self.refresh()
            return accession
        except Exception as e:
            logger.error(f"Error associating population with accession: {e}")
            return None

    def unassociate_accession(self, accession_name: str) -> Optional["Accession"]:
        try:
            from gemini.api.accession import Accession
            accession = Accession.get(accession_name=accession_name)
            if not accession:
                return None
            existing = PopulationAccessionModel.get_by_parameters(
                population_id=self.id,
                accession_id=accession.id,
            )
            if not existing:
                return None
            PopulationAccessionModel.delete(existing)
            self.refresh()
            return accession
        except Exception as e:
            logger.error(f"Error unassociating population from accession: {e}")
            return None
