"""
SQLAlchemy model for SensorType entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid


class SensorTypeModel(BaseModel):
  """
  Represents a sensor type in the GEMINIbase database.

  Attributes:
    id (int): Unique identifier for the sensor type.
    sensor_type_name (str): The name of the sensor type (e.g., "Temperature", "Humidity").
    sensor_type_info (dict): Additional JSONB data for the sensor type.
    created_at (datetime): Timestamp when the record was created.
    updated_at (datetime): Timestamp when the record was last updated.
  """
  __tablename__ = 'sensor_types'

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  sensor_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
  sensor_type_info: Mapped[dict] = mapped_column(JSONB, default={})
  created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
  updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

  __table_args__ = (
    UniqueConstraint('sensor_type_name'),
    Index('idx_sensor_types_info', 'sensor_type_info', postgresql_using='GIN')
  )
