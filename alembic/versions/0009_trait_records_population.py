"""Add ``population_id`` / ``population_name`` to ``gemini.trait_records``.

Revision ID: 0009_trait_records_population
Revises: 0008_jobs_experiment_fk
Create Date: 2026-05-29

The Analyze map joins trait records to boundary-plot polygons. The
authoritative join key is ``plot_number`` — but ``plot_number`` is only
unique *within a population* (two populations in the same
experiment/season/site can each number their plots 1, 2, 3…). Until this
revision ``trait_records`` carried no population, so a population-scoped
join was impossible and the map fell back to the brittle
``plot_number+row+col`` composite that mismatches whenever the boundary
grid's local numbering differs from the field's true numbering.

What changes (mirrors the accession work in 0006):

1. ``trait_records`` gains two real columns:
     - ``population_id   UUID NULL``
     - ``population_name TEXT NULL``
   Both nullable — records without a population (e.g. some extractor
   output) remain legal; the map simply doesn't population-scope them.
   ``trait_records`` is a Citus *columnar* table (confirmed via pg_am),
   so — exactly as 0006 documented for accession — NO FK constraint and
   NO btree on the post-hoc column. Referential integrity is enforced by
   the ``populate_trait_record_ids`` trigger; read queries hit the
   ``trait_records_immv`` row store where we add the btree.

2. The ``populate_trait_record_ids`` trigger resolves
   ``population_name`` → ``population_id`` and, when a plot resolves,
   backfills population from the plot row (``plots.population_id``) so
   plot-linked records inherit population for free.

3. The ``trait_records_immv`` pg_ivm IMMV is dropped + recreated so its
   column shape matches the base table (pg_ivm doesn't propagate
   ALTER TABLE), and a btree on ``population_id`` is added to the IMMV
   for the map's population-scoped reads.

4. Existing rows are backfilled: ``population_name`` from
   ``record_info->>'population'`` (the import wizard's key), then
   ``population_id`` from ``gemini.populations`` by name; and for
   plot-linked rows, from ``plots.population_id`` directly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_trait_records_population"
down_revision: Union[str, Sequence[str], None] = "0008_jobs_experiment_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ─── Trigger body (post-migration) ────────────────────────────────────
# Adds population_name → population_id resolution and plot-population
# backfill on top of the 0006 trigger body. Everything else is identical
# to 0006's POPULATE_TRIGGER_BODY so a clean upgrade chain leaves exactly
# this function installed.
POPULATE_TRIGGER_BODY = """
CREATE OR REPLACE FUNCTION gemini.populate_trait_record_ids()
RETURNS TRIGGER AS $$
DECLARE
    trai_id UUID;
    dat_id UUID;
    exp_id UUID;
    sea_id UUID;
    sit_id UUID;
    pl_id UUID;
    acc_id UUID;
    plot_acc_id UUID;
    plot_acc_name TEXT;
    pop_id UUID;
    plot_pop_id UUID;
