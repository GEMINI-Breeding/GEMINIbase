from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import UUID, JSON, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from gemini.db.core.base import ViewBaseModel


class PlotPopulationViewModel(ViewBaseModel):

    __tablename__ = 'plot_population_view'

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
    population_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    population_accession : Mapped[str] = mapped_column(String)
    population_name : Mapped[str] = mapped_column(String)
    population_info : Mapped[dict] = mapped_column(JSONB)