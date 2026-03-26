"""SQLAlchemy models for khobep_v1 — using shared nhahang_v1 database schema."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DanhMucMon(Base):
    """Menu categories — shared table, read-only from khobep."""
    __tablename__ = "danh_muc_mon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ten_danh_muc: Mapped[str] = mapped_column(String(100), nullable=False)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    mon_an: Mapped[list["MonAn"]] = relationship("MonAn", back_populates="danh_muc")


class MonAn(Base):
    """Dishes — shared table, khobep reads subset of columns."""
    __tablename__ = "mon_an"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ten_mon: Mapped[str] = mapped_column(String(200), nullable=False)
    gia: Mapped[Decimal] = mapped_column(Numeric(10, 0), nullable=False)
    hinh_anh: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mo_ta: Mapped[str | None] = mapped_column(Text, nullable=True)
    danh_muc_id: Mapped[int] = mapped_column(Integer, ForeignKey("danh_muc_mon.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    danh_muc: Mapped["DanhMucMon"] = relationship("DanhMucMon", back_populates="mon_an")
    cong_thuc: Mapped[list["CongThucMon"]] = relationship("CongThucMon", back_populates="mon_an")


class NguyenLieu(Base):
    """Ingredients with inline stock — the core shared table."""
    __tablename__ = "nguyen_lieu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ten_nguyen_lieu: Mapped[str] = mapped_column(String(200), nullable=False)
    don_vi: Mapped[str] = mapped_column(String(50), nullable=False)
    so_luong_ton: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    nguong_canh_bao: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    cong_thuc: Mapped[list["CongThucMon"]] = relationship("CongThucMon", back_populates="nguyen_lieu")
    chi_tiet_nhap: Mapped[list["ChiTietNhapKho"]] = relationship("ChiTietNhapKho", back_populates="nguyen_lieu")


class CongThucMon(Base):
    """Recipe formulas — shared table, read-only from khobep."""
    __tablename__ = "cong_thuc_mon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mon_an_id: Mapped[int] = mapped_column(Integer, ForeignKey("mon_an.id"), nullable=False)
    nguyen_lieu_id: Mapped[int] = mapped_column(Integer, ForeignKey("nguyen_lieu.id"), nullable=False)
    so_luong_can: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    mon_an: Mapped["MonAn"] = relationship("MonAn", back_populates="cong_thuc")
    nguyen_lieu: Mapped["NguyenLieu"] = relationship("NguyenLieu", back_populates="cong_thuc")


class PhieuNhapKho(Base):
    """Import receipt header — khobep-owned table."""
    __tablename__ = "phieu_nhap_kho"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(Text, nullable=True)
    hinh_anh_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nguoi_nhap: Mapped[str] = mapped_column(String(100), default="Nhan vien kho")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["ChiTietNhapKho"]] = relationship("ChiTietNhapKho", back_populates="phieu_nhap", cascade="all, delete-orphan")


class ChiTietNhapKho(Base):
    """Import receipt line items — khobep-owned table."""
    __tablename__ = "chi_tiet_nhap_kho"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phieu_nhap_id: Mapped[int] = mapped_column(Integer, ForeignKey("phieu_nhap_kho.id", ondelete="CASCADE"))
    nguyen_lieu_id: Mapped[int] = mapped_column(Integer, ForeignKey("nguyen_lieu.id", ondelete="RESTRICT"))
    so_luong: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    don_vi: Mapped[str] = mapped_column(String(50), nullable=False)

    phieu_nhap: Mapped["PhieuNhapKho"] = relationship("PhieuNhapKho", back_populates="items")
    nguyen_lieu: Mapped["NguyenLieu"] = relationship("NguyenLieu", back_populates="chi_tiet_nhap")
