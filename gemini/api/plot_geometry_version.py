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


# ── Plot materialization from snapshot ──────────────────────────────────────
#
# The boundary editor saves a versioned snapshot (this module). The
# analyze-page map and the EXTRACT_TRAITS auto-ingest both need a row in
# `plots` for every polygon in the active snapshot — otherwise the
# `trait_records` insert trigger raises on missing parent, and there's no
# place to attach polygon geometry that joins back to trait values.
#
# So whenever a version is saved or activated, we walk the snapshot's
# `boundaries.features`, resolve experiment/season/site by name from the
# directory's path components, and UPSERT a `plots` row per feature with
# `plot_geometry_info` carrying the polygon geometry. Failures here are
# logged but do not fail the save — the snapshot itself is the source of
# truth, and materialization can be retried later via the backfill script.


def _parse_scope_from_directory(directory: str) -> Optional[dict]:
    """Parse `Raw/{year}/{exp}/{loc}/{pop}/...` or `Processed/{year}/...`
    into a (year, experiment_name, location_name, population_name) dict.

    The boundary editor saves under `processedPrefix(scope)` today; older
    code also saves under `rawScopePrefix(scope)`. Both share the first
    five path components (`{Raw|Processed}/{year}/{exp}/{loc}/{pop}`),
    so a directory of either flavor parses uniformly.

    Returns None when the directory is too short to identify a scope —
    e.g. someone is saving a snapshot keyed by a path that doesn't follow
    the workspace convention.
    """
    if not directory:
        return None
    parts = [p for p in directory.split("/") if p]
    if len(parts) < 5:
        return None
    root = parts[0]
    if root not in ("Raw", "Processed"):
        return None
    return {
        "year": parts[1],
        "experiment_name": parts[2],
        "site_name": parts[3],
        "population_name": parts[4],
    }


def _materialize_plots_from_snapshot(
    directory: str, state_snapshot: dict
) -> None:
    """Resolve scope from the directory string, then UPSERT a `plots` row
    for every feature in `state_snapshot.boundaries`.

    Best-effort. Swallows and logs all errors so the calling save/activate
    transaction always commits the snapshot, which is the durable source
    of truth — materialization can be re-run later from the backfill
    script if anything here fails.
    """
    try:
        scope = _parse_scope_from_directory(directory)
        if scope is None:
            logger.debug(
                f"Skipping plot materialization for non-scope directory: {directory!r}"
            )
            return
        boundaries = (state_snapshot or {}).get("boundaries") or state_snapshot or {}
        if not isinstance(boundaries, dict):
            return
        features = boundaries.get("features")
        if not isinstance(features, list) or not features:
            return

        # Resolve experiment/season/site by name. Imports here (not at
        # module top) to avoid circular-import pain: api/plot.py imports
        # are tolerated via TYPE_CHECKING, but the rest of the chain pulls
        # in models that haven't loaded by the time this module is first
        # imported during app startup.
        from gemini.api.experiment import Experiment
        from gemini.api.season import Season
        from gemini.api.site import Site
        from gemini.api.accession import Accession
        from gemini.api.plot import Plot

        exp = Experiment.get(experiment_name=scope["experiment_name"])
        if exp is None or exp.id is None:
            logger.info(
                f"Plot materialization: experiment {scope['experiment_name']!r} not found; skipping."
            )
            return

        # Auto-create the season + site if missing. The directory string was
        # authored by the upload + process tooling, so the year and location
        # path components are the user's chosen season + site names. The
        # import wizard already auto-creates these idempotently on upload;
        # we mirror that here so an EXTRACT_TRAITS-only run isn't gated on
        # a separate "create season" step in the UI.
        sea = Season.get(
            season_name=scope["year"], experiment_name=scope["experiment_name"]
        )
        if sea is None or sea.id is None:
            try:
                Season.create(
                    season_name=scope["year"],
                    experiment_name=scope["experiment_name"],
                )
            except Exception as e:
                logger.info(
                    f"Plot materialization: failed to auto-create season "
                    f"{scope['year']!r} for experiment "
                    f"{scope['experiment_name']!r}: {e}; skipping."
                )
                return
            sea = Season.get(
                season_name=scope["year"],
                experiment_name=scope["experiment_name"],
            )
            if sea is None or sea.id is None:
                logger.info(
                    f"Plot materialization: season {scope['year']!r} still "
                    f"missing after auto-create; skipping."
                )
                return

        sit = Site.get(site_name=scope["site_name"])
        if sit is None or sit.id is None:
            try:
                Site.create(
                    site_name=scope["site_name"],
                    experiment_name=scope["experiment_name"],
                )
            except Exception as e:
                logger.info(
                    f"Plot materialization: failed to auto-create site "
                    f"{scope['site_name']!r}: {e}; skipping."
                )
                return
            sit = Site.get(site_name=scope["site_name"])
            if sit is None or sit.id is None:
                logger.info(
                    f"Plot materialization: site {scope['site_name']!r} still "
                    f"missing after auto-create; skipping."
                )
                return

        # Pre-resolve accession names so we don't issue one SELECT per feature.
        accession_names = set()
        for f in features:
            if not isinstance(f, dict):
                continue
            props = f.get("properties") or {}
            if not isinstance(props, dict):
                continue
            name = (
                props.get("accession_name")
                or props.get("accession")
                or props.get("Accession")
                or props.get("Label")
            )
            if isinstance(name, str) and name:
                accession_names.add(name)
        acc_id_by_name: dict = {}
        if accession_names:
            for name in accession_names:
                try:
                    acc = Accession.get(accession_name=name)
                    if acc is not None and acc.id is not None:
                        acc_id_by_name[name] = acc.id
                except Exception:
                    continue

        ok, upserted, skipped = Plot.upsert_from_features(
            experiment_id=str(exp.id),
            season_id=str(sea.id),
            site_id=str(sit.id),
            features=features,
            accession_id_by_name=acc_id_by_name,
        )
        if not ok:
            logger.warning(
                f"Plot materialization reported failure for {directory!r}; "
                f"upserted={upserted}, skipped={skipped}."
            )
        elif skipped:
            logger.info(
                f"Plot materialization: upserted={upserted}, skipped={skipped} "
                f"for {directory!r} (skipped features missing plot/row/col)."
            )
    except Exception as e:
        logger.error(
            f"Plot materialization failed for {directory!r}: {e}; "
            f"snapshot is still saved — re-run scripts/backfill_plot_geometry.py."
        )


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
                    saved = cls.model_validate(row)
                # Run plot materialization OUTSIDE the snapshot's session so
                # any failure here doesn't roll back the snapshot save (which
                # is the durable record). The helper logs + swallows errors.
                _materialize_plots_from_snapshot(
                    directory, state_snapshot or {}
                )
                return saved
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
                activated = cls.model_validate(target)
                snapshot = target.state_snapshot or {}
            # Materialize plots from the newly-active version's snapshot
            # outside the transaction (same reasoning as save()).
            _materialize_plots_from_snapshot(directory, snapshot)
            return activated
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
