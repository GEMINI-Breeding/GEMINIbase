"""
ReferenceDataset / ReferencePlot API classes.

Wraps the underlying ORM models with pydantic schemas and exposes the
handful of operations the reference-data upload flow needs: create a
dataset, bulk-insert plot rows, list/filter datasets, fetch plots, and
aggregate trait values.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Iterable, List, Optional, Tuple
from uuid import UUID

from pydantic import AliasChoices, Field
from sqlalchemy import func, select

from gemini.api.base import APIBase
from gemini.api.types import ID
from gemini.db.core.base import db_engine
from gemini.db.models.reference_data import (
    ReferenceDatasetModel,
    ReferencePlotModel,
)

logger = logging.getLogger(__name__)

IDENTITY_FIELDS = {"plot_id", "col", "row", "accession"}


def _plot_count(dataset_id: UUID | str) -> int:
    """Return the number of plots in a dataset; 0 on error."""
    try:
        with db_engine.get_session() as session:
            count = session.execute(
                select(func.count(ReferencePlotModel.id)).where(
                    ReferencePlotModel.dataset_id == dataset_id
                )
            ).scalar_one()
        return int(count or 0)
    except Exception as e:
        logger.error(f"Error counting plots for dataset {dataset_id}: {e}")
        return 0


class ReferenceDataset(APIBase):
    """Dataset-level metadata for a reference-data upload."""

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "dataset_id"))
    name: str
    experiment: Optional[str] = None
    location: Optional[str] = None
    population: Optional[str] = None
    dataset_date: Optional[date] = None
    trait_columns: List[str] = []
    dataset_info: Optional[dict] = None
    created_at: Optional[datetime] = None

    # --- lifecycle ---

    @classmethod
    def exists(cls, name: str) -> bool:
        try:
            return ReferenceDatasetModel.exists(name=name)
        except Exception as e:
            logger.error(f"Error checking reference dataset existence: {e}")
            return False

    @classmethod
    def create(
        cls,
        name: str,
        experiment: Optional[str] = None,
        location: Optional[str] = None,
        population: Optional[str] = None,
        dataset_date: Optional[date] = None,
        trait_columns: Optional[List[str]] = None,
        dataset_info: Optional[dict] = None,
    ) -> Optional["ReferenceDataset"]:
        try:
            db_instance = ReferenceDatasetModel.create(
                name=name,
                experiment=experiment,
                location=location,
                population=population,
                dataset_date=dataset_date,
                trait_columns=list(trait_columns or []),
                dataset_info=dataset_info,
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating reference dataset: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["ReferenceDataset"]:
        try:
            db_instance = ReferenceDatasetModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error retrieving reference dataset by ID: {e}")
            return None

    @classmethod
    def get(cls, name: str) -> Optional["ReferenceDataset"]:
        try:
            db_instance = ReferenceDatasetModel.get_by_parameters(name=name)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error retrieving reference dataset: {e}")
            return None

    @classmethod
    def get_all(
        cls, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Optional[List["ReferenceDataset"]]:
        try:
            rows = ReferenceDatasetModel.all(limit=limit, offset=offset)
            if not rows:
                return None
            return [cls.model_validate(r) for r in rows]
        except Exception as e:
            logger.error(f"Error retrieving all reference datasets: {e}")
            return None

    @classmethod
    def search(
        cls,
        name: Optional[str] = None,
        experiment: Optional[str] = None,
        location: Optional[str] = None,
        population: Optional[str] = None,
    ) -> Optional[List["ReferenceDataset"]]:
        try:
            if not any([name, experiment, location, population]):
                return cls.get_all()
            kwargs = {}
            if name is not None:
                kwargs["name"] = name
            if experiment is not None:
                kwargs["experiment"] = experiment
            if location is not None:
                kwargs["location"] = location
            if population is not None:
                kwargs["population"] = population
            rows = ReferenceDatasetModel.search(**kwargs)
            if not rows:
                return None
            return [cls.model_validate(r) for r in rows]
        except Exception as e:
            logger.error(f"Error searching reference datasets: {e}")
            return None

    def update(
        self,
        name: Optional[str] = None,
        experiment: Optional[str] = None,
        location: Optional[str] = None,
        population: Optional[str] = None,
        dataset_date: Optional[date] = None,
        trait_columns: Optional[List[str]] = None,
        dataset_info: Optional[dict] = None,
    ) -> Optional["ReferenceDataset"]:
        try:
            db_instance = ReferenceDatasetModel.get(self.id)
            if not db_instance:
                return None
            kwargs: dict = {}
            if name is not None:
                kwargs["name"] = name
            if experiment is not None:
                kwargs["experiment"] = experiment
            if location is not None:
                kwargs["location"] = location
            if population is not None:
                kwargs["population"] = population
            if dataset_date is not None:
                kwargs["dataset_date"] = dataset_date
            if trait_columns is not None:
                kwargs["trait_columns"] = list(trait_columns)
            if dataset_info is not None:
                kwargs["dataset_info"] = dataset_info
            if not kwargs:
                return self
            db_instance = ReferenceDatasetModel.update(db_instance, **kwargs)
            updated = self.model_validate(db_instance)
            self.refresh()
            return updated
        except Exception as e:
            logger.error(f"Error updating reference dataset: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = ReferenceDatasetModel.get(self.id)
            if not db_instance:
                return False
            ReferenceDatasetModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting reference dataset: {e}")
            return False

    def refresh(self) -> Optional["ReferenceDataset"]:
        try:
            db_instance = ReferenceDatasetModel.get(self.id)
            if not db_instance:
                return self
            fresh = self.model_validate(db_instance)
            for key, value in fresh.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing reference dataset: {e}")
            return None

    # --- plot operations ---

    def plot_count(self) -> int:
        return _plot_count(self.id)

    def insert_plots(self, rows: Iterable[dict]) -> int:
        """Bulk-insert plot rows. Returns number of rows inserted."""
        try:
            with db_engine.get_session() as session:
                inserted = 0
                batch: List[ReferencePlotModel] = []
                for row in rows:
                    batch.append(
                        ReferencePlotModel(
                            dataset_id=self.id,
                            plot_id=row.get("plot_id"),
                            plot_column=row.get("col"),
                            plot_row=row.get("row"),
                            accession=row.get("accession"),
                            traits=row.get("traits") or {},
                        )
                    )
                    inserted += 1
                session.add_all(batch)
            return inserted
        except Exception as e:
            logger.error(f"Error inserting plots into dataset {self.id}: {e}")
            return 0

    def get_plots(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[dict]:
        try:
            query = (
                select(ReferencePlotModel)
                .where(ReferencePlotModel.dataset_id == self.id)
                .order_by(ReferencePlotModel.created_at)
            )
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            with db_engine.get_session() as session:
                result = session.execute(query).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "dataset_id": str(r.dataset_id),
                    "plot_id": r.plot_id,
                    "plot_column": r.plot_column,
                    "plot_row": r.plot_row,
                    "accession": r.accession,
                    "traits": r.traits,
                }
                for r in result
            ]
        except Exception as e:
            logger.error(f"Error fetching plots for dataset {self.id}: {e}")
            return []

    def aggregate_metric(
        self, metric: str, aggregation: str = "avg"
    ) -> Tuple[Optional[float], int]:
        """Apply avg/min/max/sum/count to a trait column across all plots.

        Returns (value, count_of_non_null_rows).
        """
        aggregation = (aggregation or "avg").lower()
        if aggregation not in {"avg", "min", "max", "sum", "count"}:
            raise ValueError(f"Unsupported aggregation: {aggregation}")
        try:
            trait_expr = ReferencePlotModel.traits[metric].astext.cast(
                __import__("sqlalchemy").Float
            )
            agg_fns = {
                "avg": func.avg,
                "min": func.min,
                "max": func.max,
                "sum": func.sum,
                "count": func.count,
            }
            agg_fn = agg_fns[aggregation]
            query = (
                select(agg_fn(trait_expr), func.count(trait_expr))
                .where(ReferencePlotModel.dataset_id == self.id)
                .where(trait_expr.isnot(None))
            )
            with db_engine.get_session() as session:
                value, count = session.execute(query).one()
            return (
                float(value) if value is not None else None,
                int(count or 0),
            )
        except Exception as e:
            logger.error(
                f"Error aggregating metric {metric}/{aggregation} on dataset {self.id}: {e}"
            )
            return (None, 0)
