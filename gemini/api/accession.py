"""
This module defines the Accession class, which represents a canonical germplasm
unit (globally unique) in the Gemini API.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.associations import PopulationAccessionModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.population import Population
    from gemini.api.line import Line
    from gemini.api.plot import Plot

logger = logging.getLogger(__name__)


class Accession(APIBase):

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "accession_id"))

    accession_name: str
    line_id: Optional[ID] = None
    species: Optional[str] = None
    accession_info: Optional[dict] = None

    def __str__(self):
        return f"Accession(accession_name={self.accession_name}, id={self.id})"

    def __repr__(self):
        return f"Accession(accession_name={self.accession_name}, id={self.id})"

    @classmethod
    def exists(cls, accession_name: str) -> bool:
        try:
            return AccessionModel.exists(accession_name=accession_name)
        except Exception as e:
            logger.error(f"Error checking existence of accession: {e}")
            return False

    @classmethod
    def create(
        cls,
        accession_name: str,
        line_name: str = None,
        species: str = None,
        accession_info: dict = None,
        population_name: str = None,
    ) -> Optional["Accession"]:
        try:
            line_id = None
            if line_name:
                from gemini.api.line import Line
                line = Line.get(line_name=line_name)
                if line:
                    line_id = line.id
            db_instance = AccessionModel.get_or_create(
                accession_name=accession_name,
                line_id=line_id,
                species=species,
                accession_info=accession_info,
            )
            accession = cls.model_validate(db_instance)
            if population_name:
                accession.associate_population(population_name)
            return accession
        except Exception as e:
            logger.error(f"Error creating accession: {e}")
            return None

    @classmethod
    def get(cls, accession_name: str) -> Optional["Accession"]:
        try:
            db_instance = AccessionModel.get_by_parameters(accession_name=accession_name)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting accession: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Accession"]:
        try:
            db_instance = AccessionModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting accession by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Accession"]]:
        try:
            accessions = AccessionModel.all(limit=limit, offset=offset)
            if not accessions or len(accessions) == 0:
                return None
            return [cls.model_validate(a) for a in accessions]
        except Exception as e:
            logger.error(f"Error getting all accessions: {e}")
            return None

    @classmethod
    def search(
        cls,
        accession_name: str = None,
        species: str = None,
        accession_info: dict = None,
        line_id: UUID = None,
        include_aliases: bool = False,
        experiment_id: UUID = None,
    ) -> Optional[List["Accession"]]:
        try:
            if not any([accession_name, species, accession_info, line_id]):
                logger.warning("At least one search parameter must be provided.")
                return None
            accessions = AccessionModel.search(
                accession_name=accession_name,
                species=species,
                accession_info=accession_info,
                line_id=line_id,
            ) or []
            if include_aliases and accession_name:
                from gemini.api.germplasm_resolver import resolve_germplasm
                hit = resolve_germplasm([accession_name], experiment_id=experiment_id)
                if hit and hit[0].accession_id:
                    existing_ids = {str(a.id) for a in accessions}
                    if hit[0].accession_id not in existing_ids:
                        extra = AccessionModel.get(hit[0].accession_id)
                        if extra is not None:
                            accessions = list(accessions) + [extra]
            if not accessions:
                return None
            return [cls.model_validate(a) for a in accessions]
        except Exception as e:
            logger.error(f"Error searching accessions: {e}")
            return None

    def update(self, accession_name: str = None, species: str = None, accession_info: dict = None) -> Optional["Accession"]:
        try:
            if not any([accession_name, species, accession_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return None
            rename = accession_name is not None and accession_name != db_instance.accession_name
            db_instance = AccessionModel.update(db_instance, accession_name=accession_name, species=species, accession_info=accession_info)
            if rename:
                from gemini.api._rename_cascade import cascade_rename
                cascade_rename(self.id, "accession_id", "accession_name", accession_name)
            accession = self.model_validate(db_instance)
            self.refresh()
            return accession
        except Exception as e:
            logger.error(f"Error updating accession: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return False
            AccessionModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting accession: {e}")
            return False

    def refresh(self) -> Optional["Accession"]:
        try:
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing accession: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.accession_info
        except Exception as e:
            logger.error(f"Error getting accession info: {e}")
            return None

    def set_info(self, accession_info: dict) -> Optional["Accession"]:
        try:
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return None
            db_instance = AccessionModel.update(db_instance, accession_info=accession_info)
            self.refresh()
            return self.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error setting accession info: {e}")
            return None

    def associate_population(self, population_name: str) -> Optional["Population"]:
        try:
            from gemini.api.population import Population
            population = Population.get(population_name=population_name)
            if not population:
                logger.warning(f"Population {population_name} does not exist.")
                return None
            existing = PopulationAccessionModel.get_by_parameters(
                population_id=population.id,
                accession_id=self.id,
            )
            if existing:
                return population
            PopulationAccessionModel.get_or_create(
                population_id=population.id,
                accession_id=self.id,
            )
            self.refresh()
            return population
        except Exception as e:
            logger.error(f"Error associating accession with population: {e}")
            return None

    def unassociate_population(self, population_name: str) -> Optional["Population"]:
        try:
            from gemini.api.population import Population
            population = Population.get(population_name=population_name)
            if not population:
                return None
            existing = PopulationAccessionModel.get_by_parameters(
                population_id=population.id,
                accession_id=self.id,
            )
            if not existing:
                return None
            PopulationAccessionModel.delete(existing)
            self.refresh()
            return population
        except Exception as e:
            logger.error(f"Error unassociating accession from population: {e}")
            return None

    def get_associated_populations(self) -> Optional[List["Population"]]:
        try:
            from gemini.api.population import Population
            assocs = PopulationAccessionModel.search(accession_id=self.id)
            if not assocs or len(assocs) == 0:
                return None
            from gemini.db.models.populations import PopulationModel
            populations = []
            for assoc in assocs:
                pop = PopulationModel.get(assoc.population_id)
                if pop:
                    populations.append(Population.model_validate(pop))
            return populations if populations else None
        except Exception as e:
            logger.error(f"Error getting associated populations: {e}")
            return None

    def get_line(self) -> Optional["Line"]:
        try:
            if not self.line_id:
                return None
            from gemini.api.line import Line
            return Line.get_by_id(self.line_id)
        except Exception as e:
            logger.error(f"Error getting line: {e}")
            return None

    def associate_line(self, line_name: str) -> Optional["Line"]:
        try:
            from gemini.api.line import Line
            line = Line.get(line_name=line_name)
            if not line:
                return None
            db_instance = AccessionModel.get(self.id)
            if not db_instance:
                return None
            AccessionModel.update(db_instance, line_id=line.id)
            self.refresh()
            return line
        except Exception as e:
            logger.error(f"Error associating accession with line: {e}")
            return None

    def get_associated_plots(self) -> Optional[List["Plot"]]:
        try:
            from gemini.api.plot import Plot
            from gemini.db.models.views.plot_view import PlotViewModel
            plots = PlotViewModel.search(accession_id=self.id)
            if not plots or len(plots) == 0:
                return None
            return [Plot.model_validate(p) for p in plots]
        except Exception as e:
            logger.error(f"Error getting associated plots: {e}")
            return None
