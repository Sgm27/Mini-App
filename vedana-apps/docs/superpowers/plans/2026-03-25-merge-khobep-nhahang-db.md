# Merge khobep_v1 + nhahang_v1 Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make khobep_v1 (warehouse) and nhahang_v1 (restaurant) share the same `nhahang_v1` MySQL database so imports and orders affect the same inventory in real-time.

**Architecture:** Add 2 import tables to nhahang_v1's DB. Rewrite khobep_v1's backend (models, schemas, services, routes) to use nhahang_v1's Vietnamese-named tables. nhahang_v1 code is untouched.

**Tech Stack:** FastAPI, SQLAlchemy 2, PyMySQL, MySQL (RDS)

**Spec:** `docs/superpowers/specs/2026-03-25-merge-khobep-nhahang-db-design.md`

---

## File Structure

### Files to CREATE
- `nhahang_v1/database/004_nhap_kho.sql` — migration: new import tables + expanded seed data

### Files to MODIFY (all in `khobep_v1/backend/`)
- `app/models/kitchen.py` — full rewrite: 6 old models → 6 new models using nhahang table names
- `app/schemas/kitchen.py` — update internal field names, keep API-compatible JSON output
- `app/services/inventory_service.py` — rewrite all queries to use new models + atomic updates
- `app/api/routes/materials.py` — update model imports and queries
- `app/api/routes/imports.py` — update model import for get_import query
- `app/api/routes/ocr.py` — update `_match_materials` to use `NguyenLieu`
- `app/api/routes/reports.py` — rewrite all queries to use new models
- `.env` — change `MYSQL_DATABASE=khobep_v1` → `MYSQL_DATABASE=nhahang_v1`

### Files NOT changing (verified — only use service-layer functions, no direct model queries)
- `khobep_v1/backend/app/main.py`
- `khobep_v1/backend/app/core/config.py`
- `khobep_v1/backend/app/db/base_class.py`
- `khobep_v1/backend/app/db/session.py`
- `khobep_v1/backend/app/api/deps.py`
- `khobep_v1/backend/app/api/routes/health.py`
- `khobep_v1/backend/app/api/routes/upload.py`
- `khobep_v1/backend/app/api/routes/inventory.py` — uses service functions only, works unchanged
- `khobep_v1/backend/app/api/routes/dishes.py` — uses service functions only, works unchanged
- `khobep_v1/backend/app/services/ocr_service.py` — no model imports, works unchanged
- `khobep_v1/backend/app/api/routes/__init__.py`
- `khobep_v1/frontend/` — entire frontend unchanged
- `nhahang_v1/` — entire app unchanged

---

## Task 1: Database Migration

Create the migration that adds import tables and expands ingredient seed data in nhahang_v1's database.

**Files:**
- Create: `nhahang_v1/database/004_nhap_kho.sql`

- [ ] **Step 1: Create migration file**

