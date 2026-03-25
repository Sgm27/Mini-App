import datetime as dt
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RoomReport(Base):
    __tablename__ = "room_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    note_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_urls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), default="submitted", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False
    )
