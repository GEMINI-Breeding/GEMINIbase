"""
SQLAlchemy model for TraitLevel entities in the GEMINIbase database.
"""

from sqlalchemy import JSON, String, TIMESTAMP, UniqueConstraint, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class TraitLevelModel(BaseModel):
    """
    Represents a trait level in the GEMINIbase database.

    Attributes:
        id (int): Unique identifier for the trait level.
        trait_level_name (str): The name of the trait level.
        trait_level_info (dict): Additional JSONB data for the trait level.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "trait_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trait_level_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trait_level_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("trait_level_name", name="trait_level_unique"),
        Index("idx_trait_levels_info", "trait_level_info", postgresql_using="GIN"),
    )
