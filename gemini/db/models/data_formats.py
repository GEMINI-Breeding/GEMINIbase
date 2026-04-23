"""
SQLAlchemy model for DataFormat entities in the GEMINIbase database.
"""

from sqlalchemy import JSON, String, TIMESTAMP, UniqueConstraint, Index, Integer, Identity
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class DataFormatModel(BaseModel):
    """
    Represents a data format in the GEMINIbase database.

    Attributes:
        id (int): Unique integer identifier for the data format.
        data_format_name (str): The name of the data format (e.g., "CSV", "JSON").
        data_format_mime_type (str): The MIME type associated with the data format.
        data_format_info (dict): Additional JSONB data for the data format.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "data_formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_format_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_format_mime_type: Mapped[str] = mapped_column(String(255), default='application/octet-stream')
    data_format_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('data_format_name', name='data_format_unique'),
        Index('idx_data_formats_info', 'data_format_info', postgresql_using='GIN')
    )
