"""
This module defines the Line class, which represents a breeding line
(pedigree anchor) in the Gemini API.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.lines import LineModel

logger = logging.getLogger(__name__)


class Line(APIBase):

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "line_id"))

    line_name: str
    species: Optional[str] = None
    line_info: Optional[dict] = None

    def __str__(self):
        return f"Line(line_name={self.line_name}, id={self.id})"

    def __repr__(self):
        return f"Line(line_name={self.line_name}, id={self.id})"

    @classmethod
    def exists(cls, line_name: str) -> bool:
        try:
            return LineModel.exists(line_name=line_name)
        except Exception as e:
            logger.error(f"Error checking existence of line: {e}")
            return False

    @classmethod
    def create(
        cls,
        line_name: str,
        species: str = None,
        line_info: dict = None,
    ) -> Optional["Line"]:
        try:
            db_instance = LineModel.get_or_create(
                line_name=line_name,
                species=species,
                line_info=line_info,
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating line: {e}")
            return None

    @classmethod
    def get(cls, line_name: str) -> Optional["Line"]:
        try:
            db_instance = LineModel.get_by_parameters(line_name=line_name)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting line: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Line"]:
        try:
            db_instance = LineModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting line by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Line"]]:
        try:
            lines = LineModel.all(limit=limit, offset=offset)
            if not lines or len(lines) == 0:
                return None
            return [cls.model_validate(l) for l in lines]
        except Exception as e:
            logger.error(f"Error getting all lines: {e}")
            return None

    @classmethod
    def search(
        cls,
        line_name: str = None,
        species: str = None,
        line_info: dict = None,
        include_aliases: bool = False,
        experiment_id: UUID = None,
    ) -> Optional[List["Line"]]:
        try:
            if not any([line_name, species, line_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            lines = LineModel.search(
                line_name=line_name,
                species=species,
                line_info=line_info,
            ) or []
            if include_aliases and line_name:
                from gemini.api.germplasm_resolver import resolve_germplasm
                hit = resolve_germplasm([line_name], experiment_id=experiment_id)
                if hit and hit[0].line_id:
                    existing_ids = {str(l.id) for l in lines}
                    if hit[0].line_id not in existing_ids:
                        extra = LineModel.get(hit[0].line_id)
                        if extra is not None:
                            lines = list(lines) + [extra]
            if not lines:
                return None
            return [cls.model_validate(l) for l in lines]
        except Exception as e:
            logger.error(f"Error searching lines: {e}")
            return None

    def update(self, line_name: str = None, species: str = None, line_info: dict = None) -> Optional["Line"]:
        try:
            if not any([line_name, species, line_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = LineModel.get(self.id)
            if not db_instance:
                return None
            db_instance = LineModel.update(db_instance, line_name=line_name, species=species, line_info=line_info)
            line = self.model_validate(db_instance)
            self.refresh()
            return line
        except Exception as e:
            logger.error(f"Error updating line: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = LineModel.get(self.id)
            if not db_instance:
                return False
            LineModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting line: {e}")
            return False

    def refresh(self) -> Optional["Line"]:
        try:
            db_instance = LineModel.get(self.id)
            if not db_instance:
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing line: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = LineModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.line_info
        except Exception as e:
            logger.error(f"Error getting line info: {e}")
            return None

    def set_info(self, line_info: dict) -> Optional["Line"]:
        try:
            db_instance = LineModel.get(self.id)
            if not db_instance:
                return None
            db_instance = LineModel.update(db_instance, line_info=line_info)
            self.refresh()
            return self.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error setting line info: {e}")
            return None

    def get_associated_accessions(self) -> Optional[List]:
        try:
            from gemini.api.accession import Accession
            from gemini.db.models.accessions import AccessionModel
            db_accessions = AccessionModel.search(line_id=self.id)
            if not db_accessions or len(db_accessions) == 0:
                return None
            return [Accession.model_validate(a) for a in db_accessions]
        except Exception as e:
            logger.error(f"Error getting associated accessions: {e}")
            return None
