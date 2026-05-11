"""Add ``accession_id`` / ``accession_name`` to ``gemini.trait_records``.

Revision ID: 0006_trait_records_accession
Revises: 0005_experiment_files_metadata
Create Date: 2026-05-11

GWAS — and every downstream analysis that correlates phenotype with
germplasm identity — needs a direct trait_record → accession link.
Until this revision, the only path was
``trait_records.plot_id → plot_accession_view.accession_name``, which
breaks for "orphan" trait records (no plot mapped during import).
Those records carried the accession name only inside the
``record_info`` JSONB blob, which has no index, no FK, and no
trigger-side validation.

What changes:

1. ``trait_records`` gains two real columns:
     - ``accession_id UUID NULL REFERENCES gemini.accessions(id)``
     - ``accession_name TEXT NULL``
   Both nullable to keep the orphan path usable when the user truly
   has no germplasm column to map (the records still ingest, GWAS
   simply skips them).

2. The ``populate_trait_record_ids`` trigger now also resolves
   ``accession_name`` → ``accession_id``. When both ``plot_id`` and
   ``accession_name`` are set, the trigger asserts that the plot's
   accession matches the supplied name and RAISEs on mismatch — a
   plot collision is a data-quality bug the user wants to know about.

3. The ``trait_records_immv`` (pg_ivm IMMV) is dropped and recreated
   so its column shape matches the base table. pg_ivm does NOT
   propagate ALTER TABLE on the source; the IMMV's column list is
   frozen at create time. Recreating it is the cheap fix (the IMMV
   is "select * from trait_records" so its row set is identical to
   the base table — no extra work beyond one full scan).

4. Existing rows are backfilled: ``accession_name`` is copied from
   ``record_info->>'accession_name'`` where present, and
   ``accession_id`` is resolved from ``gemini.accessions``. Rows
   whose JSONB key is missing or whose name doesn't match any
   accession stay NULL — the GWAS worker treats those as
   "no phenotype" and excludes them from the run, which is the
   correct behavior for partial / orphan data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_trait_records_accession"
down_revision: Union[str, Sequence[str], None] = "0005_experiment_files_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ─── Trigger body (post-migration) ────────────────────────────────────
# Resolves accession_name → accession_id, and asserts plot/accession
# agreement when both are present. Mirrors the existing trigger's
# style: simple PL/pgSQL, RAISE on any inconsistency, leave NULL when
# the user genuinely supplies nothing.
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

    -- Resolve accession_name → accession_id. Same lookup approach as
    -- the other *_name → *_id pairs above. NULL name means orphan.
    IF NEW.accession_name IS NOT NULL THEN
        SELECT id INTO acc_id FROM gemini.accessions
        WHERE accession_name = NEW.accession_name;
        IF acc_id IS NULL THEN
            RAISE EXCEPTION 'No accession found with name %', NEW.accession_name;
        END IF;
        NEW.accession_id := acc_id;
    END IF;

    -- If we resolved a plot, look up its accession directly. The
    -- plots table carries accession_id as a column; no junction.
    IF NEW.plot_id IS NOT NULL THEN
        SELECT p.accession_id, a.accession_name
          INTO plot_acc_id, plot_acc_name
          FROM gemini.plots p
          LEFT JOIN gemini.accessions a ON a.id = p.accession_id
         WHERE p.id = NEW.plot_id;
        -- If both are set and they disagree, fail loudly. Mismatch
        -- means the user's germplasm column points at a different
        -- line than the plot map does — a data-quality bug they
        -- should see, not silently accept.
        IF plot_acc_id IS NOT NULL
           AND NEW.accession_id IS NOT NULL
           AND plot_acc_id <> NEW.accession_id THEN
            RAISE EXCEPTION
                'Accession mismatch on trait_records: plot % is associated with accession % but record supplied accession %',
                NEW.plot_id, plot_acc_name, NEW.accession_name;
        END IF;
        -- Backfill from plot when the user didn't supply a germplasm
        -- column. Keeps the GWAS path working for plot-only imports.
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

# Pre-migration trigger body — same SQL as currently lives in
# init_sql/scripts/6_init_functions.sql:616, kept here so downgrade()
# can restore it exactly.
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
BEGIN
    IF NOT gemini.check_trait_validity(NEW.trait_name, NEW.dataset_name, NEW.experiment_name, NEW.season_name, NEW.site_name) THEN
        RAISE EXCEPTION 'Invalid trait, dataset, experiment, season, or site combination';
    END IF;

    SELECT id INTO trai_id FROM gemini.traits WHERE trait_name = NEW.trait_name;
    SELECT id INTO dat_id  FROM gemini.datasets WHERE dataset_name = NEW.dataset_name;
    SELECT id INTO exp_id  FROM gemini.experiments WHERE experiment_name = NEW.experiment_name;
    SELECT id INTO sea_id  FROM gemini.seasons WHERE season_name = NEW.season_name AND experiment_id = exp_id;
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
    # 1. Add the two new columns. Both nullable — orphan records remain
    #    legal, the GWAS worker skips them.
    #
    # ``trait_records`` is a Citus columnar table, which does NOT support
    # foreign-key constraints (the same reason the existing trait_id,
    # experiment_id, etc. on this table aren't FK-constrained either),
    # and does NOT support creating btree indexes on columns added
    # after rows already exist (citus_columnar's index builder
    # crashes with "insufficient data for reading boolean array"
    # when scanning a not-yet-populated column). Both are fine for
    # this use case: referential integrity is enforced by the
    # populate_trait_record_ids trigger, and read queries hit
    # ``trait_records_immv`` (row store) where we DO put a btree
    # index — see step 4.
    op.add_column(
        "trait_records",
        sa.Column("accession_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="gemini",
    )
    op.add_column(
        "trait_records",
        sa.Column("accession_name", sa.Text(), nullable=True),
        schema="gemini",
    )

    # 2. Backfill from record_info JSONB. We split this into two
    #    statements: first set accession_name from the JSONB key (so
    #    even rows with an unrecognised name keep their best-effort
    #    label for diagnostics), then resolve accession_id where the
    #    name maps to a known accession. Pre-existing rows that have
    #    no `accession_name` key in record_info simply stay NULL.
    op.execute(
        """
        UPDATE gemini.trait_records
           SET accession_name = NULLIF(record_info->>'accession_name', '')
         WHERE record_info ? 'accession_name';
        """
    )
    op.execute(
        """
        UPDATE gemini.trait_records tr
           SET accession_id = a.id
          FROM gemini.accessions a
         WHERE tr.accession_id IS NULL
           AND tr.accession_name IS NOT NULL
           AND a.accession_name = tr.accession_name;
        """
    )
    # Plot-based records that pre-date this migration: pull the
    # accession from the plot row so they're GWAS-eligible too.
    op.execute(
        """
        UPDATE gemini.trait_records tr
           SET accession_id = p.accession_id,
               accession_name = COALESCE(tr.accession_name, a.accession_name)
          FROM gemini.plots p
          LEFT JOIN gemini.accessions a ON a.id = p.accession_id
         WHERE tr.accession_id IS NULL
           AND tr.plot_id IS NOT NULL
           AND p.id = tr.plot_id
           AND p.accession_id IS NOT NULL;
        """
    )

    # 3. Replace the populate_trait_record_ids trigger function with
    #    the version that resolves accession_name → accession_id and
    #    asserts plot/accession agreement.
    op.execute(POPULATE_TRIGGER_BODY)

    # 4. Recreate the pg_ivm IMMV so its column set matches the new
    #    base table. pg_ivm doesn't propagate ALTER TABLE on the
    #    source — its column list is frozen at create time. Drop +
    #    recreate is the documented path. The recreate runs the
    #    defining SELECT once, so backfilled rows land in the IMMV
    #    immediately.
    #
    # We have to commit alembic's transaction first and run the IMMV
    # drop/recreate on its own autocommit connection: dropping an
    # IMMV inside a wrapped transaction has been observed to crash
    # the backend during COMMIT (pg_ivm trigger teardown segfaults
    # the backend process). Doing it on an unwrapped connection
    # sidesteps the bad code path.
    bind = op.get_bind()
    bind.execute(sa.text("COMMIT"))
    bind.execute(sa.text("DROP TABLE IF EXISTS gemini.trait_records_immv CASCADE"))
    bind.execute(
        sa.text(
            "SELECT pgivm.create_immv('gemini.trait_records_immv', "
            "'select * from gemini.trait_records')"
        )
    )
    # Btree on the row-store IMMV so the GWAS join ``WHERE
    # accession_id = ?`` can index-scan instead of seq-scan. Safe
    # here because the IMMV is plain heap, not columnar.
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_trait_records_immv_accession_id "
            "ON gemini.trait_records_immv (accession_id)"
        )
    )
    # Reopen a transaction so the alembic runner's own COMMIT at the
    # end of upgrade() has something to commit. Without this, alembic
    # complains the connection is in autocommit state.
    bind.execute(sa.text("BEGIN"))


def downgrade() -> None:
    # Restore the prior trigger body first so DROPs don't race with
    # the new function's accession lookup on any in-flight INSERTs.
    op.execute(POPULATE_TRIGGER_BODY_PRE)

    op.drop_column("trait_records", "accession_name", schema="gemini")
    op.drop_column("trait_records", "accession_id", schema="gemini")

    # IMMV recreate happens outside alembic's transaction for the
    # same reason as in upgrade() — pg_ivm teardown segfaults inside
    # a wrapped transaction.
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
