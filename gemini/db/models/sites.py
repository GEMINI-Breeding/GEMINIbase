"""
SQLAlchemy model for Site entities in the GEMINIbase database.
"""

from sqlalchemy import (
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import BaseModel

from datetime import datetime
import uuid



class SiteModel(BaseModel):
  """
  Represents a site in the GEMINIbase database.

  Attributes:
    id (uuid.UUID): Unique identifier for the site.
    site_name (str): The name of the site.
    site_city (str): The city where the site is located.
    site_state (str): The state where the site is located.
    site_country (str): The country where the site is located.
    site_info (dict): Additional JSONB data for the site.
    created_at (datetime): Timestamp when the record was created.
    updated_at (datetime): Timestamp when the record was last updated.
  """
  __tablename__ = 'sites'

  id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
  site_name: Mapped[str] = mapped_column(String(255), nullable=False)
  site_city: Mapped[str] = mapped_column(String(255), default='')
  site_state: Mapped[str] = mapped_column(String(255), default='')
  site_country: Mapped[str] = mapped_column(String(255), default='')
  site_info: Mapped[dict] = mapped_column(JSONB, default={})
  created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
  updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)


  __table_args__ = (
    UniqueConstraint('site_name', 'site_city', 'site_state', 'site_country'),
    Index('idx_sites_info', 'site_info', postgresql_using='GIN')
  )
