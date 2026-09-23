"""Phase 9d': move genotype calls from a Hydra columnar tall table into
PGEN files in MinIO; keep Postgres for metadata only.

Revision ID: 0002_genomic_pgen_metadata
Revises: 0001_baseline
Create Date: 2026-05-01

Architecture review (research agent, 2026-05-01) found that
``gemini.genotype_records`` (one row per study × variant × accession
call) was the dominant performance bottleneck for the genomic flow:

* The table is ``USING columnar`` (Hydra), which serializes
  table-level writes via an internal lock. Concurrent inserts queue up
  rather than overlap.
* A 3-column UNIQUE constraint plus three secondary btree indexes plus
  one GIN index on ``record_info`` (always ``{}`` in practice) cost
  ~3 GB of index storage on a ~3 GB table, and every ingest pays the
  uniqueness lookup against the largest of those.
* DELETE never reclaims stripe space (Hydra DELETE only flips a row
  mask), so the table grows monotonically across re-imports.
* The GWAS worker already converts the tall data into PLINK PGEN at
  job time (``backend/gemini/workers/gwas/extract.py:97``). Storing it
  tall just to flatten it back into a packed format is double work.

Prior art (BreedBase/Chado, Gigwa, the GenomicSelectionDB benchmark
paper) all reach the same conclusion: per-call rows in an RDBMS don't
scale. The chosen design here is metadata-in-Postgres, calls-in-PGEN.

This migration is the **additive** half of the rework: it adds the
four new metadata tables but does NOT yet drop ``genotype_records``.
The legacy table stays in place so existing read paths (export, GWAS
extract, /records pagination) keep functioning while Phases 9d'.2–.4
cut them over. A follow-up migration in Phase 9d'.5 drops the legacy
table once nothing reads from it.

Tables added:
  - ``genotyping_study_files`` — file_kind → MinIO URI + bytes + sha256.
  - ``genotyping_study_variants`` — variant ↔ ordinal in PGEN.
  - ``genotyping_study_samples`` — accession ↔ ordinal in PSAM.
  - ``genotyping_study_variant_stats`` — pre-computed per-variant
    stats (MAF, missing, HWE) so the variant browser doesn't need to
    crack the PGEN for analytic UI.

Downgrade is a clean drop of those four tables. ``genotype_records``
is untouched in either direction.

Pre-Alembic bridge: upgrade() also creates (IF NOT EXISTS) the five
tables that main's pre-Alembic init_sql/ lacked — users,
user_experiments, reference_datasets, reference_plots,
plot_geometry_versions — so a main-built DB stamped at 0001_baseline
can upgrade. No-op on fresh DBs; not reversed by downgrade().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_genomic_pgen_metadata"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Allowed values for genotyping_study_files.file_kind. Not enforced as a
# CHECK constraint here so the set can grow without a follow-up
# migration; the application validates on write.
_FILE_KINDS = (
    "pgen",         # PLINK2 packed genotype matrix (canonical write target)
    "pvar",         # PLINK2 variant metadata sidecar
    "psam",         # PLINK2 sample metadata sidecar
    "bcf",          # bcftools binary VCF (region-query friendly)
    "bcf_index",    # .csi for the bcf above
    "parquet",      # per-variant stats in Apache Parquet
    "manifest",     # JSON manifest summarizing the per-study artefacts
    "source",       # original uploaded archive (xlsx/HapMap/VCF) for audit
)


# ─── Pre-Alembic bridge (see upgrade() step 0) ────────────────────────
# DDL copied verbatim from gemini/db/init_sql/scripts/2_init_schema.sql
# (users, reference_datasets, reference_plots, plot_geometry_versions)
# and 3_init_relationships.sql (user_experiments). The only edits are
# that every CREATE is ``IF NOT EXISTS`` and each ``ADD CONSTRAINT`` is
# wrapped in a pg_constraint guard, so the whole block is a no-op on a
# DB that already has these objects.
_PRE_ALEMBIC_BRIDGE_DDL = (
    # --- users (2_init_schema.sql) ---
    """
    CREATE TABLE IF NOT EXISTS gemini.users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
        user_info JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON gemini.users (email)",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON gemini.users (email)",
    "CREATE INDEX IF NOT EXISTS idx_users_info ON gemini.users USING GIN (user_info)",
    # --- reference_datasets (2_init_schema.sql) ---
    """
    CREATE TABLE IF NOT EXISTS gemini.reference_datasets (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        experiment VARCHAR(255),
        location VARCHAR(255),
        population VARCHAR(255),
        dataset_date DATE,
        trait_columns TEXT[] NOT NULL DEFAULT '{}',
        dataset_info JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reference_datasets_name ON gemini.reference_datasets (name)",
    "CREATE INDEX IF NOT EXISTS idx_reference_datasets_experiment ON gemini.reference_datasets (experiment)",
    "CREATE INDEX IF NOT EXISTS idx_reference_datasets_population ON gemini.reference_datasets (population)",
    # --- reference_plots (2_init_schema.sql) ---
    """
    CREATE TABLE IF NOT EXISTS gemini.reference_plots (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        dataset_id UUID NOT NULL REFERENCES gemini.reference_datasets(id) ON DELETE CASCADE,
        plot_id VARCHAR(255),
        plot_column VARCHAR(64),
        plot_row VARCHAR(64),
        accession VARCHAR(255),
        traits JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reference_plots_dataset ON gemini.reference_plots (dataset_id)",
    "CREATE INDEX IF NOT EXISTS idx_reference_plots_plot_id ON gemini.reference_plots (plot_id)",
    "CREATE INDEX IF NOT EXISTS idx_reference_plots_accession ON gemini.reference_plots (accession)",
    "CREATE INDEX IF NOT EXISTS idx_reference_plots_traits ON gemini.reference_plots USING GIN (traits)",
    # --- plot_geometry_versions (2_init_schema.sql) ---
    """
    CREATE TABLE IF NOT EXISTS gemini.plot_geometry_versions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        directory VARCHAR(1024) NOT NULL,
        version INT NOT NULL,
        name VARCHAR(255),
        is_active BOOLEAN NOT NULL DEFAULT FALSE,
        state_snapshot JSONB NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_by VARCHAR(255)
    )
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conname = 'plot_geometry_version_unique'
               AND conrelid = 'gemini.plot_geometry_versions'::regclass
        ) THEN
            ALTER TABLE gemini.plot_geometry_versions ADD CONSTRAINT plot_geometry_version_unique UNIQUE (directory, version);
        END IF;
    END
    $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_plot_geometry_versions_directory ON gemini.plot_geometry_versions (directory)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_plot_geometry_versions_active ON gemini.plot_geometry_versions (directory) WHERE is_active",
    # --- user_experiments (3_init_relationships.sql) ---
    """
    CREATE TABLE IF NOT EXISTS gemini.user_experiments (
        user_id UUID REFERENCES gemini.users(id) ON DELETE CASCADE,
        experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
        role VARCHAR(50),
        info JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, experiment_id)
    )
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conname = 'user_experiment_unique'
               AND conrelid = 'gemini.user_experiments'::regclass
        ) THEN
            ALTER TABLE gemini.user_experiments ADD CONSTRAINT user_experiment_unique UNIQUE (user_id, experiment_id);
        END IF;
    END
    $$
    """,
)


def upgrade() -> None:
    # 0. PRE-ALEMBIC BRIDGE. DBs built from main's (pre-Alembic)
    #    init_sql/ and stamped at 0001_baseline are missing five tables
    #    that only exist in this branch's init_sql/: users,
    #    user_experiments, reference_datasets, reference_plots and
    #    plot_geometry_versions. Without them 0004 fails (its
    #    experiment_files.uploaded_by FK targets gemini.users) and the
    #    ORM models for the others hit UndefinedTable. We create them
    #    here, idempotently, rather than in 0001 so DBs already stamped
    #    at 0001 still pick them up. On a DB bootstrapped from current
    #    init_sql/ every statement is a no-op. Intentionally NOT undone
    #    in downgrade(): these tables are day-0 schema, not part of this
    #    revision's genomic change, and dropping them would destroy
    #    user/auth data.
    for stmt in _PRE_ALEMBIC_BRIDGE_DDL:
        op.execute(stmt)

    # NOTE: ``gemini.genotype_records`` is intentionally left in place
    # for now — the legacy export / GWAS-extract / records pagination
    # paths still query it during the 9d'.2–.4 cutover. A follow-up
    # migration in Phase 9d'.5 drops the table once those read paths
    # have moved to the PGEN-backed equivalents below.

    # 1. Pointer table: one row per (study, file_kind). The rest-api
    #    looks up the s3_uri here and either streams the file out for
    #    export or hands a presigned URL to the GWAS worker.
    op.create_table(
        "genotyping_study_files",
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_kind", sa.Text(), nullable=False),
        sa.Column("s3_uri", sa.Text(), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("study_id", "file_kind"),
        schema="gemini",
    )

    # 2. Variant catalog per study: which variants are in this study's
    #    PGEN, and at what ordinal. The variant_index lets a callable
    #    detail endpoint slice the PGEN row directly without scanning.
    op.create_table(
        "genotyping_study_variants",
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.variants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("variant_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("study_id", "variant_id"),
        schema="gemini",
    )
    # Ordinal lookups (e.g. "what's the variant at row N?") use this
    # secondary key. Cheap on a heap table; required for streaming the
    # variant browser without having to ORDER BY at query time.
    op.create_index(
        "idx_genotyping_study_variants_ordinal",
        "genotyping_study_variants",
        ["study_id", "variant_index"],
        unique=True,
        schema="gemini",
    )

    # 3. Sample catalog per study: which accessions appear in the .psam
    #    and at what ordinal. Same shape as variants; used by GWAS to
    #    align phenotype rows with the PGEN columns.
    op.create_table(
        "genotyping_study_samples",
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accession_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.accessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sample_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("study_id", "accession_id"),
        schema="gemini",
    )
    op.create_index(
        "idx_genotyping_study_samples_ordinal",
        "genotyping_study_samples",
        ["study_id", "sample_index"],
        unique=True,
        schema="gemini",
    )

    # 4. Pre-computed per-variant analytics. Computed at ingest from the
    #    PGEN by a single bcftools / DuckDB pass; lets the variant
    #    browser show MAF / missing / HWE without cracking the PGEN.
    #    Small (one row per variant per study), heap, indexed.
    op.create_table(
        "genotyping_study_variant_stats",
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.genotyping_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gemini.variants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("n_called", sa.Integer(), nullable=True),
        sa.Column("n_missing", sa.Integer(), nullable=True),
        sa.Column("maf", sa.Float(), nullable=True),
        sa.Column("hwe_p", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("study_id", "variant_id"),
        schema="gemini",
    )

    # Note: there are intentionally NO indexes on (chromosome) or
    # (record_info GIN) here. The columnar tall table had four
    # secondary indexes that totalled ~3 GB on the user's DB; on
    # PGEN-backed reads the variant catalog is small enough that the
    # PK + ordinal indexes are sufficient.


def downgrade() -> None:
    # Drop the four new metadata tables. ``genotype_records`` is
    # untouched in either direction (the legacy table was not modified
    # by upgrade(), so downgrade has nothing to restore).
    op.drop_table("genotyping_study_variant_stats", schema="gemini")
    op.drop_index(
        "idx_genotyping_study_samples_ordinal",
        table_name="genotyping_study_samples",
        schema="gemini",
    )
    op.drop_table("genotyping_study_samples", schema="gemini")
    op.drop_index(
        "idx_genotyping_study_variants_ordinal",
        table_name="genotyping_study_variants",
        schema="gemini",
    )
    op.drop_table("genotyping_study_variants", schema="gemini")
    op.drop_table("genotyping_study_files", schema="gemini")
