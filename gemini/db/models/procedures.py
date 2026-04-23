"""
SQLAlchemy model for Procedure entities in the GEMINIbase database.
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


class ProcedureModel(BaseModel):
    """
    Represents a procedure in the GEMINIbase database.

    Attributes:
        id (uuid.UUID): Unique identifier for the procedure.
        procedure_name (str): The name of the procedure.
        procedure_info (dict): Additional JSONB data for the procedure.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "procedures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    procedure_name: Mapped[str] = mapped_column(String(255))
    procedure_info: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        UniqueConstraint("procedure_name"),
        Index("idx_procedures_info", "procedure_info", postgresql_using="GIN"),
    )