BEGIN
    -- Check if the trait, dataset, experiment, season, and site are valid
    IF NOT gemini.check_trait_validity(NEW.trait_name, NEW.dataset_name, NEW.experiment_name, NEW.season_name, NEW.site_name) THEN
        RAISE EXCEPTION 'Invalid trait, dataset, experiment, season, or site combination';
    END IF;

    SELECT id INTO trai_id FROM gemini.traits WHERE trait_name = NEW.trait_name;
    SELECT id INTO dat_id  FROM gemini.datasets WHERE dataset_name = NEW.dataset_name;
    SELECT id INTO exp_id  FROM gemini.experiments WHERE experiment_name = NEW.experiment_name;
    SELECT id INTO sea_id  FROM gemini.seasons
        WHERE season_name = NEW.season_name AND experiment_id = exp_id;
    SELECT id INTO sit_id  FROM gemini.sites WHERE site_name = NEW.site_name;

    -- Plot fields stay optional. When plot_number IS NULL the record is
    -- intentionally unlinked; when supplied, it must resolve to a real
    -- plot in this (experiment, season, site).
    IF NEW.plot_number IS NOT NULL THEN
        IF NOT gemini.check_plot_validity(NEW.experiment_name, NEW.season_name, NEW.site_name, NEW.plot_number, NEW.plot_row_number, NEW.plot_column_number) THEN
            RAISE EXCEPTION 'Invalid experiment, season, or site combination for plots';
        END IF;
        SELECT id INTO pl_id FROM gemini.plots
        WHERE experiment_id = exp_id
          AND season_id = sea_id
          AND site_id = sit_id
          AND plot_number = NEW.plot_number
          AND plot_row_number = NEW.plot_row_number
          AND plot_column_number = NEW.plot_column_number;
        IF pl_id IS NULL THEN
            RAISE EXCEPTION 'No matching plot found for the given parameters';
        END IF;
        NEW.plot_id := pl_id;
    END IF;

    -- Resolve accession_name → accession_id. NULL name means orphan.
    IF NEW.accession_name IS NOT NULL THEN
        SELECT id INTO acc_id FROM gemini.accessions
        WHERE accession_name = NEW.accession_name;
        IF acc_id IS NULL THEN
            RAISE EXCEPTION 'No accession found with name %', NEW.accession_name;
        END IF;
        NEW.accession_id := acc_id;
    END IF;

    -- Resolve population_name → population_id. Population names are
    -- globally unique in gemini.populations (single name-keyed table).
    -- NULL name leaves the record unscoped-by-population (still legal).
    IF NEW.population_name IS NOT NULL THEN
        SELECT id INTO pop_id FROM gemini.populations
        WHERE population_name = NEW.population_name;
        IF pop_id IS NULL THEN
            RAISE EXCEPTION 'No population found with name %', NEW.population_name;
        END IF;
        NEW.population_id := pop_id;
    END IF;

    -- If we resolved a plot, look up its accession + population directly.
    IF NEW.plot_id IS NOT NULL THEN
        SELECT p.accession_id, a.accession_name, p.population_id
          INTO plot_acc_id, plot_acc_name, plot_pop_id
          FROM gemini.plots p
          LEFT JOIN gemini.accessions a ON a.id = p.accession_id
         WHERE p.id = NEW.plot_id;
        -- Accession agreement check (unchanged from 0006).
        IF plot_acc_id IS NOT NULL
           AND NEW.accession_id IS NOT NULL
           AND plot_acc_id <> NEW.accession_id THEN
            RAISE EXCEPTION
                'Accession mismatch on trait_records: plot % is associated with accession % but record supplied accession %',
                NEW.plot_id, plot_acc_name, NEW.accession_name;
        END IF;
        IF plot_acc_id IS NOT NULL AND NEW.accession_id IS NULL THEN
            NEW.accession_id := plot_acc_id;
            IF NEW.accession_name IS NULL THEN
                NEW.accession_name := plot_acc_name;
            END IF;
        END IF;
        -- Backfill population from the plot when the record didn't carry
        -- one. The plot's population is authoritative for plot-linked
        -- records (it's what the boundary materialization stamped).
        IF plot_pop_id IS NOT NULL AND NEW.population_id IS NULL THEN
            NEW.population_id := plot_pop_id;
        END IF;
    END IF;

    NEW.trait_id := trai_id;
    NEW.dataset_id := dat_id;
    NEW.experiment_id := exp_id;
    NEW.season_id := sea_id;
    NEW.site_id := sit_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Pre-migration trigger body — identical to 0006's POPULATE_TRIGGER_BODY
# (the accession-aware version, no population), so downgrade() restores
# the chain to its 0006-era state exactly.
POPULATE_TRIGGER_BODY_PRE = """
CREATE OR REPLACE FUNCTION gemini.populate_trait_record_ids()
RETURNS TRIGGER AS $$
DECLARE
    trai_id UUID;
    dat_id UUID;
    exp_id UUID;
    sea_id UUID;
    sit_id UUID;
    pl_id UUID;
    acc_id UUID;
    plot_acc_id UUID;
    plot_acc_name TEXT;
BEGIN
    IF NOT gemini.check_trait_validity(NEW.trait_name, NEW.dataset_name, NEW.experiment_name, NEW.season_name, NEW.site_name) THEN
        RAISE EXCEPTION 'Invalid trait, dataset, experiment, season, or site combination';
    END IF;

    SELECT id INTO trai_id FROM gemini.traits WHERE trait_name = NEW.trait_name;
    SELECT id INTO dat_id  FROM gemini.datasets WHERE dataset_name = NEW.dataset_name;
    SELECT id INTO exp_id  FROM gemini.experiments WHERE experiment_name = NEW.experiment_name;
    SELECT id INTO sea_id  FROM gemini.seasons
        WHERE season_name = NEW.season_name AND experiment_id = exp_id;
    SELECT id INTO sit_id  FROM gemini.sites WHERE site_name = NEW.site_name;

    IF NEW.plot_number IS NOT NULL THEN
        IF NOT gemini.check_plot_validity(NEW.experiment_name, NEW.season_name, NEW.site_name, NEW.plot_number, NEW.plot_row_number, NEW.plot_column_number) THEN
            RAISE EXCEPTION 'Invalid experiment, season, or site combination for plots';
        END IF;
        SELECT id INTO pl_id FROM gemini.plots
        WHERE experiment_id = exp_id
          AND season_id = sea_id
          AND site_id = sit_id
          AND plot_number = NEW.plot_number
          AND plot_row_number = NEW.plot_row_number
          AND plot_column_number = NEW.plot_column_number;
        IF pl_id IS NULL THEN
            RAISE EXCEPTION 'No matching plot found for the given parameters';
        END IF;
        NEW.plot_id := pl_id;
    END IF;

    IF NEW.accession_name IS NOT NULL THEN
        SELECT id INTO acc_id FROM gemini.accessions
        WHERE accession_name = NEW.accession_name;
        IF acc_id IS NULL THEN
            RAISE EXCEPTION 'No accession found with name %', NEW.accession_name;
        END IF;
        NEW.accession_id := acc_id;
    END IF;

    IF NEW.plot_id IS NOT NULL THEN
        SELECT p.accession_id, a.accession_name
          INTO plot_acc_id, plot_acc_name
          FROM gemini.plots p
          LEFT JOIN gemini.accessions a ON a.id = p.accession_id
         WHERE p.id = NEW.plot_id;
        IF plot_acc_id IS NOT NULL
           AND NEW.accession_id IS NOT NULL
           AND plot_acc_id <> NEW.accession_id THEN
            RAISE EXCEPTION
                'Accession mismatch on trait_records: plot % is associated with accession % but record supplied accession %',
                NEW.plot_id, plot_acc_name, NEW.accession_name;
        END IF;
        IF plot_acc_id IS NOT NULL AND NEW.accession_id IS NULL THEN
            NEW.accession_id := plot_acc_id;
            IF NEW.accession_name IS NULL THEN
                NEW.accession_name := plot_acc_name;
            END IF;
        END IF;
    END IF;

    NEW.trait_id := trai_id;
    NEW.dataset_id := dat_id;
    NEW.experiment_id := exp_id;
    NEW.season_id := sea_id;
    NEW.site_id := sit_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    # 1. Add the two new columns — both nullable. Columnar table: no FK,
    #    no btree on a post-hoc column (see 0006 for the citus_columnar
    #    rationale). Validation lives in the trigger; the read-side btree
    #    goes on the IMMV in step 4.
    op.add_column(
        "trait_records",
        sa.Column("population_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="gemini",
    )
    op.add_column(
        "trait_records",
        sa.Column("population_name", sa.Text(), nullable=True),
        schema="gemini",
    )

    # 2. Backfill. First the name from record_info (the import wizard
    #    stores the population under the 'population' key), then the id by
    #    name, then — for plot-linked rows — straight from the plot.
    op.execute(
        """
        UPDATE gemini.trait_records
           SET population_name = NULLIF(record_info->>'population', '')
         WHERE population_name IS NULL
           AND record_info ? 'population';
        """
    )
    op.execute(
        """
        UPDATE gemini.trait_records tr
           SET population_id = p.id
          FROM gemini.populations p
         WHERE tr.population_id IS NULL
           AND tr.population_name IS NOT NULL
           AND p.population_name = tr.population_name;
        """
    )
    op.execute(
        """
        UPDATE gemini.trait_records tr
           SET population_id = pl.population_id,
               population_name = COALESCE(tr.population_name, pop.population_name)
          FROM gemini.plots pl
          LEFT JOIN gemini.populations pop ON pop.id = pl.population_id
         WHERE tr.population_id IS NULL
           AND tr.plot_id IS NOT NULL
           AND pl.id = tr.plot_id
           AND pl.population_id IS NOT NULL;
        """
    )

    # 3. Install the population-aware trigger body.
    op.execute(POPULATE_TRIGGER_BODY)

    # 4. Recreate the pg_ivm IMMV so its columns match the base table,
    #    and add a btree on population_id for population-scoped reads.
    #    Same out-of-transaction dance as 0006 — dropping an IMMV inside a
    #    wrapped transaction segfaults the backend during pg_ivm teardown.
    bind = op.get_bind()
    bind.execute(sa.text("COMMIT"))
    bind.execute(sa.text("DROP TABLE IF EXISTS gemini.trait_records_immv CASCADE"))
    bind.execute(
        sa.text(
            "SELECT pgivm.create_immv('gemini.trait_records_immv', "
            "'select * from gemini.trait_records')"
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_trait_records_immv_population_id "
            "ON gemini.trait_records_immv (population_id)"
        )
    )
    bind.execute(sa.text("BEGIN"))


def downgrade() -> None:
    # Restore the prior (0006) trigger body first so DROPs don't race with
    # the population lookup on any in-flight INSERTs.
    op.execute(POPULATE_TRIGGER_BODY_PRE)

    op.drop_column("trait_records", "population_name", schema="gemini")
    op.drop_column("trait_records", "population_id", schema="gemini")

    # IMMV recreate outside alembic's transaction (pg_ivm teardown).
    bind = op.get_bind()
    bind.execute(sa.text("COMMIT"))
    bind.execute(sa.text("DROP TABLE IF EXISTS gemini.trait_records_immv CASCADE"))
    bind.execute(
        sa.text(
            "SELECT pgivm.create_immv('gemini.trait_records_immv', "
            "'select * from gemini.trait_records')"
        )
    )
    bind.execute(sa.text("BEGIN"))