```sql
-- 004_nhap_kho.sql: Add warehouse import tables + expand ingredients for khobep integration

-- Import receipt header
CREATE TABLE IF NOT EXISTS phieu_nhap_kho (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nha_cung_cap VARCHAR(200) DEFAULT NULL COMMENT 'Tên nhà cung cấp/người giao',
  ghi_chu TEXT DEFAULT NULL,
  hinh_anh_url VARCHAR(500) DEFAULT NULL COMMENT 'Ảnh hoá đơn',
  nguoi_nhap VARCHAR(100) DEFAULT 'Nhan vien kho',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Import receipt line items
CREATE TABLE IF NOT EXISTS chi_tiet_nhap_kho (
  id INT AUTO_INCREMENT PRIMARY KEY,
  phieu_nhap_id INT NOT NULL,
  nguyen_lieu_id INT NOT NULL,
  so_luong DECIMAL(10,3) NOT NULL,
  don_vi VARCHAR(50) NOT NULL,
  FOREIGN KEY (phieu_nhap_id) REFERENCES phieu_nhap_kho(id) ON DELETE CASCADE,
  FOREIGN KEY (nguyen_lieu_id) REFERENCES nguyen_lieu(id) ON DELETE RESTRICT,
  INDEX idx_phieu_nhap (phieu_nhap_id),
  INDEX idx_nguyen_lieu (nguyen_lieu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Expand nguyen_lieu with common kitchen ingredients missing from nhahang seed data
-- (needed for khobep OCR matching)
INSERT IGNORE INTO nguyen_lieu (ten_nguyen_lieu, don_vi, so_luong_ton, nguong_canh_bao) VALUES
  ('Mực',         'kg',   1.500, 1.0),
  ('Giá đỗ',      'kg',   2.000, 1.0),
  ('Dầu ăn',      'lít',  3.000, 2.0),
  ('Nước mắm',    'lít',  2.000, 1.0),
  ('Muối',         'kg',   2.000, 1.0),
  ('Đường',        'kg',   2.000, 1.0),
  ('Tiêu',         'kg',   0.500, 0.2),
  ('Mì chính',    'kg',   0.500, 0.3),
  ('Hành lá',      'bó',   8.000, 5.0),
  ('Hành tây',     'kg',   2.000, 1.0),
  ('Tỏi',          'kg',   1.000, 0.5),
  ('Gừng',         'kg',   0.500, 0.3),
  ('Ớt',           'kg',   0.300, 0.2),
  ('Cà chua',      'kg',   2.000, 1.0),
  ('Rau cải',      'bó',  12.000, 5.0);

INSERT IGNORE INTO schema_migrations (version) VALUES ('004_nhap_kho');
```

- [ ] **Step 2: Run the migration against nhahang_v1 database**

```bash
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -u admin -psonktx12345 nhahang_v1 < nhahang_v1/database/004_nhap_kho.sql
```

Expected: tables `phieu_nhap_kho` and `chi_tiet_nhap_kho` created, ~15 new ingredient rows inserted.

- [ ] **Step 3: Verify migration**

```bash
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -u admin -psonktx12345 nhahang_v1 -e "SHOW TABLES; SELECT COUNT(*) as ingredient_count FROM nguyen_lieu;"
```

Expected: 8 tables total (6 existing + 2 new), ~33 ingredients (18 original + ~15 new).

- [ ] **Step 4: Commit**

```bash
git add nhahang_v1/database/004_nhap_kho.sql
git commit -m "feat: add warehouse import tables and expanded ingredients to nhahang_v1 DB"
```

---

## Task 2: Rewrite khobep_v1 Models

Replace all 6 SQLAlchemy models to match nhahang_v1's table schema exactly.

**Files:**
- Modify: `khobep_v1/backend/app/models/kitchen.py` (full rewrite)

- [ ] **Step 1: Rewrite models file**

Replace the entire contents of `khobep_v1/backend/app/models/kitchen.py` with:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/backend/app/models/kitchen.py
git commit -m "refactor: rewrite khobep models to use nhahang_v1 shared DB schema"
```

---

## Task 3: Update khobep_v1 Schemas

Update Pydantic schemas to work with new models. Keep API JSON field names English for frontend backward compatibility.

**Files:**
- Modify: `khobep_v1/backend/app/schemas/kitchen.py` (full rewrite)

- [ ] **Step 1: Rewrite schemas file**

Replace the entire contents of `khobep_v1/backend/app/schemas/kitchen.py` with:

```python
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
```

Note: Schemas are structurally identical to the old ones. The only change is that **services** will now construct these from new model fields. No schema field was renamed — the API contract is preserved.

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/backend/app/schemas/kitchen.py
git commit -m "refactor: update khobep schemas (unchanged API contract, ready for new models)"
```

---

## Task 4: Rewrite khobep_v1 inventory_service.py

The biggest change — rewrite all queries to use `NguyenLieu`, `MonAn`, `CongThucMon`, `PhieuNhapKho`, `ChiTietNhapKho`. Use atomic SQL for stock updates.

**Files:**
- Modify: `khobep_v1/backend/app/services/inventory_service.py` (full rewrite)

- [ ] **Step 1: Rewrite inventory_service.py**

Replace the entire contents with:

