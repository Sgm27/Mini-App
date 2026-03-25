from typing import List, Optional

from pydantic import BaseModel


# ── Category ──────────────────────────────────────────────────────────────────

class DanhMucMonOut(BaseModel):
    id: int
    ten_danh_muc: str
    thu_tu: int
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Dish ──────────────────────────────────────────────────────────────────────

class MonAnOut(BaseModel):
    id: int
    ten_mon: str
    gia: float
    hinh_anh: Optional[str] = None
    mo_ta: Optional[str] = None
    danh_muc_id: int
    danh_muc_ten: Optional[str] = None
    danh_muc_icon: Optional[str] = None
    active: bool
    co_the_phuc_vu: bool = True
    thieu_nguyen_lieu: List[str] = []

    model_config = {"from_attributes": True}


# ── Availability check ────────────────────────────────────────────────────────

class CartItem(BaseModel):
    mon_an_id: int
    so_luong: int


class MonAnAvailability(BaseModel):
    mon_an_id: int
    co_the_phuc_vu: bool
    thieu_nguyen_lieu: List[str] = []


class ThieuNguyenLieu(BaseModel):
    id: int
    ten: str
    don_vi: str
    ton_kho: float
    can_them: float


class CheckAvailabilityRequest(BaseModel):
    items: List[CartItem]


class CheckAvailabilityResponse(BaseModel):
    co_the_phuc_vu_tat_ca: bool
    thieu_nguyen_lieu: List[ThieuNguyenLieu] = []
    mon_an: List[MonAnAvailability] = []


# ── Ingredient / Inventory ────────────────────────────────────────────────────

class NguyenLieuOut(BaseModel):
    id: int
    ten_nguyen_lieu: str
    don_vi: str
    so_luong_ton: float
    nguong_canh_bao: float
    canh_bao_thap: bool = False

    model_config = {"from_attributes": True}


class NguyenLieuUpdate(BaseModel):
    so_luong_ton: float
    nguong_canh_bao: Optional[float] = None


class NguyenLieuCreate(BaseModel):
    ten_nguyen_lieu: str
    don_vi: str
    so_luong_ton: float = 0
    nguong_canh_bao: float = 0


# ── Order ─────────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    ma_ban: Optional[str] = None
    items: List[CartItem]
    ghi_chu: Optional[str] = None


class ChiTietDonHangOut(BaseModel):
    mon_an_id: int
    ten_mon: str
    so_luong: int
    don_gia: float
    thanh_tien: float

    model_config = {"from_attributes": True}


class DonHangOut(BaseModel):
    id: int
    ma_ban: Optional[str] = None
    trang_thai: str
    tong_tien: float
    ghi_chu: Optional[str] = None
    chi_tiet: List[ChiTietDonHangOut] = []
    created_at: str

    model_config = {"from_attributes": True}
