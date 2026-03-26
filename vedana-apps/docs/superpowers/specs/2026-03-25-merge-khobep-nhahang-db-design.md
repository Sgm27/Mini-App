# Design: Merge khobep_v1 + nhahang_v1 into Shared Database

## Goal

Unify the databases of two apps — `khobep_v1` (warehouse/inventory management) and `nhahang_v1` (restaurant ordering) — so that inventory imported via khobep is immediately visible to nhahang, and orders placed via nhahang deduct from the same inventory.

## Decision

Use `nhahang_v1` as the unified database. nhahang_v1's schema is kept as-is; two new tables are added for warehouse import functionality.

## Unified Schema

### Existing tables (nhahang_v1 — no changes)

| Table | Purpose |
|---|---|
| `danh_muc_mon` | Menu categories |
| `mon_an` | Dishes (name, price, image, description, category, active) |
| `nguyen_lieu` | Ingredients with inline stock (`so_luong_ton`, `nguong_canh_bao`) |
| `cong_thuc_mon` | Recipe formulas (dish → ingredient with quantity) |
| `don_hang` | Orders (table number, status, total, notes) |
| `chi_tiet_don_hang` | Order line items (order → dish with quantity, price) |

### New tables (for khobep import functionality)

```sql
CREATE TABLE phieu_nhap_kho (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nha_cung_cap VARCHAR(200) DEFAULT NULL,
  ghi_chu TEXT DEFAULT NULL,
  hinh_anh_url VARCHAR(500) DEFAULT NULL,
  nguoi_nhap VARCHAR(100) DEFAULT 'Nhan vien kho',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chi_tiet_nhap_kho (
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
```

**Design notes:**
- `ON DELETE RESTRICT` on `nguyen_lieu_id`: prevents deleting ingredients that have import history.
- Index on `nguyen_lieu_id`: supports queries for import history by ingredient.

### Column mapping (khobep old → unified new)

| khobep_v1 (old) | nhahang_v1 (unified) | Notes |
|---|---|---|
| `materials.name` | `nguyen_lieu.ten_nguyen_lieu` | |
| `materials.unit` | `nguyen_lieu.don_vi` | |
| `materials.min_stock` | `nguyen_lieu.nguong_canh_bao` | |
| `inventory.quantity` | `nguyen_lieu.so_luong_ton` | No separate inventory table |
| `dishes.name` | `mon_an.ten_mon` | |
| `dishes.category` (string) | `mon_an.danh_muc_id` (FK int) | khobep resolves via JOIN `danh_muc_mon.ten_danh_muc` |
| `dishes.is_available` | `mon_an.active` | |
| `recipe_ingredients.dish_id` | `cong_thuc_mon.mon_an_id` | |
| `recipe_ingredients.material_id` | `cong_thuc_mon.nguyen_lieu_id` | |
| `recipe_ingredients.quantity_required` | `cong_thuc_mon.so_luong_can` | |
| `recipe_ingredients.unit` | *(removed)* | `cong_thuc_mon` has no unit column; adopt nhahang's approach — recipe quantities always use same unit as `nguyen_lieu.don_vi` |
| `import_records.*` | `phieu_nhap_kho.*` | |
| `import_items.*` | `chi_tiet_nhap_kho.*` | |

**Key type mismatches resolved:**
- **`dishes.category` (string) → `mon_an.danh_muc_id` (int FK)**: khobep's API will JOIN `danh_muc_mon` and return `ten_danh_muc` as the category string for backward compatibility.
- **`recipe_ingredients.unit` removed**: nhahang's `cong_thuc_mon` has no unit column. khobep's unit conversion logic for recipes (g→kg, ml→lit) will be removed. Recipe `so_luong_can` is assumed to use the same unit as the ingredient's `don_vi`.
- **`mon_an` extra columns** (`gia`, `hinh_anh`, `mo_ta`, `danh_muc_id NOT NULL`): khobep only reads a subset of `mon_an` columns (ten_mon, active, danh_muc_id + relationship to danh_muc_mon). Extra columns are ignored.
- **Decimal vs Float**: nhahang uses `Numeric(10,3)` / `Decimal`. khobep's refactored code must use `Decimal` types consistently (not `Float`).

## Data Flow

```
[khobep_v1 app]                          [nhahang_v1 app]
     |                                         |
     | POST /api/imports                       | POST /api/orders
     |   → INSERT phieu_nhap_kho               |   → INSERT don_hang
     |   → INSERT chi_tiet_nhap_kho            |   → INSERT chi_tiet_don_hang
     |   → UPDATE nguyen_lieu.so_luong_ton +=  |   → UPDATE nguyen_lieu.so_luong_ton -=
     |                                         |
     +------------ nguyen_lieu (shared) -------+
```

