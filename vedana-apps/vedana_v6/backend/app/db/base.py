"""Import models here so Alembic can discover them."""

from app.db.base_class import Base  # noqa: F401
from app.models.room_report import RoomReport  # noqa: F401

