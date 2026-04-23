"""
SQLAlchemy model for Dataset entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    UniqueConstraint,
    Index,
    Integer,
    ForeignKey,
    TIMESTAMP,
    DATE,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime, date
import uuid


class DatasetModel(BaseModel):
    """
    Represents a dataset in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the dataset.
        collection_date (date): The date when the dataset was collected.
        dataset_name (str): The name of the dataset.
        dataset_info (dict): Additional JSONB data for the dataset.
        dataset_type_id (int): Foreign key referencing the dataset type.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.

    Relationships:
        dataset_type (DatasetTypeModel): Relationship to the dataset type.
    """

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    collection_date: Mapped[date] = mapped_column(DATE, default=date.today)
    dataset_name: Mapped[str] = mapped_column(String(255))
    dataset_info: Mapped[dict] = mapped_column(JSONB, default={})
    dataset_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("gemini.dataset_types.id"), default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("dataset_name"),
        Index("idx_datasets_info", "dataset_info", postgresql_using="GIN"),
    )

    dataset_type = relationship("DatasetTypeModel", lazy="selectin")
