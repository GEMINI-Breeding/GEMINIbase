"""
SQLAlchemy model for Sensor entities in the GEMINIbase database.
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


class SensorModel(BaseModel):
    """
    Represents a sensor in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the sensor.
        sensor_name (str): The name of the sensor.
        sensor_type_id (int): Foreign key referencing the sensor type.
        sensor_data_type_id (int): Foreign key referencing the data type of the sensor's data.
        sensor_data_format_id (int): Foreign key referencing the data format of the sensor's data.
        sensor_info (dict): Additional JSONB data for the sensor.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "sensors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    sensor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensor_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("gemini.sensor_types.id"), default=0)
    sensor_data_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("gemini.data_types.id"), default=0)
    sensor_data_format_id: Mapped[int] = mapped_column(Integer, ForeignKey("gemini.data_formats.id"), default=0)
    sensor_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("sensor_name"),
        Index("idx_sensors_info", "sensor_info", postgresql_using="GIN"),
    )
