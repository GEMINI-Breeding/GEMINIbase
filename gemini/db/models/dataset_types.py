"""
SQLAlchemy model for DatasetType entities in the GEMINIbase database.
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

class DatasetTypeModel(BaseModel):
    """
    Represents a type of dataset in the GEMINIbase database.

    Attributes:
        id (int): Unique integer identifier for the dataset type.
        dataset_type_name (str): The name of the dataset type (e.g., "Phenotypic", "Genotypic").
        dataset_type_info (dict): Additional JSONB data for the dataset type.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "dataset_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_type_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("dataset_type_name"),
        Index("idx_dataset_types_info", "dataset_type_info", postgresql_using="GIN"),
    )
