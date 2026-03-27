# OCR Upgrade for Vedana Receiving Notes (Phieu Nhap Kho)

**Date:** 2026-03-27
**Status:** Approved

## Overview

Upgrade khobep_v1 OCR system to handle Vedana Resort's standardized receiving notes (Phieu Nhap Kho / Receiving Note). Switch from Claude Haiku + regex parsing to GPT-5.1 + direct JSON output (matching checkin_v4 approach). Extend database, backend, and frontend to capture all fields from the invoice format.

## Current State

- **OCR engine**: Claude Haiku 4.5 via Anthropic API
- **Parse method**: Regex `re.search(r'\[.*\]')` to find JSON array in response
- **Output**: Simple `[{name, quantity, unit}]` array
- **DB schema**: `import_receipts` (supplier, notes, image_url, received_by) + `import_receipt_items` (ingredient_id, quantity, unit)
- **Frontend**: 3 input methods (Camera OCR, Voice, Manual), simple review list

## Target State

- **OCR engine**: OpenAI GPT-5.1
- **Parse method**: Direct JSON output with markdown fence stripping (no regex)
- **Output**: Full structured `{header, items[], summary}` matching Vedana invoice format
- **DB schema**: Extended with all invoice header fields + item-level financial data
- **Frontend**: Enhanced OCR review showing header info + detailed item list; Voice/Manual unchanged

## Database Migration

### Table: `import_receipts` — new columns (all nullable)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `receipt_date` | DATE | Ngay nhap | 2026-02-09 |
| `description` | VARCHAR(500) | Noi dung | "Nhap ca hoi cho Bep theo HD so 39" |
| `vendor_name` | VARCHAR(300) | Nha cung cap | "Cong ty tnhh thuong mai va dich vu DK FOOD" |
| `period` | VARCHAR(20) | Ky KT/Period | "202602" |
| `voucher_no` | VARCHAR(50) | So/Vno | "NK0072" |
| `invoice_serial` | VARCHAR(50) | Seri HD | "1C26TDK" |
| `invoice_no` | VARCHAR(50) | So HD | "39" |

### Table: `import_receipt_items` — new columns (all nullable)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `item_code` | VARCHAR(50) | Ma so/Item Code | "10210016" |
| `item_name` | VARCHAR(200) | Ten goc tu phieu (before matching) | "Ca hoi fillet" |
| `unit_price` | DECIMAL(12,2) | Don gia | 604914.00 |
| `amount` | DECIMAL(15,2) | Thanh tien | 3387520.00 |
| `location` | VARCHAR(50) | Kho/Location code | "320" |
| `acc_no` | VARCHAR(50) | TK/Account number | "152102" |

### Migration SQL

```sql
ALTER TABLE import_receipts
  ADD COLUMN receipt_date DATE NULL,
  ADD COLUMN description VARCHAR(500) NULL,
  ADD COLUMN vendor_name VARCHAR(300) NULL,
  ADD COLUMN period VARCHAR(20) NULL,
  ADD COLUMN voucher_no VARCHAR(50) NULL,
  ADD COLUMN invoice_serial VARCHAR(50) NULL,
  ADD COLUMN invoice_no VARCHAR(50) NULL;

ALTER TABLE import_receipt_items
  ADD COLUMN item_code VARCHAR(50) NULL,
  ADD COLUMN item_name VARCHAR(200) NULL,
  ADD COLUMN unit_price DECIMAL(12,2) NULL,
  ADD COLUMN amount DECIMAL(15,2) NULL,
  ADD COLUMN location VARCHAR(50) NULL,
  ADD COLUMN acc_no VARCHAR(50) NULL;
```

Existing data (4 receipts) is unaffected — all new columns are nullable.

## OCR Service Rewrite

### Engine Change

| Aspect | Before | After |
|--------|--------|-------|
| Provider | Anthropic (Claude Haiku 4.5) | OpenAI (GPT-5.1) |
| Client | `anthropic.Anthropic` | `openai.AsyncOpenAI` |
| Parsing | Regex `re.search(r'\[.*\]')` | `json.loads()` after stripping markdown fences |
| Fallback | Regex `_regex_extract()` for voice | Keep regex fallback for voice only |
| Self-correction | None | If LLM returns "0" (upside-down), rotate 180 and retry |
| Image handling | Base64 from frontend | Base64 from frontend (same) |

### GPT-5.1 Prompt Design

Prompt instructs LLM to extract the full Vedana receiving note format:

```json
{
  "header": {
    "receipt_date": "09/02/2026",
    "description": "Nhap ca hoi cho Bep theo HD so 39",
    "vendor_name": "Cong ty tnhh thuong mai va dich vu DK FOOD",
    "period": "202602",
    "voucher_no": "NK0072",
    "invoice_serial": "1C26TDK",
    "invoice_no": "39"
  },
  "items": [
    {
      "item_code": "10210016",
      "name": "Ca hoi fillet",
      "unit": "Kg",
      "quantity": 5.60,
      "unit_price": 604914,
      "amount": 3387520,
      "location": "320",
      "acc_no": "152102"
    }
  ],
  "summary": {
    "sub_amount": 3387520,
    "discount": 0,
    "vat": 0,
    "total_amount": 3387520
  }
}
```

