"""
SQLAlchemy model for DataType entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    Index,
    Integer
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from gemini.db.core.base import BaseModel
from datetime import datetime

class DataTypeModel(BaseModel):
    """
    Represents a data type in the GEMINIbase database.

    Attributes:
        id (int): Unique integer identifier for the data type.
        data_type_name (str): The name of the data type (e.g., "Temperature", "Humidity").
        data_type_info (dict): Additional JSONB data for the data type.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = 'data_types'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('data_type_name', name='data_type_unique'),
        Index('idx_data_types_info', 'data_type_info', postgresql_using='GIN')
    )
