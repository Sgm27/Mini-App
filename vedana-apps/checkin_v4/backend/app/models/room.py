from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_number = Column(String(50), nullable=False, unique=True)
    room_type = Column(String(50), nullable=False)
    building = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assignments = relationship("RoomAssignment", back_populates="room")


class RoomAssignment(Base):
    __tablename__ = "room_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    released_at = Column(DateTime, nullable=True)

    checkin = relationship("Checkin")
    room = relationship("Room", back_populates="assignments")
