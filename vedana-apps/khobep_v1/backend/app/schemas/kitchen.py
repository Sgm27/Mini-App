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


# ─── Import ──────────────────────────────────────────────────
class ImportItemIn(BaseModel):
    material_id: int
    quantity: float = Field(..., gt=0)
    unit: str


class ImportItemOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    quantity: float
    unit: str

    model_config = {"from_attributes": True}


class ImportRecordCreate(BaseModel):
    supplier_name: str | None = None
    notes: str | None = None
    image_url: str | None = None
    created_by: str = "Nhân viên kho"
    items: list[ImportItemIn]


class ImportRecordOut(BaseModel):
    id: int
    supplier_name: str | None
    notes: str | None
    image_url: str | None
    created_by: str
    created_at: datetime
    items: list[ImportItemOut] = []

    model_config = {"from_attributes": True}


class ImportRecordSummary(BaseModel):
    id: int
    supplier_name: str | None
    created_by: str
    created_at: datetime
    item_count: int
    total_items_summary: str

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


# ─── OCR / Voice ─────────────────────────────────────────────
class ExtractedItem(BaseModel):
    name: str
    quantity: float
    unit: str
    material_id: int | None = None


class OcrExtractRequest(BaseModel):
    image_base64: str


class VoiceExtractRequest(BaseModel):
    transcript: str


class ExtractResponse(BaseModel):
    items: list[ExtractedItem]
    raw_text: str | None = None


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