Self-correction: if response is "0", rotate image 180 degrees and retry (same as checkin_v4).

### Functions

- `extract_from_image(image_path: str) -> dict` — main OCR, returns {header, items, summary}
- `extract_from_voice(transcript: str) -> list[ExtractedItem]` — unchanged, returns simple items
- `_parse_json_response(text: str) -> str` — strip markdown fences (from checkin_v4)
- `encode_image_to_base64(path: str) -> str | None` — helper
- `rotate_image(path: str, angle: int) -> str` — self-correction helper

### Dependencies Change

- Remove: `anthropic` (for OCR only; keep if used elsewhere)
- Add: `openai`, `Pillow` (for image rotation)

## Backend Changes

### Config (`config.py`)

Add `openai_api_key` field reading from `OPENAI_API_KEY` env var.

### Schemas (`kitchen.py`)

New/updated Pydantic models:

```python
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
    material_id: int | None = None  # matched ingredient ID
    is_new: bool = False  # true if auto-created

class ReceiptSummary(BaseModel):
    sub_amount: float | None = None
    discount: float | None = None
    vat: float | None = None
    total_amount: float | None = None

class OcrReceiptResponse(BaseModel):
    header: ReceiptHeader
    items: list[ReceiptItem]
    summary: ReceiptSummary | None = None

# Updated import creation
class ImportRecordCreate(BaseModel):
    # Header fields
    receipt_date: str | None = None
    description: str | None = None
    vendor_name: str | None = None
    period: str | None = None
    voucher_no: str | None = None
    invoice_serial: str | None = None
    invoice_no: str | None = None
    supplier_name: str | None = None
    notes: str | None = None
    image_url: str | None = None
    created_by: str = "Nhan vien kho"
    # Items
    items: list[ImportItemCreate]

class ImportItemCreate(BaseModel):
    material_id: int | None = None
    item_code: str | None = None
    item_name: str | None = None
    quantity: float
    unit: str
    unit_price: float | None = None
    amount: float | None = None
    location: str | None = None
    acc_no: str | None = None
```

### Models (`kitchen.py`)

Add new columns to SQLAlchemy models matching the migration.

### Routes

**`POST /api/ocr/image`** — updated response:
- Returns `OcrReceiptResponse` with header + matched items + summary
- Material matching: exact/partial match against `ingredients` table
- Auto-create: if item not found, create new `Ingredient` record and set `is_new=True`

**`POST /api/imports`** — updated payload:
- Accepts full `ImportRecordCreate` with header fields
- Saves header to `import_receipts` new columns
- Saves item details to `import_receipt_items` new columns
- Stock update logic unchanged

**Voice/Manual paths** — unchanged, header fields simply remain null.

## Frontend Changes

### OCR Review Page (enhanced)

After OCR extraction, show 2 sections:

**Section 1: Header Info (collapsible)**
- Receipt date, vendor, description
- Voucher no, invoice serial/no, period
- All fields editable

**Section 2: Items Table**
- Each item shows: name, qty, unit, unit_price, amount
- Badge "Moi" for auto-created ingredients
- Stepper for quantity edit, delete button
- Add item button (existing manual flow)

**Section 3: Summary (read-only)**
- Sub amount, discount, VAT, total

### Confirm Import

Sends full payload (header + items with all fields) to `POST /api/imports`.

### Voice/Manual

Unchanged — these only produce simple items, header stays empty.

### Import History (reports tab)

Display new header fields (vendor, voucher_no, receipt_date) in history list cards.

## File Change Summary

| File | Change |
|------|--------|
| `backend/.env` | Add OPENAI_API_KEY |
| `backend/app/core/config.py` | Add openai_api_key field |
| `backend/app/models/kitchen.py` | Add new columns to ImportReceipt, ImportReceiptItem |
| `backend/app/schemas/kitchen.py` | Add ReceiptHeader, ReceiptItem, ReceiptSummary, OcrReceiptResponse; update ImportRecordCreate, ImportItemCreate |
| `backend/app/services/ocr_service.py` | Full rewrite: OpenAI GPT-5.1, JSON direct parse, self-correction, rotate |
| `backend/app/api/routes/ocr.py` | Update response format, add auto-create ingredient |
| `backend/app/api/routes/imports.py` | Accept and save new header/item fields |
| `backend/app/services/inventory_service.py` | Update create_import to handle new fields |
| `backend/requirements.txt` | Add openai, Pillow |
| `database/003_ocr_upgrade.sql` | ALTER TABLE migration |
| `frontend/js/app.js` | Enhanced OCR review page with header + items + summary |
| `frontend/css/style.css` | Styles for new review layout |

## Decisions

- **Approach**: Upgrade in place (not separate module) — minimal disruption, reuse existing logic
- **LLM**: GPT-5.1 via OpenAI API (matching checkin_v4)
- **Parsing**: Direct JSON, no regex (except voice fallback)
- **Auto-create ingredients**: Yes, when OCR finds items not in DB
- **Voice/Manual**: Unchanged, header fields null
- **Migration safety**: All new columns nullable, existing 4 receipts unaffected
