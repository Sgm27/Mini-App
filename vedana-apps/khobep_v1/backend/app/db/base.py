"""Import models here so Alembic can discover them."""

from app.db.base_class import Base  # noqa: F401
from app.models.kitchen import ChiTietNhapKho, CongThucMon, DanhMucMon, MonAn, NguyenLieu, PhieuNhapKho  # noqa: F401

