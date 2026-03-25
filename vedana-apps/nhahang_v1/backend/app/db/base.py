"""Import models here so Alembic can discover them."""

from app.db.base_class import Base  # noqa: F401
from app.models.nha_hang import (  # noqa: F401
    ChiTietDonHang,
    CongThucMon,
    DanhMucMon,
    DonHang,
    MonAn,
    NguyenLieu,
)

