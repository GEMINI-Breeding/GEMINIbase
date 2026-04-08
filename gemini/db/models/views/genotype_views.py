"""
SQLAlchemy view models for Genotype-related views in the GEMINI database.
"""

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import UUID, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from gemini.db.core.base import ViewBaseModel


class ExperimentGenotypesViewModel(ViewBaseModel):

    __tablename__ = 'experiment_genotypes_view'

    experiment_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    experiment_name: Mapped[str] = mapped_column(String)
    experiment_info: Mapped[dict] = mapped_column(JSONB)
    experiment_start_date: Mapped[str] = mapped_column(String)
    experiment_end_date: Mapped[str] = mapped_column(String)
    genotype_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    genotype_name: Mapped[str] = mapped_column(String)
    genotype_info: Mapped[dict] = mapped_column(JSONB)
