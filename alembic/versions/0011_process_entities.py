"""Server-side Process workspaces, pipelines and runs.

Revision ID: 0011_process_entities
Revises: 0010_filter_trait_records_pop
Create Date: 2026-09-22

They lived only in the browser's localStorage: gone if site data was
cleared, invisible to a second user or machine. Each is now one row
holding the app's JSON document for it. ``parent_id`` chains
run → pipeline → workspace with ON DELETE CASCADE, so deleting a
workspace removes its pipelines and runs, as the browser store did.
Documents are opaque to the database; the app owns their shape.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011_process_entities"
down_revision: Union[str, Sequence[str], None] = "0010_filter_trait_records_pop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS gemini.process_entities (
            id UUID PRIMARY KEY,
            kind VARCHAR(16) NOT NULL CHECK (kind IN ('workspace', 'pipeline', 'run')),
            parent_id UUID REFERENCES gemini.process_entities(id) ON DELETE CASCADE,
            doc JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(255)
        );
        CREATE INDEX IF NOT EXISTS idx_process_entities_kind
            ON gemini.process_entities (kind);
        CREATE INDEX IF NOT EXISTS idx_process_entities_parent
            ON gemini.process_entities (parent_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS gemini.process_entities")
