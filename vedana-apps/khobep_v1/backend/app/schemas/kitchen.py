"""Pydantic schemas for khobep_v1 API.

Internal field names match the Vietnamese DB columns.
API responses use English field names for frontend backward compatibility.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Material (NguyenLieu) ──────────────────────────────────
class MaterialBase(BaseModel):
    name: str
    unit: str
    min_stock: float = 0.0


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    min_stock: float | None = None


class MaterialOut(MaterialBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialWithStock(MaterialOut):
    quantity: float = 0.0
    stock_status: str = "ok"  # ok | low | out


# ─── Inventory ───────────────────────────────────────────────
class InventoryOut(BaseModel):
    material_id: int
    material_name: str
    unit: str
    quantity: float
    min_stock: float
    stock_status: str  # ok | low | out
    last_updated: datetime | None = None

    model_config = {"from_attributes": True}


# ─── Import ──────────────────────────────────────
class ImportItemIn(BaseModel):
    material_id: int | None = None
    quantity: float = Field(..., gt=0)
    unit: str
    item_code: str | None = None
    item_name: str | None = None
    unit_price: float | None = None
    amount: float | None = None
    location: str | None = None
    acc_no: str | None = None


class ImportItemOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    quantity: float
    unit: str
    item_code: str | None = None
    item_name: str | None = None
    unit_price: float | None = None
    amount: float | None = None
    location: str | None = None
    acc_no: str | None = None

    model_config = {"from_attributes": True}


class ImportRecordCreate(BaseModel):
    supplier_name: str | None = None
    notes: str | None = None
    image_url: str | None = None
    created_by: str = "Nhân viên kho"
    # Vedana receiving note header
    receipt_date: str | None = None
    description: str | None = None
    vendor_name: str | None = None
    period: str | None = None
    voucher_no: str | None = None
    invoice_serial: str | None = None
    invoice_no: str | None = None
    items: list[ImportItemIn]


class ImportRecordOut(BaseModel):
    id: int
    supplier_name: str | None
    notes: str | None
    image_url: str | None
    created_by: str
    created_at: datetime
    receipt_date: str | None = None
    description: str | None = None
    vendor_name: str | None = None
    period: str | None = None
    voucher_no: str | None = None
    invoice_serial: str | None = None
    invoice_no: str | None = None
    items: list[ImportItemOut] = []

    model_config = {"from_attributes": True}


class ImportRecordSummary(BaseModel):
    id: int
    supplier_name: str | None
    created_by: str
    created_at: datetime
    item_count: int
    total_items_summary: str
    vendor_name: str | None = None
    voucher_no: str | None = None

    model_config = {"from_attributes": True}


# ─── Dish ────────────────────────────────────────────────────
class RecipeIngredientOut(BaseModel):
    material_id: int
    material_name: str
    quantity_required: float
    unit: str
    current_stock: float = 0.0
    is_sufficient: bool = True

    model_config = {"from_attributes": True}


class DishOut(BaseModel):
    id: int
    name: str
    category: str | None
    is_available: bool
    recipe_ingredients: list[RecipeIngredientOut] = []

    model_config = {"from_attributes": True}


class DishStatusOut(BaseModel):
    id: int
    name: str
    category: str | None
    is_available: bool
    missing_ingredients: list[str] = []

    model_config = {"from_attributes": True}


# ─── OCR / Voice ─────────────────────────────────
class ExtractedItem(BaseModel):
    name: str
    quantity: float
    unit: str
    material_id: int | None = None


class ReceiptHeader(BaseModel):
    receipt_date: str | None = None
    description: str | None = None
    vendor_name: str | None = None
    period: str | None = None
    voucher_no: str | None = None
    invoice_serial: str | None = None
    invoice_no: str | None = None


class ReceiptItem(BaseModel):
    item_code: str | None = None
    name: str
    unit: str
    quantity: float
    unit_price: float | None = None
    amount: float | None = None
    location: str | None = None
    acc_no: str | None = None
    material_id: int | None = None
    is_new: bool = False


class ReceiptSummary(BaseModel):
    sub_amount: float | None = None
    discount: float | None = None
    vat: float | None = None
    total_amount: float | None = None


class OcrExtractRequest(BaseModel):
    image_base64: str


class VoiceExtractRequest(BaseModel):
    transcript: str


class OcrReceiptResponse(BaseModel):
    header: ReceiptHeader
    items: list[ReceiptItem]
    summary: ReceiptSummary | None = None


class ExtractResponse(BaseModel):
    items: list[ExtractedItem]
    raw_text: str | None = None


# ─── Orders (kitchen workflow) ──────────────────────────────
class OrderItemOut(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    table_number: str | None = None
    status: str
    total_amount: float
    notes: str | None = None
    reject_reason: str | None = None
    items: list[OrderItemOut] = []
    created_at: datetime
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RejectOrderRequest(BaseModel):
    reject_reason: str


# ─── Reports ─────────────────────────────────────────────────
class ReportOverview(BaseModel):
    total_materials: int
    total_available_dishes: int
    total_unavailable_dishes: int
    low_stock_count: int
    out_of_stock_count: int
    today_import_count: int
    today_import_items: int


class LowStockItem(BaseModel):
    material_id: int
    material_name: str
    unit: str
    quantity: float
    min_stock: float
    status: str  # low | out