```python
"""Inventory and import business logic — using shared nhahang_v1 DB."""

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.kitchen import (
    ChiTietNhapKho, CongThucMon, MonAn, NguyenLieu, PhieuNhapKho,
)
from app.schemas.kitchen import (
    ImportRecordCreate, ImportRecordOut, ImportItemOut,
    InventoryOut, MaterialWithStock,
)


def _stock_status(quantity: float, min_stock: float) -> str:
    if quantity <= 0:
        return "out"
    if min_stock > 0 and quantity < min_stock:
        return "low"
    return "ok"


# ─── Materials ───────────────────────────────────────────────

def get_all_materials_with_stock(db: Session) -> list[MaterialWithStock]:
    materials = db.query(NguyenLieu).all()
    result = []
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        result.append(MaterialWithStock(
            id=mat.id,
            name=mat.ten_nguyen_lieu,
            unit=mat.don_vi,
            min_stock=min_s,
            created_at=mat.created_at,
            quantity=qty,
            stock_status=_stock_status(qty, min_s),
        ))
    return result


def create_material(db: Session, name: str, unit: str, min_stock: float = 0.0) -> NguyenLieu:
    mat = NguyenLieu(
        ten_nguyen_lieu=name,
        don_vi=unit,
        nguong_canh_bao=Decimal(str(min_stock)),
        so_luong_ton=Decimal("0"),
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


# ─── Inventory ───────────────────────────────────────────────

def get_inventory(db: Session) -> list[InventoryOut]:
    materials = db.query(NguyenLieu).all()
    result = []
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        result.append(InventoryOut(
            material_id=mat.id,
            material_name=mat.ten_nguyen_lieu,
            unit=mat.don_vi,
            quantity=qty,
            min_stock=min_s,
            stock_status=_stock_status(qty, min_s),
            last_updated=mat.updated_at,
        ))
    return result


# ─── Imports ─────────────────────────────────────────────────

def create_import(db: Session, data: ImportRecordCreate) -> PhieuNhapKho:
    record = PhieuNhapKho(
        nha_cung_cap=data.supplier_name,
        ghi_chu=data.notes,
        hinh_anh_url=data.image_url,
        nguoi_nhap=data.created_by,
    )
    db.add(record)
    db.flush()

    for item_in in data.items:
        mat = db.query(NguyenLieu).filter(NguyenLieu.id == item_in.material_id).first()
        if not mat:
            continue

        # Add import line item
        import_item = ChiTietNhapKho(
            phieu_nhap_id=record.id,
            nguyen_lieu_id=item_in.material_id,
            so_luong=Decimal(str(item_in.quantity)),
            don_vi=item_in.unit,
        )
        db.add(import_item)

        # Unit conversion: g→kg, ml→lít
        qty = Decimal(str(item_in.quantity))
        unit_lower = item_in.unit.lower().strip()
        mat_unit_lower = mat.don_vi.lower().strip()
        if unit_lower == "g" and mat_unit_lower == "kg":
            qty = qty / 1000
        elif unit_lower == "ml" and mat_unit_lower in ("lít", "lit", "l"):
            qty = qty / 1000

        # Atomic stock update — avoids TOCTOU race
        db.execute(
            update(NguyenLieu)
            .where(NguyenLieu.id == item_in.material_id)
            .values(so_luong_ton=NguyenLieu.so_luong_ton + qty)
        )

    db.commit()
    db.refresh(record)

    # Recalculate dish availability
    recalculate_all_dishes(db)

    return record


def get_imports(db: Session, limit: int = 50, import_date: date | None = None) -> list[PhieuNhapKho]:
    q = db.query(PhieuNhapKho).order_by(PhieuNhapKho.created_at.desc())
    if import_date:
        q = q.filter(
            PhieuNhapKho.created_at >= datetime.combine(import_date, datetime.min.time()),
            PhieuNhapKho.created_at < datetime.combine(import_date, datetime.max.time()),
        )
    return q.limit(limit).all()


def build_import_out(record: PhieuNhapKho) -> ImportRecordOut:
    items_out = []
    for it in record.items:
        items_out.append(ImportItemOut(
            id=it.id,
            material_id=it.nguyen_lieu_id,
            material_name=it.nguyen_lieu.ten_nguyen_lieu if it.nguyen_lieu else "?",
            quantity=float(it.so_luong),
            unit=it.don_vi,
        ))
    return ImportRecordOut(
        id=record.id,
        supplier_name=record.nha_cung_cap,
        notes=record.ghi_chu,
        image_url=record.hinh_anh_url,
        created_by=record.nguoi_nhap,
        created_at=record.created_at,
        items=items_out,
    )


# ─── Dish Availability ───────────────────────────────────────

def recalculate_all_dishes(db: Session) -> None:
    dishes = db.query(MonAn).all()
    for dish in dishes:
        _recalc_dish(db, dish)
    db.commit()


def _recalc_dish(db: Session, dish: MonAn) -> None:
    """Check if all recipe ingredients are available in stock."""
    for ri in dish.cong_thuc:
        current_qty = float(ri.nguyen_lieu.so_luong_ton) if ri.nguyen_lieu else 0.0
        required = float(ri.so_luong_can)
        if current_qty < required:
            dish.active = False
            return
    dish.active = True


def get_dishes_with_status(db: Session) -> list[dict]:
    dishes = db.query(MonAn).all()
    result = []
    for dish in dishes:
        missing = []
        for ri in dish.cong_thuc:
            qty = float(ri.nguyen_lieu.so_luong_ton) if ri.nguyen_lieu else 0.0
            if qty < float(ri.so_luong_can):
                mat_name = ri.nguyen_lieu.ten_nguyen_lieu if ri.nguyen_lieu else "?"
                missing.append(mat_name)
        # Resolve category from danh_muc_mon relationship
        category = dish.danh_muc.ten_danh_muc if dish.danh_muc else None
        result.append({
            "id": dish.id,
            "name": dish.ten_mon,
            "category": category,
            "is_available": dish.active,
            "missing_ingredients": missing,
        })
    return result
```

