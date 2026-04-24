"""
SQLAlchemy model for plot-geometry version snapshots.

Named, timestamped snapshots of the plot-marking state for a given
`directory` (the MinIO path used by the plot_geometry controller as the
scoping key, e.g. `Raw/2024/ExpA/Lincoln/Pop1/2024-06-01/Amiga/top`).
Each `(directory, version)` is unique; at most one row per directory has
`is_active = True`.
"""
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    TIMESTAMP,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class PlotGeometryVersionModel(BaseModel):
    """Named snapshot of plot-geometry state for a directory."""

    __tablename__ = "plot_geometry_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    directory: Mapped[str] = mapped_column(String(1024), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "directory", "version", name="plot_geometry_version_unique"
        ),
        Index("idx_plot_geometry_versions_directory", "directory"),
        Index(
            "idx_plot_geometry_versions_active",
            "directory",
            unique=True,
            postgresql_where=is_active,
        ),
    )
