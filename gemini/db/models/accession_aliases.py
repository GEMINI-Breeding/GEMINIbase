"""
SQLAlchemy model for AccessionAlias entities in the GEMINI database.

An alias is an alternate name (numeric field-book shorthand, BrAPI-style
synonym, legacy identifier) that resolves to exactly one canonical
Accession OR Line. Scope may be 'global' (resolves everywhere) or
'experiment' (resolves only within a specific experiment), which prevents
collisions when two experiments independently use numeric keys like 1, 2, 3.
"""

from sqlalchemy import String, TIMESTAMP, CheckConstraint, Index, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class AccessionAliasModel(BaseModel):
    """
    Represents an alias (alternate name) for an accession or line.

    Exactly one of accession_id or line_id must be set (enforced by
    CHECK constraint). Uniqueness is on (scope, experiment_id, lower(alias))
    via a functional unique index in the init SQL — not declared here
    because SQLAlchemy's UniqueConstraint doesn't support function expressions.
    """
    __tablename__ = "accession_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    accession_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gemini.accessions.id", ondelete="CASCADE"), nullable=True
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gemini.lines.id", ondelete="CASCADE"), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="global")
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gemini.experiments.id", ondelete="CASCADE"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(512), nullable=True)
    alias_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        CheckConstraint(
            "scope IN ('global','experiment')",
            name="accession_alias_scope_check",
        ),
        CheckConstraint(
            "(CASE WHEN accession_id IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN line_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="accession_alias_target_check",
        ),
        CheckConstraint(
            "(scope = 'experiment') = (experiment_id IS NOT NULL)",
            name="accession_alias_scope_experiment_check",
        ),
        Index("idx_accession_aliases_info", "alias_info", postgresql_using="GIN"),
        Index(
            "idx_accession_aliases_lower_alias",
            text("lower(alias)"),
        ),
        Index(
            "idx_accession_aliases_exp_lower_alias",
            "experiment_id",
            text("lower(alias)"),
        ),
    )
