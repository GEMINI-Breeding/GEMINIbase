"""Plot numbers become text: a field's plot identifier is kept as it is.

Revision ID: 0012_plot_number_text
Revises: 0011_process_entities
Create Date: 2026-11-13

Fields name some plots with letters — check plots ``KW1``…``KW20`` among
numbered ones, ``B12`` and the like. ``plot_number`` was INTEGER on
``plots``, ``trait_records`` and ``sensor_records``, so such plots were
dropped when boundaries were saved and when traits were stored. It is now
TEXT everywhere; existing numbers keep their digits ("101").

Text compares as text, so readers that order plots sort them naturally
(numbers first by value) in Python/TypeScript rather than in SQL.

What changes:

1. The views that select ``plots.plot_number`` (site_plot_view,
   plot_view, plot_accession_view) and the pg_ivm IMMVs over the two
   record tables are dropped, as ALTER TYPE refuses columns that views
   use and pg_ivm does not follow ALTER TABLE.
2. ``plot_number`` becomes TEXT on the three tables (the unique
   constraints are rebuilt by ALTER TYPE).
3. ``create_plot_if_not_exists`` / ``check_plot_validity`` take a text
   plot number; ``filter_*_records`` return one.
4. The views and IMMVs (with 0006/0009's IMMV indexes) are recreated.

Downgrade casts back to INTEGER and fails if any plot identifier is not
a whole number.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_plot_number_text"
down_revision: Union[str, Sequence[str], None] = "0011_process_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("plots", "trait_records", "sensor_records")

DROP_FUNCTIONS = """
DROP FUNCTION IF EXISTS gemini.check_plot_validity(text, text, text, {t}, integer, integer);
DROP FUNCTION IF EXISTS gemini.create_plot_if_not_exists(text, text, text, {t}, integer, integer);
DROP FUNCTION IF EXISTS gemini.filter_sensor_records(timestamptz, timestamptz, text[], text[], text[], text[], text[]);
DROP FUNCTION IF EXISTS gemini.filter_trait_records(timestamptz, timestamptz, text[], text[], text[], text[], text[]);
"""

DROP_VIEWS = """
DROP VIEW IF EXISTS gemini.plot_accession_view;
DROP VIEW IF EXISTS gemini.plot_view;
DROP VIEW IF EXISTS gemini.site_plot_view;
"""

VIEWS = """
CREATE VIEW gemini.site_plot_view AS
SELECT s.site_name, p.id AS plot_id, p.plot_number, p.plot_row_number,
       p.plot_column_number, p.plot_geometry_info, p.plot_info
FROM gemini.sites AS s
JOIN gemini.plots AS p ON s.id = p.site_id;

CREATE VIEW gemini.plot_view AS
SELECT p.id AS plot_id, e.id AS experiment_id, e.experiment_name,
       s.id AS season_id, s.season_name, si.id AS site_id, si.site_name,
       a.id AS accession_id, a.accession_name,
       pop.id AS population_id, pop.population_name,
       p.plot_number, p.plot_row_number, p.plot_column_number,
       p.plot_geometry_info, p.plot_info
FROM gemini.plots p
LEFT JOIN gemini.experiments e ON p.experiment_id = e.id
LEFT JOIN gemini.seasons s ON p.season_id = s.id
LEFT JOIN gemini.sites si ON p.site_id = si.id
LEFT JOIN gemini.accessions a ON p.accession_id = a.id
LEFT JOIN gemini.populations pop ON p.population_id = pop.id;

CREATE VIEW gemini.plot_accession_view AS
SELECT pv.plot_id, pv.plot_number, pv.plot_row_number, pv.plot_column_number,
       pv.plot_info, pv.plot_geometry_info, pv.experiment_id, pv.experiment_name,
       pv.season_id, pv.season_name, pv.site_id, pv.site_name,
       a.id AS accession_id, a.accession_name, a.accession_info,
       pop.id AS population_id, pop.population_name, pop.population_info
