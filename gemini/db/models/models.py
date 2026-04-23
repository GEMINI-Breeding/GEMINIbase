"""
SQLAlchemy model for Model entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid

class ModelModel(BaseModel):
    """
    Represents a model in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the model.
        model_name (str): The name of the model.
        model_url (str): The URL where the model can be accessed.
        model_info (dict): Additional JSONB data for the model.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(255))
    model_url: Mapped[str] = mapped_column(String(255))
    model_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("model_name", "model_url"),
        Index("idx_models_info", "model_info", postgresql_using="GIN"),
    )
