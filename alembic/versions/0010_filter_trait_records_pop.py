"""Rebuild ``gemini.filter_trait_records`` with the accession + population columns.

Revision ID: 0010_filter_trait_records_pop
Revises: 0009_trait_records_population
Create Date: 2026-09-21

``TraitRecord.filter()`` reads through the ``gemini.filter_trait_records()``
set-returning function (``SELECT * FROM gemini.filter_trait_records(...)`` in
``TraitRecordModel.filter_records``). That function pins its own ``RETURNS
TABLE`` column list, so any column added to ``gemini.trait_records`` is
invisible to every ``filter()`` caller until the function is rebuilt.

Two revisions added columns and did not rebuild it:

* ``0006`` added ``accession_id`` / ``accession_name`` (it updated the table and
  ``init_sql/scripts/6_init_functions.sql``, but not this function).
* ``0009`` added ``population_id`` / ``population_name`` and repeated the
  omission in both places.

The effect on an **upgraded** database is that ``filter()`` returns every row
with ``accession_name`` NULL. ``TraitRecord.filter()`` wraps its body in
``except Exception``, so nothing surfaces — the caller just sees empty columns.
The multivariate analyses read through ``filter()`` and drop rows with no
accession (``_one_way_panel`` does ``work[work["accession_name"].notna()]``),
so ANOVA / heritability / GGE / MANOVA all report ``insufficient_data`` over
datasets that have complete accession data. Confirmed live: 10,278 records
fetched, ``n_obs 0``, ``n_groups 0``.

A **fresh** database built from init_sql got the ``0006`` half of the fix, so it
returned accession but not population — which is why this never showed up as a
hard failure everywhere. That divergence is the real hazard here; this revision
and the matching init_sql edit put both paths on the same 23-column shape.

``CREATE OR REPLACE FUNCTION`` cannot change a function's result type, so the
function is dropped and recreated. Callers use ``SELECT *``, so no caller needs
to change. Signature (argument list) is unchanged.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0010_filter_trait_records_pop"
down_revision: Union[str, Sequence[str], None] = "0009_trait_records_population"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full 23-column shape: the 19 original columns + accession (0006) +
# population (0009). Mirrors init_sql/scripts/6_init_functions.sql.
FILTER_FN_CURRENT = """
CREATE OR REPLACE FUNCTION gemini.filter_trait_records(
    p_start_timestamp TIMESTAMPTZ DEFAULT NULL,
    p_end_timestamp TIMESTAMPTZ DEFAULT NULL,
    p_experiment_names TEXT[] DEFAULT NULL,
    p_season_names TEXT[] DEFAULT NULL,
    p_site_names TEXT[] DEFAULT NULL,
    p_dataset_names TEXT[] DEFAULT NULL,
    p_trait_names TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    "id" UUID,
    "timestamp" TIMESTAMPTZ,
    "collection_date" DATE,
    "dataset_id" UUID,
    "dataset_name" TEXT,
    "trait_id" UUID,
    "trait_name" TEXT,
    "trait_value" REAL,
    "experiment_id" UUID,
    "experiment_name" TEXT,
    "season_id" UUID,
    "season_name" TEXT,
    "site_id" UUID,
    "site_name" TEXT,
    "plot_id" UUID,
    "plot_number" INTEGER,
    "plot_row_number" INTEGER,
    "plot_column_number" INTEGER,
    "accession_id" UUID,
    "accession_name" TEXT,
    "population_id" UUID,
    "population_name" TEXT,
    "record_info" JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        tr.id,
        tr.timestamp,
        tr.collection_date,
        tr.dataset_id,
        tr.dataset_name,
        tr.trait_id,
        tr.trait_name,
        tr.trait_value,
        tr.experiment_id,
        tr.experiment_name,
        tr.season_id,
        tr.season_name,
        tr.site_id,
        tr.site_name,
        tr.plot_id,
        tr.plot_number,
        tr.plot_row_number,
        tr.plot_column_number,
        tr.accession_id,
        tr.accession_name,
        tr.population_id,
        tr.population_name,
        tr.record_info
    FROM
        gemini.trait_records tr
    WHERE
        (p_start_timestamp IS NULL OR p_end_timestamp IS NULL OR tr.timestamp BETWEEN p_start_timestamp AND p_end_timestamp)
        AND (p_experiment_names IS NULL OR array_length(p_experiment_names, 1) IS NULL OR tr.experiment_name = ANY(p_experiment_names))
        AND (p_season_names IS NULL OR array_length(p_season_names, 1) IS NULL OR tr.season_name = ANY(p_season_names))
        AND (p_site_names IS NULL OR array_length(p_site_names, 1) IS NULL OR tr.site_name = ANY(p_site_names))
        AND (p_dataset_names IS NULL OR array_length(p_dataset_names, 1) IS NULL OR tr.dataset_name = ANY(p_dataset_names))
        AND (p_trait_names IS NULL OR array_length(p_trait_names, 1) IS NULL OR tr.trait_name = ANY(p_trait_names));
END;
$$;
"""

# Pre-revision shape — the 21-column version init_sql carried after 0006
# (accession, no population). downgrade() restores exactly that.
FILTER_FN_PRE = """
CREATE OR REPLACE FUNCTION gemini.filter_trait_records(
    p_start_timestamp TIMESTAMPTZ DEFAULT NULL,
    p_end_timestamp TIMESTAMPTZ DEFAULT NULL,
    p_experiment_names TEXT[] DEFAULT NULL,
    p_season_names TEXT[] DEFAULT NULL,
    p_site_names TEXT[] DEFAULT NULL,
    p_dataset_names TEXT[] DEFAULT NULL,
    p_trait_names TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    "id" UUID,
    "timestamp" TIMESTAMPTZ,
    "collection_date" DATE,
    "dataset_id" UUID,
    "dataset_name" TEXT,
    "trait_id" UUID,
    "trait_name" TEXT,
    "trait_value" REAL,
    "experiment_id" UUID,
    "experiment_name" TEXT,
    "season_id" UUID,
    "season_name" TEXT,
    "site_id" UUID,
    "site_name" TEXT,
    "plot_id" UUID,
    "plot_number" INTEGER,
    "plot_row_number" INTEGER,
    "plot_column_number" INTEGER,
    "accession_id" UUID,
    "accession_name" TEXT,
    "record_info" JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        tr.id,
        tr.timestamp,
        tr.collection_date,
        tr.dataset_id,
        tr.dataset_name,
        tr.trait_id,
        tr.trait_name,
        tr.trait_value,
        tr.experiment_id,
        tr.experiment_name,
        tr.season_id,
        tr.season_name,
        tr.site_id,
        tr.site_name,
        tr.plot_id,
        tr.plot_number,
        tr.plot_row_number,
        tr.plot_column_number,
        tr.accession_id,
        tr.accession_name,
        tr.record_info
    FROM
        gemini.trait_records tr
    WHERE
        (p_start_timestamp IS NULL OR p_end_timestamp IS NULL OR tr.timestamp BETWEEN p_start_timestamp AND p_end_timestamp)
        AND (p_experiment_names IS NULL OR array_length(p_experiment_names, 1) IS NULL OR tr.experiment_name = ANY(p_experiment_names))
        AND (p_season_names IS NULL OR array_length(p_season_names, 1) IS NULL OR tr.season_name = ANY(p_season_names))
        AND (p_site_names IS NULL OR array_length(p_site_names, 1) IS NULL OR tr.site_name = ANY(p_site_names))
        AND (p_dataset_names IS NULL OR array_length(p_dataset_names, 1) IS NULL OR tr.dataset_name = ANY(p_dataset_names))
        AND (p_trait_names IS NULL OR array_length(p_trait_names, 1) IS NULL OR tr.trait_name = ANY(p_trait_names));
END;
$$;
"""

# The argument list is what identifies the function for DROP. It is identical
# on both sides of this revision, so one signature serves upgrade + downgrade.
DROP_FN = """
DROP FUNCTION IF EXISTS gemini.filter_trait_records(
    TIMESTAMPTZ, TIMESTAMPTZ, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
);
"""


def upgrade() -> None:
    # CREATE OR REPLACE cannot widen RETURNS TABLE — must drop first.
    op.execute(DROP_FN)
    op.execute(FILTER_FN_CURRENT)


def downgrade() -> None:
    op.execute(DROP_FN)
    op.execute(FILTER_FN_PRE)
