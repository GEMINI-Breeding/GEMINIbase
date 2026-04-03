from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import UUID, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import TIMESTAMP, DATE
from gemini.db.core.base import BaseModel
from datetime import datetime, date


class ModelRecordsIMMVModel(BaseModel):

    __tablename__ = 'model_records_immv'

    id : Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp : Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    collection_date : Mapped[date] = mapped_column(DATE, default=date.today)
    dataset_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    dataset_name : Mapped[str] = mapped_column(String)
    model_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    model_name : Mapped[str] = mapped_column(String)
    model_data : Mapped[dict] = mapped_column(JSONB)
    experiment_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    experiment_name : Mapped[str] = mapped_column(String)
    season_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    season_name : Mapped[str] = mapped_column(String)
    site_id : Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    site_name : Mapped[str] = mapped_column(String)
    record_file : Mapped[str] = mapped_column(String)
    record_info : Mapped[dict] = mapped_column(JSONB)

