from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import UUID, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from gemini.db.core.base import ViewBaseModel


class PlotAccessionViewModel(ViewBaseModel):

    __tablename__ = 'plot_accession_view'

    plot_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    plot_number : Mapped[int] = mapped_column(Integer)
    plot_row_number : Mapped[int] = mapped_column(Integer)
    plot_column_number : Mapped[int] = mapped_column(Integer)
    plot_info : Mapped[dict] = mapped_column(JSONB)
    plot_geometry_info : Mapped[dict] = mapped_column(JSONB)
    experiment_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    experiment_name : Mapped[str] = mapped_column(String)
    season_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    season_name : Mapped[str] = mapped_column(String)
    site_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    site_name : Mapped[str] = mapped_column(String)
    accession_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    accession_name : Mapped[str] = mapped_column(String)
    accession_info : Mapped[dict] = mapped_column(JSONB)
    population_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    population_name : Mapped[str] = mapped_column(String)
    population_info : Mapped[dict] = mapped_column(JSONB)