Key changes from old code:
- `Material` → `NguyenLieu` with `.ten_nguyen_lieu`, `.don_vi`, `.nguong_canh_bao`, `.so_luong_ton`
- `Inventory` table removed — stock is inline on `NguyenLieu`
- `Dish` → `MonAn` with `.ten_mon`, `.active`, `.cong_thuc`
- `RecipeIngredient` → `CongThucMon` with `.so_luong_can`, `.nguyen_lieu`
- `ImportRecord` → `PhieuNhapKho`, `ImportItem` → `ChiTietNhapKho`
- `_recalc_dish()` no longer does unit conversion (recipes use same unit as ingredient)
- `create_import()` uses atomic `UPDATE ... SET so_luong_ton = so_luong_ton + qty`
- `get_dishes_with_status()` resolves category via `dish.danh_muc.ten_danh_muc`
- All `float` reads from DB wrapped in `float()` to convert from `Decimal`

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/backend/app/services/inventory_service.py
git commit -m "refactor: rewrite inventory_service to use shared nhahang DB schema"
```

---

## Task 5: Update khobep_v1 Routes

Update model imports and queries in all route files.

**Files:**
- Modify: `khobep_v1/backend/app/api/routes/materials.py`
- Modify: `khobep_v1/backend/app/api/routes/inventory.py`
- Modify: `khobep_v1/backend/app/api/routes/imports.py`
- Modify: `khobep_v1/backend/app/api/routes/ocr.py`
- Modify: `khobep_v1/backend/app/api/routes/reports.py`
- No change: `dishes.py` (only uses service functions, no direct model imports for queries)

- [ ] **Step 1: Update materials.py**

Replace entire file with:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import NguyenLieu
from app.schemas.kitchen import MaterialCreate, MaterialOut, MaterialUpdate, MaterialWithStock
from app.services.inventory_service import create_material, get_all_materials_with_stock

router = APIRouter(prefix="/materials")


@router.get("", response_model=list[MaterialWithStock])
def list_materials(db: Session = Depends(get_db)):
    return get_all_materials_with_stock(db)


@router.post("", response_model=MaterialOut, status_code=201)
def add_material(data: MaterialCreate, db: Session = Depends(get_db)):
    mat = create_material(db, name=data.name, unit=data.unit, min_stock=data.min_stock)
    return MaterialOut(
        id=mat.id,
        name=mat.ten_nguyen_lieu,
        unit=mat.don_vi,
        min_stock=float(mat.nguong_canh_bao),
        created_at=mat.created_at,
    )


@router.put("/{material_id}", response_model=MaterialOut)
def update_material(material_id: int, data: MaterialUpdate, db: Session = Depends(get_db)):
    mat = db.query(NguyenLieu).filter(NguyenLieu.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên vật liệu")
    if data.name is not None:
        mat.ten_nguyen_lieu = data.name
    if data.unit is not None:
        mat.don_vi = data.unit
    if data.min_stock is not None:
        mat.nguong_canh_bao = data.min_stock
    db.commit()
    db.refresh(mat)
    return MaterialOut(
        id=mat.id,
        name=mat.ten_nguyen_lieu,
        unit=mat.don_vi,
        min_stock=float(mat.nguong_canh_bao),
        created_at=mat.created_at,
    )


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: int, db: Session = Depends(get_db)):
    mat = db.query(NguyenLieu).filter(NguyenLieu.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên vật liệu")
    db.delete(mat)
    db.commit()
```

