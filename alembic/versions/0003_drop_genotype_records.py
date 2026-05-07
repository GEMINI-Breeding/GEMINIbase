"""Phase 9d'.5: drop the legacy ``gemini.genotype_records`` columnar
table now that all read paths have moved to PGEN-in-MinIO.

Revision ID: 0003_drop_genotype_records
Revises: 0002_genomic_pgen_metadata
Create Date: 2026-05-01

The legacy tall table held one row per (study, variant, accession) call
and was the dominant performance bottleneck of the genomic flow:
~3 GB index storage on a ~3 GB columnar heap, advisory-locked writes,
and DELETE that never reclaimed stripe space. Phase 9d'.0 wiped its
contents; Phases 9d'.2-.4 cut every consumer over to MinIO PGEN +
metadata-only Postgres tables. With nothing reading it, this migration
finally drops the table along with its four indexes and the UNIQUE
constraint.

Downgrade re-creates the table empty, in case a future revert needs
the schema back; the columnar extension and Hydra access method are
preserved at the database level by ``init_sql/4_init_columnar.sql``.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0003_drop_genotype_records"
down_revision: Union[str, Sequence[str], None] = "0002_genomic_pgen_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CASCADE picks up the four secondary indexes + the UNIQUE
    # constraint without us listing them explicitly.
    op.execute("DROP TABLE IF EXISTS gemini.genotype_records CASCADE")


def downgrade() -> None:
    # Re-create the empty columnar table and its index footprint.
    # Mirrors the original DDL in
    # backend/gemini/db/init_sql/scripts/4_init_columnar.sql:260-283.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS gemini.genotype_records (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            study_id UUID,
            study_name TEXT,
            variant_id UUID,
            variant_name TEXT,
            chromosome INTEGER,
            position FLOAT,
            accession_id UUID,
            accession_name TEXT,
            call_value VARCHAR(10),
            record_info JSONB NOT NULL DEFAULT '{}'
        ) USING columnar
        """
    )
    op.execute(
        """
        ALTER TABLE gemini.genotype_records
        ADD CONSTRAINT genotype_records_unique
        UNIQUE (study_id, variant_id, accession_id)
        """
    )
    op.execute(
        "CREATE INDEX genotype_records_study_variant_idx "
        "ON gemini.genotype_records (study_id, variant_id)"
    )
    op.execute(
        "CREATE INDEX genotype_records_study_accession_idx "
        "ON gemini.genotype_records (study_id, accession_id)"
    )
    op.execute(
        "CREATE INDEX genotype_records_chromosome_idx "
        "ON gemini.genotype_records (chromosome)"
    )
    op.execute(
        "CREATE INDEX genotype_records_record_info_idx "
        "ON gemini.genotype_records USING GIN (record_info)"
    )
