"""
SQLAlchemy model for Season entities in the GEMINI database.
"""

"""
SQLAlchemy model for Season entities in the GEMINI database.
"""

from sqlalchemy import JSON, String, TIMESTAMP, UniqueConstraint, Index, ForeignKey, CheckConstraint, DATE
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime, date
import uuid


class SeasonModel(BaseModel):
    """
    Represents a season in the GEMINI database.

    Attributes:
        id (uuid.UUID): Unique identifier for the season.
        experiment_id (uuid.UUID): Foreign key referencing the experiment to which the season belongs.
        season_name (str): The name of the season.
        season_info (dict): Additional JSONB data for the season.
        season_start_date (date): The start date of the season.
        season_end_date (date): The end date of the season.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
    """
    __tablename__ = "seasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('gemini.experiments.id'))
    season_name: Mapped[str] = mapped_column(String(255), nullable=False)
    season_info: Mapped[dict] = mapped_column(JSONB, default={})
    season_start_date: Mapped[date] = mapped_column(DATE, nullable=False, default=date.today)
    season_end_date: Mapped[date] = mapped_column(DATE)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('experiment_id', 'season_name'),
        CheckConstraint('season_start_date <= season_end_date'),
        CheckConstraint('season_end_date >= season_start_date'),
        Index('idx_seasons_info', 'season_info', postgresql_using='GIN')
    )
