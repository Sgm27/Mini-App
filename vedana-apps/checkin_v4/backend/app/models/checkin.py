from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_code = Column(String(100), nullable=False)
    room_type = Column(String(100), nullable=True)
    num_guests = Column(Integer, nullable=False)
    arrival_date = Column(String(20), nullable=False)
    departure_date = Column(String(20), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    guests = relationship("Guest", back_populates="checkin", cascade="all, delete-orphan")


class Guest(Base):
    __tablename__ = "guests"
    __table_args__ = (
        UniqueConstraint("checkin_id", "identification_number", name="uq_vn_guest"),
        UniqueConstraint("checkin_id", "passport_number", name="uq_foreign_guest"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    guest_type = Column(String(20), nullable=False, default="vietnamese")
    full_name = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    identification_number = Column(String(50), nullable=True)
    passport_number = Column(String(50), nullable=True)
    nationality_code = Column(String(10), nullable=True)
    address = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    checkin = relationship("Checkin", back_populates="guests")
