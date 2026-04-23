"""
SQLAlchemy model for Script entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid

class ScriptModel(BaseModel):
    """
    Represents a script in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the script.
        script_name (str): The name of the script.
        script_url (str): The URL where the script can be accessed.
        script_extension (str): The file extension of the script.
        script_info (dict): Additional JSONB data for the script.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    script_name: Mapped[str] = mapped_column(String(255))
    script_url: Mapped[str] = mapped_column(String(255))
    script_extension: Mapped[str] = mapped_column(String(255))
    script_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('script_name', 'script_url'),
        Index('idx_scripts_info', 'script_info', postgresql_using='GIN')
    )
