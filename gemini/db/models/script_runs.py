"""
SQLAlchemy model for ScriptRun entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    UniqueConstraint,
    Index,
    Integer,
    Boolean,
    ForeignKey,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from gemini.db.core.base import BaseModel

import uuid
from datetime import datetime


class ScriptRunModel(BaseModel):
    """
    Represents a script run in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the script run.
        script_id (uuid.UUID): Foreign key referencing the script.
        script_run_info (dict): Additional JSONB data for the script run.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "script_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gemini.scripts.id", ondelete="CASCADE"))
    script_run_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("script_id", "script_run_info"),
        Index("idx_script_runs_info", "script_run_info", postgresql_using="GIN"),
    )