**Concurrency note:** Both apps use a read-then-update pattern for `so_luong_ton`. This is a pre-existing TOCTOU risk (not introduced by the merge), but the merge increases probability since two apps now write the same rows. The refactored khobep `create_import()` should use atomic SQL: `UPDATE nguyen_lieu SET so_luong_ton = so_luong_ton + :qty WHERE id = :id` to avoid lost updates.

## Changes Required

### 1. Database migration (nhahang_v1)

- New file: `nhahang_v1/database/004_nhap_kho.sql`
- Creates `phieu_nhap_kho` and `chi_tiet_nhap_kho` tables
- References `nguyen_lieu.id` via FK with ON DELETE RESTRICT
- Expands `nguyen_lieu` seed data with missing ingredients from khobep (Muc, Gia do, Dau an, Nuoc mam, Muoi, Duong, Tieu, Mi chinh, etc.) so OCR matching works

### 2. khobep_v1 backend refactor

**Config:**
- `.env`: Change `MYSQL_DATABASE=khobep_v1` → `MYSQL_DATABASE=nhahang_v1`

**Models (`app/models/kitchen.py`):**
- Remove: `Material`, `Inventory`, `Dish`, `RecipeIngredient`
- Add: `NguyenLieu`, `MonAn`, `DanhMucMon`, `CongThucMon` (matching nhahang schema exactly)
- Rewrite: `ImportRecord` → `PhieuNhapKho`, `ImportItem` → `ChiTietNhapKho`

**Schemas (`app/schemas/kitchen.py`):**
- Update all Pydantic models to use Vietnamese field names internally
- Keep API response format compatible (English field names in JSON responses for backward compatibility with frontend)
- `DishStatusOut.category`: populated from `danh_muc_mon.ten_danh_muc` via JOIN

**Services (`app/services/inventory_service.py`):**
- `create_import()`: Use atomic SQL `UPDATE nguyen_lieu SET so_luong_ton = so_luong_ton + :qty WHERE id = :id` instead of read-update pattern. Preserve unit conversion for import items (g→kg, ml→lit) before updating `so_luong_ton`.
- `get_all_materials_with_stock()`: Read directly from `nguyen_lieu` (no JOIN with inventory)
- `recalculate_all_dishes()`: Use `mon_an` + `cong_thuc_mon`. Remove recipe unit conversion logic — recipe `so_luong_can` uses same unit as `nguyen_lieu.don_vi`.
- Remove inventory table operations entirely

**Services (`app/services/ocr_service.py`):**
- Material matching: query `nguyen_lieu.ten_nguyen_lieu` instead of `materials.name`

**Routes (`app/api/routes/*.py`):**
- `materials.py`: Update model imports (`Material` → `NguyenLieu`)
- `inventory.py`: Update model imports, remove inventory table queries
- `dishes.py`: Update to use `MonAn`, `CongThucMon`, JOIN `DanhMucMon`
- `imports.py`: Update to use `PhieuNhapKho`, `ChiTietNhapKho`
- `ocr.py`: Update material query to use `nguyen_lieu`
- `reports.py`: Update all model references

### 3. nhahang_v1 backend — NO code changes

nhahang_v1's code remains untouched. The only change is 2 new tables added to its database (no impact on existing queries). Note: `ON DELETE RESTRICT` on `chi_tiet_nhap_kho.nguyen_lieu_id` means nhahang cannot delete an ingredient that has import history — this is intentional to preserve audit trail.

### 4. khobep_v1 frontend — minimal changes

- API contract stays the same (backend handles field mapping)
- No frontend changes expected if schemas map correctly

## What is NOT changing

- nhahang_v1 backend code
- nhahang_v1 frontend code
- nhahang_v1 existing database tables
- khobep_v1 frontend code (API responses stay compatible)
- khobep_v1 API endpoint paths
- khobep_v1 upload route (no model dependencies, works unchanged)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Data loss in khobep_v1 DB | khobep_v1's data is seed data only; no production data to migrate |
| Concurrent writes to `so_luong_ton` | Use atomic SQL UPDATE (so_luong_ton += qty) instead of read-update pattern |
| Breaking nhahang_v1 | No nhahang code changes; only adding tables to its DB |
| OCR matching fails post-merge | Expand nguyen_lieu seed data to include all common ingredients |
| Ingredient deletion blocked by FK | Intentional — ON DELETE RESTRICT preserves import audit trail |