- [ ] **Step 2: Update imports.py**

Replace entire file with:

```python
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import PhieuNhapKho
from app.schemas.kitchen import ImportRecordCreate, ImportRecordOut
from app.services.inventory_service import build_import_out, create_import, get_imports

router = APIRouter(prefix="/imports")


@router.post("", response_model=ImportRecordOut, status_code=201)
def create_import_record(data: ImportRecordCreate, db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 nguyên vật liệu")
    record = create_import(db, data)
    return build_import_out(record)


@router.get("", response_model=list[ImportRecordOut])
def list_imports(limit: int = 50, import_date: date | None = None, db: Session = Depends(get_db)):
    records = get_imports(db, limit=limit, import_date=import_date)
    return [build_import_out(r) for r in records]


@router.get("/{import_id}", response_model=ImportRecordOut)
def get_import(import_id: int, db: Session = Depends(get_db)):
    record = db.query(PhieuNhapKho).filter(PhieuNhapKho.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập")
    return build_import_out(record)
```

- [ ] **Step 3: Update ocr.py**

Replace entire file with:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import NguyenLieu
from app.schemas.kitchen import ExtractResponse, OcrExtractRequest, VoiceExtractRequest
from app.services.ocr_service import extract_from_image, extract_from_voice

router = APIRouter(prefix="/ocr")


def _match_materials(items, db: Session):
    """Try to match extracted item names to known ingredients."""
    all_mats = db.query(NguyenLieu).all()
    mat_map = {m.ten_nguyen_lieu.lower(): m for m in all_mats}

    for item in items:
        name_lower = item.name.lower()
        # Exact match
        if name_lower in mat_map:
            item.material_id = mat_map[name_lower].id
            item.unit = mat_map[name_lower].don_vi
            continue
        # Partial match
        for mat_name, mat in mat_map.items():
            if name_lower in mat_name or mat_name in name_lower:
                item.material_id = mat.id
                item.unit = mat.don_vi
                break
    return items


