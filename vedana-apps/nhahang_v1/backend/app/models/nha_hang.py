from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DanhMucMon(Base):
    __tablename__ = "danh_muc_mon"

    id = Column(Integer, primary_key=True, index=True)
    ten_danh_muc = Column(String(100), nullable=False)
    thu_tu = Column(Integer, default=0)
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mon_an = relationship("MonAn", back_populates="danh_muc")


class MonAn(Base):
    __tablename__ = "mon_an"

    id = Column(Integer, primary_key=True, index=True)
    ten_mon = Column(String(200), nullable=False)
    gia = Column(Numeric(10, 0), nullable=False)
    hinh_anh = Column(String(500), nullable=True)
    mo_ta = Column(Text, nullable=True)
    danh_muc_id = Column(Integer, ForeignKey("danh_muc_mon.id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    danh_muc = relationship("DanhMucMon", back_populates="mon_an")
    cong_thuc = relationship("CongThucMon", back_populates="mon_an")
    chi_tiet_don_hang = relationship("ChiTietDonHang", back_populates="mon_an")


class NguyenLieu(Base):
    __tablename__ = "nguyen_lieu"

    id = Column(Integer, primary_key=True, index=True)
    ten_nguyen_lieu = Column(String(200), nullable=False)
    don_vi = Column(String(50), nullable=False)
    so_luong_ton = Column(Numeric(10, 3), default=0)
    nguong_canh_bao = Column(Numeric(10, 3), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cong_thuc = relationship("CongThucMon", back_populates="nguyen_lieu")


class CongThucMon(Base):
    __tablename__ = "cong_thuc_mon"

    id = Column(Integer, primary_key=True, index=True)
    mon_an_id = Column(Integer, ForeignKey("mon_an.id"), nullable=False)
    nguyen_lieu_id = Column(Integer, ForeignKey("nguyen_lieu.id"), nullable=False)
    so_luong_can = Column(Numeric(10, 3), nullable=False)

    __table_args__ = (UniqueConstraint("mon_an_id", "nguyen_lieu_id", name="uq_mon_nguyen_lieu"),)

    mon_an = relationship("MonAn", back_populates="cong_thuc")
    nguyen_lieu = relationship("NguyenLieu", back_populates="cong_thuc")


class DonHang(Base):
    __tablename__ = "don_hang"

    id = Column(Integer, primary_key=True, index=True)
    ma_ban = Column(String(50), nullable=True)
    trang_thai = Column(
        Enum("cho_xac_nhan", "da_xac_nhan", "da_huy"), default="cho_xac_nhan"
    )
    tong_tien = Column(Numeric(10, 0), default=0)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chi_tiet = relationship("ChiTietDonHang", back_populates="don_hang")


class ChiTietDonHang(Base):
    __tablename__ = "chi_tiet_don_hang"

    id = Column(Integer, primary_key=True, index=True)
    don_hang_id = Column(Integer, ForeignKey("don_hang.id"), nullable=False)
    mon_an_id = Column(Integer, ForeignKey("mon_an.id"), nullable=False)
    so_luong = Column(Integer, nullable=False, default=1)
    don_gia = Column(Numeric(10, 0), nullable=False)

    don_hang = relationship("DonHang", back_populates="chi_tiet")
    mon_an = relationship("MonAn", back_populates="chi_tiet_don_hang")
