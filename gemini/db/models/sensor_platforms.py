"""
SQLAlchemy model for SensorPlatform entities in the GEMINIbase database.
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


class SensorPlatformModel(BaseModel):
    """
    Represents a sensor platform in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the sensor platform.
        sensor_platform_name (str): The name of the sensor platform.
        sensor_platform_info (dict): Additional JSONB data for the sensor platform.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "sensor_platforms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    sensor_platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensor_platform_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)


    __table_args__ = (
        UniqueConstraint("sensor_platform_name"),
        Index(
            "idx_sensor_platforms_info", "sensor_platform_info", postgresql_using="GIN"
        ),
    )
