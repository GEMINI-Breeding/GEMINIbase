from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import UUID, String, Integer, REAL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import TIMESTAMP, DATE
from gemini.db.core.base import BaseModel
from datetime import datetime, date


class TraitRecordsIMMVModel(BaseModel):

    __tablename__ = 'trait_records_immv'

    id : Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp : Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    collection_date : Mapped[date] = mapped_column(DATE, default=date.today)
    dataset_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    dataset_name : Mapped[str] = mapped_column(String)
    trait_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    trait_name : Mapped[str] = mapped_column(String)
    trait_value : Mapped[REAL] = mapped_column(REAL)
    experiment_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    experiment_name : Mapped[str] = mapped_column(String)
    season_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    season_name : Mapped[str] = mapped_column(String)
    site_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    site_name : Mapped[str] = mapped_column(String)
    plot_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    plot_number : Mapped[int] = mapped_column(Integer)
    plot_row_number : Mapped[int] = mapped_column(Integer)
    plot_column_number : Mapped[int] = mapped_column(Integer)
    record_info : Mapped[dict] = mapped_column(JSONB)

    