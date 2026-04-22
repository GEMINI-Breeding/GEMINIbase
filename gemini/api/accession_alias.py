"""
This module defines the AccessionAlias class, an alternate name (synonym /
field-book shorthand) pointing at a canonical Accession OR Line. Aliases can
be global or scoped to a single experiment.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging

from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.accession_aliases import AccessionAliasModel

logger = logging.getLogger(__name__)


class AccessionAlias(APIBase):

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "accession_alias_id"))

    alias: str
    accession_id: Optional[ID] = None
    line_id: Optional[ID] = None
    scope: str = "global"
    experiment_id: Optional[ID] = None
    source: Optional[str] = None
    alias_info: Optional[dict] = None

    def __str__(self):
        return f"AccessionAlias(alias={self.alias}, scope={self.scope}, id={self.id})"

    def __repr__(self):
        return f"AccessionAlias(alias={self.alias}, scope={self.scope}, id={self.id})"

    @classmethod
    def exists(
        cls,
        alias: str,
        scope: str = "global",
        experiment_id: UUID | str | None = None,
    ) -> bool:
        try:
            kwargs = {"alias": alias, "scope": scope}
            if experiment_id is not None:
                kwargs["experiment_id"] = experiment_id
            return AccessionAliasModel.exists(**kwargs)
        except Exception as e:
            logger.error(f"Error checking existence of alias: {e}")
            return False

    @classmethod
    def create(
        cls,
        alias: str,
        accession_id: UUID | str | None = None,
        line_id: UUID | str | None = None,
        scope: str = "global",
        experiment_id: UUID | str | None = None,
        source: Optional[str] = None,
        alias_info: Optional[dict] = None,
    ) -> Optional["AccessionAlias"]:
        try:
            if (accession_id is None) == (line_id is None):
                logger.warning("Exactly one of accession_id or line_id must be set.")
                return None
            if scope not in ("global", "experiment"):
                logger.warning(f"Invalid scope {scope!r}.")
                return None
            if (scope == "experiment") != (experiment_id is not None):
                logger.warning("experiment_id must be set iff scope='experiment'.")
                return None
            db_instance = AccessionAliasModel.create(
                alias=alias,
                accession_id=accession_id,
                line_id=line_id,
                scope=scope,
                experiment_id=experiment_id,
                source=source,
                alias_info=alias_info if alias_info is not None else {},
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating alias: {e}")
            return None

    @classmethod
    def get(
        cls,
        alias: str,
        scope: str = "global",
        experiment_id: UUID | str | None = None,
    ) -> Optional["AccessionAlias"]:
        try:
            kwargs = {"alias": alias, "scope": scope}
            if experiment_id is not None:
                kwargs["experiment_id"] = experiment_id
            db_instance = AccessionAliasModel.get_by_parameters(**kwargs)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting alias: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["AccessionAlias"]:
        try:
            db_instance = AccessionAliasModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting alias by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["AccessionAlias"]]:
        try:
            rows = AccessionAliasModel.all(limit=limit, offset=offset)
            if not rows:
                return None
            return [cls.model_validate(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting all aliases: {e}")
            return None

    @classmethod
    def search(
        cls,
        alias: Optional[str] = None,
        accession_id: Optional[UUID] = None,
        line_id: Optional[UUID] = None,
        scope: Optional[str] = None,
        experiment_id: Optional[UUID] = None,
    ) -> Optional[List["AccessionAlias"]]:
        try:
            if not any([alias, accession_id, line_id, scope, experiment_id]):
                logger.warning("At least one search parameter must be provided.")
                return None
            rows = AccessionAliasModel.search(
                alias=alias,
                accession_id=accession_id,
                line_id=line_id,
                scope=scope,
                experiment_id=experiment_id,
            )
            if not rows:
                return None
            return [cls.model_validate(r) for r in rows]
        except Exception as e:
            logger.error(f"Error searching aliases: {e}")
            return None

    def update(
        self,
        alias: Optional[str] = None,
        source: Optional[str] = None,
        alias_info: Optional[dict] = None,
    ) -> Optional["AccessionAlias"]:
        try:
            if not any([alias, source, alias_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = AccessionAliasModel.get(self.id)
            if not db_instance:
                return None
            db_instance = AccessionAliasModel.update(
                db_instance, alias=alias, source=source, alias_info=alias_info
            )
            self.refresh()
            return self.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error updating alias: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = AccessionAliasModel.get(self.id)
            if not db_instance:
                return False
            AccessionAliasModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting alias: {e}")
            return False

    def refresh(self) -> Optional["AccessionAlias"]:
        try:
            db_instance = AccessionAliasModel.get(self.id)
            if not db_instance:
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing alias: {e}")
            return None