FROM gemini.plot_view pv
LEFT JOIN gemini.accessions a ON pv.accession_id = a.id
LEFT JOIN gemini.populations pop ON pv.population_id = pop.id;
"""

FUNCTIONS_TEXT = r"""
CREATE OR REPLACE FUNCTION gemini.create_plot_if_not_exists(exp_name text, sea_name text, sit_name text, plt_num text, plt_row_num integer, plt_col_num integer)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    exp_id UUID;
    sea_id UUID;
    sit_id UUID;
    pl_id UUID;
BEGIN
    -- Check if the experiment exists
    SELECT id INTO exp_id FROM gemini.experiments WHERE experiment_name = exp_name;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Experiment % does not exist', exp_name;
    END IF;

    -- Check if the season exists for the experiment
    SELECT id INTO sea_id FROM gemini.seasons WHERE season_name = sea_name AND experiment_id = exp_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Season % does not exist for experiment %', sea_name, exp_name;
    END IF;

    -- Check if the site exists
    SELECT id INTO sit_id FROM gemini.sites WHERE site_name = sit_name;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Site % does not exist', sit_name;
    END IF;

    -- Check if the plot already exists
    SELECT id INTO pl_id FROM gemini.plots 
    WHERE experiment_id = exp_id 
      AND season_id = sea_id 
      AND site_id = sit_id 
      AND plot_number = plt_num
      AND plot_row_number = plt_row_num
      AND plot_column_number = plt_col_num;

    IF NOT FOUND THEN
        -- If not, create a new plot
        INSERT INTO gemini.plots (experiment_id, season_id, site_id, plot_number, plot_row_number, plot_column_number)
        VALUES (exp_id, sea_id, sit_id, plt_num, plt_row_num, plt_col_num)
        RETURNING id INTO pl_id;
    END IF;

    -- Return the plot ID
    RETURN pl_id;
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.check_plot_validity(exp_name text, sea_name text, sit_name text, plt_num text, plt_row_num integer, plt_col_num integer)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Check if the combination of valid_plot_combinations_view exists
    IF EXISTS (
        SELECT 1
        FROM gemini.valid_plot_combinations_view vpc
        WHERE vpc.experiment_name = exp_name
          AND vpc.season_name = sea_name
          AND vpc.site_name = sit_name
    ) THEN
        PERFORM gemini.create_plot_if_not_exists(exp_name, sea_name, sit_name, plt_num, plt_row_num, plt_col_num);
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.filter_sensor_records(p_start_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_end_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_experiment_names text[] DEFAULT NULL::text[], p_season_names text[] DEFAULT NULL::text[], p_site_names text[] DEFAULT NULL::text[], p_dataset_names text[] DEFAULT NULL::text[], p_sensor_names text[] DEFAULT NULL::text[])
 RETURNS TABLE(id uuid, "timestamp" timestamp with time zone, collection_date date, dataset_id uuid, dataset_name text, sensor_id uuid, sensor_name text, sensor_data jsonb, experiment_id uuid, experiment_name text, season_id uuid, season_name text, site_id uuid, site_name text, plot_id uuid, plot_number text, plot_row_number integer, plot_column_number integer, record_file text, record_info jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        sr.id,
        sr.timestamp,
        sr.collection_date,
        sr.dataset_id,
        sr.dataset_name,
        sr.sensor_id,
        sr.sensor_name,
        sr.sensor_data,
        sr.experiment_id,
        sr.experiment_name,
        sr.season_id,
        sr.season_name,
        sr.site_id,
        sr.site_name,
        sr.plot_id,
        sr.plot_number,
        sr.plot_row_number,
        sr.plot_column_number,
        sr.record_file,
        sr.record_info
    FROM
        gemini.sensor_records sr
    WHERE
        (p_start_timestamp IS NULL OR p_end_timestamp IS NULL OR sr.timestamp BETWEEN p_start_timestamp AND p_end_timestamp)
        AND (p_experiment_names IS NULL OR array_length(p_experiment_names, 1) IS NULL OR sr.experiment_name = ANY(p_experiment_names))
        AND (p_season_names IS NULL OR array_length(p_season_names, 1) IS NULL OR sr.season_name = ANY(p_season_names))
        AND (p_site_names IS NULL OR array_length(p_site_names, 1) IS NULL OR sr.site_name = ANY(p_site_names))
        AND (p_dataset_names IS NULL OR array_length(p_dataset_names, 1) IS NULL OR sr.dataset_name = ANY(p_dataset_names))
        AND (p_sensor_names IS NULL OR array_length(p_sensor_names, 1) IS NULL OR sr.sensor_name = ANY(p_sensor_names));
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.filter_trait_records(p_start_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_end_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_experiment_names text[] DEFAULT NULL::text[], p_season_names text[] DEFAULT NULL::text[], p_site_names text[] DEFAULT NULL::text[], p_dataset_names text[] DEFAULT NULL::text[], p_trait_names text[] DEFAULT NULL::text[])
 RETURNS TABLE(id uuid, "timestamp" timestamp with time zone, collection_date date, dataset_id uuid, dataset_name text, trait_id uuid, trait_name text, trait_value real, experiment_id uuid, experiment_name text, season_id uuid, season_name text, site_id uuid, site_name text, plot_id uuid, plot_number text, plot_row_number integer, plot_column_number integer, accession_id uuid, accession_name text, population_id uuid, population_name text, record_info jsonb)
 LANGUAGE plpgsql
AS $function$
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
$function$;
"""

FUNCTIONS_INTEGER = r"""
CREATE OR REPLACE FUNCTION gemini.create_plot_if_not_exists(exp_name text, sea_name text, sit_name text, plt_num integer, plt_row_num integer, plt_col_num integer)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    exp_id UUID;
    sea_id UUID;
    sit_id UUID;
    pl_id UUID;
BEGIN
    -- Check if the experiment exists
    SELECT id INTO exp_id FROM gemini.experiments WHERE experiment_name = exp_name;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Experiment % does not exist', exp_name;
    END IF;

    -- Check if the season exists for the experiment
    SELECT id INTO sea_id FROM gemini.seasons WHERE season_name = sea_name AND experiment_id = exp_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Season % does not exist for experiment %', sea_name, exp_name;
    END IF;

    -- Check if the site exists
    SELECT id INTO sit_id FROM gemini.sites WHERE site_name = sit_name;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Site % does not exist', sit_name;
    END IF;

    -- Check if the plot already exists
    SELECT id INTO pl_id FROM gemini.plots 
    WHERE experiment_id = exp_id 
      AND season_id = sea_id 
      AND site_id = sit_id 
      AND plot_number = plt_num
      AND plot_row_number = plt_row_num
      AND plot_column_number = plt_col_num;

    IF NOT FOUND THEN
        -- If not, create a new plot
        INSERT INTO gemini.plots (experiment_id, season_id, site_id, plot_number, plot_row_number, plot_column_number)
        VALUES (exp_id, sea_id, sit_id, plt_num, plt_row_num, plt_col_num)
        RETURNING id INTO pl_id;
    END IF;

    -- Return the plot ID
    RETURN pl_id;
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.check_plot_validity(exp_name text, sea_name text, sit_name text, plt_num integer, plt_row_num integer, plt_col_num integer)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Check if the combination of valid_plot_combinations_view exists
    IF EXISTS (
        SELECT 1
        FROM gemini.valid_plot_combinations_view vpc
        WHERE vpc.experiment_name = exp_name
          AND vpc.season_name = sea_name
          AND vpc.site_name = sit_name
    ) THEN
        PERFORM gemini.create_plot_if_not_exists(exp_name, sea_name, sit_name, plt_num, plt_row_num, plt_col_num);
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.filter_sensor_records(p_start_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_end_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_experiment_names text[] DEFAULT NULL::text[], p_season_names text[] DEFAULT NULL::text[], p_site_names text[] DEFAULT NULL::text[], p_dataset_names text[] DEFAULT NULL::text[], p_sensor_names text[] DEFAULT NULL::text[])
 RETURNS TABLE(id uuid, "timestamp" timestamp with time zone, collection_date date, dataset_id uuid, dataset_name text, sensor_id uuid, sensor_name text, sensor_data jsonb, experiment_id uuid, experiment_name text, season_id uuid, season_name text, site_id uuid, site_name text, plot_id uuid, plot_number integer, plot_row_number integer, plot_column_number integer, record_file text, record_info jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        sr.id,
        sr.timestamp,
        sr.collection_date,
        sr.dataset_id,
        sr.dataset_name,
        sr.sensor_id,
        sr.sensor_name,
        sr.sensor_data,
        sr.experiment_id,
        sr.experiment_name,
        sr.season_id,
        sr.season_name,
        sr.site_id,
        sr.site_name,
        sr.plot_id,
        sr.plot_number,
        sr.plot_row_number,
        sr.plot_column_number,
        sr.record_file,
        sr.record_info
    FROM
        gemini.sensor_records sr
    WHERE
        (p_start_timestamp IS NULL OR p_end_timestamp IS NULL OR sr.timestamp BETWEEN p_start_timestamp AND p_end_timestamp)
        AND (p_experiment_names IS NULL OR array_length(p_experiment_names, 1) IS NULL OR sr.experiment_name = ANY(p_experiment_names))
        AND (p_season_names IS NULL OR array_length(p_season_names, 1) IS NULL OR sr.season_name = ANY(p_season_names))
        AND (p_site_names IS NULL OR array_length(p_site_names, 1) IS NULL OR sr.site_name = ANY(p_site_names))
        AND (p_dataset_names IS NULL OR array_length(p_dataset_names, 1) IS NULL OR sr.dataset_name = ANY(p_dataset_names))
        AND (p_sensor_names IS NULL OR array_length(p_sensor_names, 1) IS NULL OR sr.sensor_name = ANY(p_sensor_names));
END;
$function$;

CREATE OR REPLACE FUNCTION gemini.filter_trait_records(p_start_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_end_timestamp timestamp with time zone DEFAULT NULL::timestamp with time zone, p_experiment_names text[] DEFAULT NULL::text[], p_season_names text[] DEFAULT NULL::text[], p_site_names text[] DEFAULT NULL::text[], p_dataset_names text[] DEFAULT NULL::text[], p_trait_names text[] DEFAULT NULL::text[])
 RETURNS TABLE(id uuid, "timestamp" timestamp with time zone, collection_date date, dataset_id uuid, dataset_name text, trait_id uuid, trait_name text, trait_value real, experiment_id uuid, experiment_name text, season_id uuid, season_name text, site_id uuid, site_name text, plot_id uuid, plot_number integer, plot_row_number integer, plot_column_number integer, accession_id uuid, accession_name text, population_id uuid, population_name text, record_info jsonb)
 LANGUAGE plpgsql
AS $function$
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
$function$;
"""


def _drop_immvs(bind) -> None:
    # Outside alembic's transaction: dropping an IMMV inside a wrapped
    # transaction segfaults the backend during pg_ivm teardown (see 0006).
    bind.execute(sa.text("COMMIT"))
    for t in ("trait_records_immv", "sensor_records_immv"):
        bind.execute(sa.text(f"DROP TABLE IF EXISTS gemini.{t} CASCADE"))
    bind.execute(sa.text("BEGIN"))


def _create_immvs(bind) -> None:
    bind.execute(sa.text("COMMIT"))
    for t in ("sensor_records", "trait_records"):
        bind.execute(sa.text(
            f"SELECT pgivm.create_immv('gemini.{t}_immv', 'select * from gemini.{t}')"))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_trait_records_immv_accession_id "
        "ON gemini.trait_records_immv (accession_id)"))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_trait_records_immv_population_id "
        "ON gemini.trait_records_immv (population_id)"))
    bind.execute(sa.text("BEGIN"))


def _change(to_type: str, using: str, from_type: str, functions: str) -> None:
    bind = op.get_bind()
    _drop_immvs(bind)
    op.execute(DROP_VIEWS)
    op.execute(DROP_FUNCTIONS.replace("{t}", from_type))
    for t in TABLES:
        op.execute(f"ALTER TABLE gemini.{t} ALTER COLUMN plot_number TYPE {to_type} USING {using}")
    op.execute(functions)
    op.execute(VIEWS)
    _create_immvs(bind)


def upgrade() -> None:
    _change("TEXT", "plot_number::text", "integer", FUNCTIONS_TEXT)


def downgrade() -> None:
    _change("INTEGER", "plot_number::integer", "text", FUNCTIONS_INTEGER)