@router.post("/image", response_model=ExtractResponse)
async def extract_from_invoice_image(data: OcrExtractRequest, db: Session = Depends(get_db)):
    try:
        items = await extract_from_image(data.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = _match_materials(items, db)
    return ExtractResponse(items=items)


@router.post("/voice", response_model=ExtractResponse)
async def extract_from_voice_transcript(data: VoiceExtractRequest, db: Session = Depends(get_db)):
    if not data.transcript.strip():
        raise HTTPException(status_code=400, detail="Nội dung giọng nói trống")

    items = await extract_from_voice(data.transcript)
    items = _match_materials(items, db)
    return ExtractResponse(items=items, raw_text=data.transcript)
```

- [ ] **Step 4: Update reports.py**

Replace entire file with:

```python
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import MonAn, NguyenLieu, PhieuNhapKho
from app.schemas.kitchen import LowStockItem, ReportOverview
from app.services.inventory_service import build_import_out, get_imports

router = APIRouter(prefix="/reports")


@router.get("/overview", response_model=ReportOverview)
def get_overview(db: Session = Depends(get_db)):
    total_materials = db.query(NguyenLieu).count()
    total_available = db.query(MonAn).filter(MonAn.active == True).count()  # noqa: E712
    total_unavailable = db.query(MonAn).filter(MonAn.active == False).count()  # noqa: E712

    low_stock = 0
    out_of_stock = 0
    materials = db.query(NguyenLieu).all()
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        if qty <= 0:
            out_of_stock += 1
        elif min_s > 0 and qty < min_s:
            low_stock += 1

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    today_records = db.query(PhieuNhapKho).filter(
        PhieuNhapKho.created_at >= today_start,
        PhieuNhapKho.created_at <= today_end,
    ).all()
    today_items = sum(len(r.items) for r in today_records)

    return ReportOverview(
        total_materials=total_materials,
        total_available_dishes=total_available,
        total_unavailable_dishes=total_unavailable,
        low_stock_count=low_stock,
        out_of_stock_count=out_of_stock,
        today_import_count=len(today_records),
        today_import_items=today_items,
    )


@router.get("/history")
def get_history(limit: int = 20, import_date: date | None = None, db: Session = Depends(get_db)):
    records = get_imports(db, limit=limit, import_date=import_date)
    return [build_import_out(r) for r in records]


@router.get("/low-stock", response_model=list[LowStockItem])
def get_low_stock(db: Session = Depends(get_db)):
    materials = db.query(NguyenLieu).all()
    result = []
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        if qty <= 0:
            status = "out"
        elif min_s > 0 and qty < min_s:
            status = "low"
        else:
            continue
        result.append(LowStockItem(
            material_id=mat.id,
            material_name=mat.ten_nguyen_lieu,
            unit=mat.don_vi,
            quantity=qty,
            min_stock=min_s,
            status=status,
        ))
    return result
```

- [ ] **Step 5: Commit all route changes**

```bash
git add khobep_v1/backend/app/api/routes/materials.py khobep_v1/backend/app/api/routes/imports.py khobep_v1/backend/app/api/routes/ocr.py khobep_v1/backend/app/api/routes/reports.py
git commit -m "refactor: update khobep routes to use shared nhahang DB models"
```

---

## Task 6: Update khobep_v1 Config

Point khobep to the shared nhahang_v1 database.

**Files:**
- Modify: `khobep_v1/backend/.env`

- [ ] **Step 1: Change database name in .env**

In `khobep_v1/backend/.env`, change:
```
MYSQL_DATABASE=khobep_v1
```
to:
```
MYSQL_DATABASE=nhahang_v1
```

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/backend/.env
git commit -m "config: point khobep_v1 to shared nhahang_v1 database"
```

---

## Task 7: Smoke Test

Verify both apps work against the shared database.

- [ ] **Step 1: Start khobep_v1 backend and test health**

```bash
cd khobep_v1/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 2701
```

In another terminal:
```bash
curl http://localhost:2701/api/health
```

Expected: `{"status": "ok", ...}`

- [ ] **Step 2: Test materials endpoint**

```bash
curl http://localhost:2701/api/materials | python3 -m json.tool | head -30
```

Expected: JSON array with ~33 ingredients, each having `id`, `name`, `unit`, `min_stock`, `quantity`, `stock_status`.

- [ ] **Step 3: Test dishes endpoint**

```bash
curl http://localhost:2701/api/dishes | python3 -m json.tool | head -30
```

Expected: JSON array with 18 dishes, each having `id`, `name`, `category` (resolved from danh_muc_mon), `is_available`, `missing_ingredients`.

- [ ] **Step 4: Test import creation**

```bash
curl -X POST http://localhost:2701/api/imports \
  -H "Content-Type: application/json" \
  -d '{"supplier_name":"Test","items":[{"material_id":1,"quantity":2.0,"unit":"kg"}]}'
```

Expected: 201 response with import record. Verify `nguyen_lieu` id=1 stock increased by 2.0.

- [ ] **Step 5: Test reports endpoint**

```bash
curl http://localhost:2701/api/reports/overview | python3 -m json.tool
```

Expected: Overview with `total_materials`, `total_available_dishes`, etc.

- [ ] **Step 6: Verify nhahang_v1 still works (if running)**

The nhahang_v1 app should see the same inventory. If nhahang is deployed on Lambda, test its existing endpoints to confirm no disruption.

- [ ] **Step 7: Verify no uncommitted changes**

```bash
git status
```

Expected: clean working tree (all changes committed in Tasks 1-6).
