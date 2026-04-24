"""
PlotGeometryVersion API class.

Versioning is scoped by `directory` (the MinIO path the plot_geometry
controller already uses as its key). Saving creates a new version and
auto-activates it; loading can target a specific version or the active
one; deleting removes the row and re-activates the next-most-recent
version if the deleted one was active.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import AliasChoices, Field
from sqlalchemy import desc, func, select, update
from sqlalchemy.exc import IntegrityError

from gemini.api.base import APIBase
from gemini.api.types import ID
from gemini.db.core.base import db_engine
from gemini.db.models.plot_geometry_versions import PlotGeometryVersionModel

logger = logging.getLogger(__name__)


class PlotGeometryVersion(APIBase):
    """A named snapshot of plot-geometry state for a directory."""

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "version_id"))
    directory: str
    version: int
    name: Optional[str] = None
    is_active: bool = False
    state_snapshot: dict = {}
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    # ------------------------------------------------------------------
    # Save / load / list / delete
    # ------------------------------------------------------------------

    @classmethod
    def save(
        cls,
        directory: str,
        state_snapshot: dict,
        name: Optional[str] = None,
        created_by: Optional[str] = None,
        _attempts: int = 3,
    ) -> Optional["PlotGeometryVersion"]:
        """Create a new version for `directory`, auto-activate it, and
        deactivate whatever version was previously active.

        Two concurrent saves for the same directory compute the same
        ``max_version+1`` and race on ``UNIQUE(directory, version)``. On
        IntegrityError we retry up to ``_attempts`` times; each retry
        re-reads the current max and tries a new number.
        """
        last_error: Optional[Exception] = None
        for attempt in range(_attempts):
            try:
                with db_engine.get_session() as session:
                    max_version = session.execute(
                        select(func.max(PlotGeometryVersionModel.version)).where(
                            PlotGeometryVersionModel.directory == directory
                        )
                    ).scalar()
                    next_version = int(max_version or 0) + 1

                    session.execute(
                        update(PlotGeometryVersionModel)
                        .where(PlotGeometryVersionModel.directory == directory)
                        .where(PlotGeometryVersionModel.is_active.is_(True))
                        .values(is_active=False)
                    )

                    row = PlotGeometryVersionModel(
                        directory=directory,
                        version=next_version,
                        name=name,
                        is_active=True,
                        state_snapshot=state_snapshot or {},
                        created_by=created_by,
                    )
                    session.add(row)
                    session.flush()
                    session.refresh(row)
                    return cls.model_validate(row)
            except IntegrityError as e:
                last_error = e
                logger.warning(
                    f"save race on ({directory!r}, v{next_version}); "
                    f"attempt {attempt + 1}/{_attempts}"
                )
                continue
            except Exception as e:
                logger.error(f"Error saving plot-geometry version: {e}")
                return None
        logger.error(
            f"Exhausted retries saving plot-geometry version for {directory!r}: {last_error}"
        )
        return None

    @classmethod
    def list_for_directory(
        cls, directory: str
    ) -> List["PlotGeometryVersion"]:
        try:
            with db_engine.get_session() as session:
                rows = (
                    session.execute(
                        select(PlotGeometryVersionModel)
                        .where(PlotGeometryVersionModel.directory == directory)
                        .order_by(desc(PlotGeometryVersionModel.version))
                    )
                    .scalars()
                    .all()
                )
            return [cls.model_validate(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing plot-geometry versions: {e}")
            return []

    @classmethod
    def load(
        cls, directory: str, version: Optional[int] = None
    ) -> Optional["PlotGeometryVersion"]:
        """Return the named version, or the active version when `version` is None."""
        try:
            query = select(PlotGeometryVersionModel).where(
                PlotGeometryVersionModel.directory == directory
            )
            if version is not None:
                query = query.where(PlotGeometryVersionModel.version == version)
            else:
                query = query.where(PlotGeometryVersionModel.is_active.is_(True))
            with db_engine.get_session() as session:
                row = session.execute(query).scalars().first()
            if row is None:
                return None
            return cls.model_validate(row)
        except Exception as e:
            logger.error(f"Error loading plot-geometry version: {e}")
            return None

    @classmethod
    def activate(
        cls, directory: str, version: int
    ) -> Optional["PlotGeometryVersion"]:
        try:
            with db_engine.get_session() as session:
                target = session.execute(
                    select(PlotGeometryVersionModel)
                    .where(PlotGeometryVersionModel.directory == directory)
                    .where(PlotGeometryVersionModel.version == version)
                ).scalar_one_or_none()
                if target is None:
                    return None
                session.execute(
                    update(PlotGeometryVersionModel)
                    .where(PlotGeometryVersionModel.directory == directory)
                    .where(PlotGeometryVersionModel.is_active.is_(True))
                    .values(is_active=False)
                )
                target.is_active = True
                session.flush()
                session.refresh(target)
                return cls.model_validate(target)
        except Exception as e:
            logger.error(f"Error activating plot-geometry version: {e}")
            return None

    @classmethod
    def delete_version(cls, directory: str, version: int) -> bool:
        """Delete a version; if it was active, activate the next-most-recent remaining version."""
        try:
            with db_engine.get_session() as session:
                target = session.execute(
                    select(PlotGeometryVersionModel)
                    .where(PlotGeometryVersionModel.directory == directory)
                    .where(PlotGeometryVersionModel.version == version)
                ).scalar_one_or_none()
                if target is None:
                    return False
                was_active = target.is_active
                session.delete(target)
                session.flush()

                if was_active:
                    replacement = (
                        session.execute(
                            select(PlotGeometryVersionModel)
                            .where(PlotGeometryVersionModel.directory == directory)
                            .order_by(desc(PlotGeometryVersionModel.version))
                        )
                        .scalars()
                        .first()
                    )
                    if replacement is not None:
                        replacement.is_active = True
                        session.flush()
                return True
        except Exception as e:
            logger.error(f"Error deleting plot-geometry version: {e}")
            return False

    # ------------------------------------------------------------------
    # APIBase lifecycle — satisfied for abstract-method coverage only.
    # ------------------------------------------------------------------

    @classmethod
    def exists(cls, directory: str, version: int) -> bool:
        return cls.load(directory=directory, version=version) is not None

    @classmethod
    def create(cls, **kwargs):  # pragma: no cover — use `save` instead
        return cls.save(**kwargs)

    @classmethod
    def get_by_id(cls, id):  # pragma: no cover — use `load` instead
        try:
            row = PlotGeometryVersionModel.get(id)
            if not row:
                return None
            return cls.model_validate(row)
        except Exception as e:
            logger.error(f"Error getting plot-geometry version by id: {e}")
            return None

    @classmethod
    def get_all(cls, **_):  # pragma: no cover
        return None

    @classmethod
    def get(cls, **_):  # pragma: no cover
        return None

    @classmethod
    def search(cls, **_):  # pragma: no cover
        return None

    def update(self, **_):  # pragma: no cover
        return None

    def delete(self) -> bool:
        return self.__class__.delete_version(self.directory, self.version)

    def refresh(self):  # pragma: no cover
        return self
