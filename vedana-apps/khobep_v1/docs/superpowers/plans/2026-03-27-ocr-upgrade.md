# OCR Upgrade for Vedana Receiving Notes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade khobep_v1 OCR from Claude Haiku + regex to GPT-5.1 + direct JSON, extracting full Vedana receiving note format (header + items + summary).

**Architecture:** In-place upgrade of existing OCR pipeline. Database gets new nullable columns via ALTER TABLE. OCR service rewritten to use OpenAI async client. Frontend enhanced to show header info + detailed item list after OCR.

**Tech Stack:** FastAPI, SQLAlchemy 2, OpenAI GPT-5.1, Pillow, vanilla JS

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `database/003_ocr_upgrade.sql` | Create | Migration: add columns to import_receipts and import_receipt_items |
| `backend/.env` | Modify | Add OPENAI_API_KEY |
| `backend/requirements.txt` | Modify | Add openai, Pillow |
| `backend/app/core/config.py` | Modify | Add openai_api_key field |
| `backend/app/models/kitchen.py` | Modify | Add new columns to ImportReceipt and ImportReceiptItem |
| `backend/app/schemas/kitchen.py` | Modify | Add receipt schemas, update import schemas |
| `backend/app/services/ocr_service.py` | Rewrite | GPT-5.1 OCR with direct JSON parse |
| `backend/app/api/routes/ocr.py` | Modify | Return full receipt response, add auto-create |
| `backend/app/api/routes/imports.py` | Modify | Accept new header/item fields |
| `backend/app/services/inventory_service.py` | Modify | Save new fields in create_import, update build_import_out |
| `frontend/js/app.js` | Modify | Enhanced OCR review page with header + items |
| `frontend/css/style.css` | Modify | Styles for new receipt review layout |

---

### Task 1: Database Migration

**Files:**
- Create: `database/003_ocr_upgrade.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 003_ocr_upgrade.sql
-- Add Vedana receiving note fields to import tables

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

INSERT INTO schema_migrations (version, description) VALUES ('003', 'OCR upgrade: add receiving note fields');
```

- [ ] **Step 2: Run the migration**

```bash
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -P 3306 -u admin -psonktx12345 --skip-ssl nha_hang_v1 < database/003_ocr_upgrade.sql
```

Expected: no errors. Verify with:

```bash
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -P 3306 -u admin -psonktx12345 --skip-ssl nha_hang_v1 -e "DESCRIBE import_receipts; DESCRIBE import_receipt_items;"
```

Expected: both tables show the new columns.

- [ ] **Step 3: Commit**

```bash
git add database/003_ocr_upgrade.sql
git commit -m "db: add receiving note fields to import tables"
```

---

### Task 2: Backend Config & Dependencies

**Files:**
- Modify: `backend/.env`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py:37`

- [ ] **Step 1: Add OpenAI API key to .env**

Add this line to `backend/.env` after the `ANTHROPIC_API_KEY` line:

```
# OpenAI API (for OCR receiving note recognition)
OPENAI_API_KEY=your-openai-api-key-here
```

- [ ] **Step 2: Add openai and Pillow to requirements.txt**

Add after the `anthropic>=0.40.0` line in `backend/requirements.txt`:

```
openai>=1.30.0
Pillow>=10.0.0
```

- [ ] **Step 3: Add openai_api_key to config.py**

In `backend/app/core/config.py`, add after line 37 (`anthropic_api_key`):

```python
    openai_api_key: Annotated[str, Field(default="")]
```

- [ ] **Step 4: Install new dependencies**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
pip install openai Pillow --break-system-packages
```

- [ ] **Step 5: Commit**

```bash
git add backend/.env backend/requirements.txt backend/app/core/config.py
git commit -m "config: add OpenAI API key and dependencies for OCR upgrade"
```

---

### Task 3: SQLAlchemy Models — Add New Columns

**Files:**
- Modify: `backend/app/models/kitchen.py:73-98`

- [ ] **Step 1: Add columns to ImportReceipt model**

In `backend/app/models/kitchen.py`, replace the `ImportReceipt` class (lines 73-84) with:

```python
class ImportReceipt(Base):
    """Import receipt header — khobep-owned table."""
    __tablename__ = "import_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_by: Mapped[str] = mapped_column(String(100), default="Nhan vien kho")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Vedana receiving note header fields
    receipt_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    voucher_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_serial: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_no: Mapped[str | None] = mapped_column(String(50), nullable=True)

    items: Mapped[list["ImportReceiptItem"]] = relationship("ImportReceiptItem", back_populates="import_receipt", cascade="all, delete-orphan")
```

- [ ] **Step 2: Add columns to ImportReceiptItem model**

Replace the `ImportReceiptItem` class (lines 87-98) with:

```python
class ImportReceiptItem(Base):
    """Import receipt line items — khobep-owned table."""
    __tablename__ = "import_receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("import_receipts.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    # Vedana receiving note item fields
    item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    item_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    location: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acc_no: Mapped[str | None] = mapped_column(String(50), nullable=True)

    import_receipt: Mapped["ImportReceipt"] = relationship("ImportReceipt", back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="import_items")
```

- [ ] **Step 3: Verify import works**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.models.kitchen import ImportReceipt, ImportReceiptItem; print('Models OK')"
```

Expected: `Models OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/kitchen.py
git commit -m "models: add receiving note fields to ImportReceipt and ImportReceiptItem"
```

---

### Task 4: Pydantic Schemas — Receipt Types

**Files:**
- Modify: `backend/app/schemas/kitchen.py:55-101` and `135-153`

- [ ] **Step 1: Update Import schemas**

In `backend/app/schemas/kitchen.py`, replace the Import section (lines 55-101) with:

```python
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
```

- [ ] **Step 2: Update OCR schemas**

Replace the OCR / Voice section (lines 135-153) with:

```python
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
```

- [ ] **Step 3: Verify schemas compile**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.schemas.kitchen import OcrReceiptResponse, ImportRecordCreate, ReceiptItem; print('Schemas OK')"
```

Expected: `Schemas OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/kitchen.py
git commit -m "schemas: add receipt header/item/summary types for OCR upgrade"
```

---

### Task 5: OCR Service Rewrite

**Files:**
- Rewrite: `backend/app/services/ocr_service.py`

- [ ] **Step 1: Rewrite ocr_service.py with GPT-5.1**

Replace the entire content of `backend/app/services/ocr_service.py` with:

```python
"""OCR extraction using OpenAI GPT-5.1 and voice transcript parsing."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from PIL import Image, ImageOps

from app.core.config import settings
from app.schemas.kitchen import ExtractedItem

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-5.1"
TEMP_ROTATED_FOLDER = "/tmp/khobep_rotated_images"

UNITS_VI = [
    "kg", "g", "lít", "lit", "l", "ml", "cái", "hộp", "bao", "bó",
    "quả", "trái", "túi", "lon", "chai", "thùng", "gói", "tờ", "miếng",
]

VOICE_EXTRACT_PROMPT = """Bạn là trợ lý nhận diện cho kho bếp nhà hàng.

Nhiệm vụ: Trích xuất danh sách nguyên vật liệu từ nội dung sau.

Trả về JSON array với format chính xác sau (KHÔNG thêm text khác):
[
  {"name": "Tên nguyên vật liệu", "quantity": 5.0, "unit": "kg"},
  ...
]

Quy tắc:
- name: tên nguyên vật liệu bằng tiếng Việt, viết thường, không có số
- quantity: số lượng (float)
- unit: đơn vị (kg, g, lít, ml, cái, hộp, bao, bó, quả, túi, lon, chai, thùng)
- Nếu không đọc được số lượng, dùng 1.0
- Nếu không đọc được đơn vị, đoán dựa trên loại nguyên liệu (thịt/cá→kg, nước→lít)
- Bỏ qua thông tin không phải nguyên vật liệu (tên cửa hàng, ngày tháng, tổng tiền...)
"""

RECEIPT_EXTRACT_PROMPT = """Bạn là chuyên gia nhận diện phiếu nhập kho cho nhà hàng/resort.
Nếu nhận thấy ảnh bị ngược chữ trả về luôn số 0 (chỉ trả ra số 0).

Nhiệm vụ: Trích xuất TOÀN BỘ thông tin từ phiếu nhập kho / receiving note trong ảnh.

Trả về JSON với format chính xác sau (KHÔNG giải thích):
{
  "header": {
    "receipt_date": "DD/MM/YYYY",
    "description": "Nội dung phiếu nhập",
    "vendor_name": "Tên nhà cung cấp",
    "period": "Kỳ KT (ví dụ: 202602)",
    "voucher_no": "Số phiếu (ví dụ: NK0072)",
    "invoice_serial": "Seri HĐ (ví dụ: 1C26TDK)",
    "invoice_no": "Số HĐ (ví dụ: 39)"
  },
  "items": [
    {
      "item_code": "Mã số hàng",
      "name": "Tên nguyên vật liệu",
      "unit": "Đơn vị tính",
      "quantity": 5.60,
      "unit_price": 604914,
      "amount": 3387520,
      "location": "Mã kho",
      "acc_no": "Mã tài khoản"
    }
  ],
  "summary": {
    "sub_amount": 3387520,
    "discount": 0,
    "vat": 0,
    "total_amount": 3387520
  }
}

Quy tắc:
- Trích xuất CHÍNH XÁC số liệu từ phiếu, không làm tròn
- quantity là số lượng (Số lượng/Qty), unit_price là đơn giá (Đơn giá/Price), amount là thành tiền (Thành tiền/Amount)
- Nếu không tìm thấy trường nào, ghi null
- Nếu có nhiều dòng hàng, trích xuất TẤT CẢ
- Tên nguyên vật liệu phải viết có dấu tiếng Việt nếu trong ảnh có dấu
"""


def _parse_json_response(response_text: str) -> str:
    """Strip markdown code fences from LLM response."""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    return response_text


def _get_openai_client() -> AsyncOpenAI:
    """Get async OpenAI client."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY chưa được cấu hình")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _detect_mime_and_strip(image_base64: str) -> tuple[str, str]:
    """Detect MIME type and strip data URI prefix if present."""
    mime_type = "image/jpeg"
    data = image_base64

    if data.startswith("data:"):
        header, data = data.split(",", 1)
        if "png" in header:
            mime_type = "image/png"
        elif "webp" in header:
            mime_type = "image/webp"
        elif "gif" in header:
            mime_type = "image/gif"

    return mime_type, data


def _rotate_image_base64(image_base64: str, mime_type: str, angle: int) -> str:
    """Rotate a base64 image by the given angle and return new base64."""
    if angle == 0:
        return image_base64

    try:
        import io
        image_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        rotated = img.rotate(-angle, expand=True)

        buffer = io.BytesIO()
        fmt = "PNG" if "png" in mime_type else "JPEG"
        rotated.save(buffer, format=fmt)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error rotating image: {e}")
        return image_base64


async def extract_receipt_from_image(image_base64: str) -> dict:
    """Extract full receiving note (header + items + summary) from image using GPT-5.1.

    Returns dict with keys: header, items, summary.
    Uses self-correction: if LLM detects upside-down text, rotates 180° and retries.
    """
    client = _get_openai_client()
    mime_type, b64_data = _detect_mime_and_strip(image_base64)

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": RECEIPT_EXTRACT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_data}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = response.choices[0].message.content.strip()

        # Self-correction: if text is upside down, rotate 180° and retry
        if response_text == "0":
            b64_data = _rotate_image_base64(b64_data, mime_type, 180)

            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": RECEIPT_EXTRACT_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0,
            )
            response_text = response.choices[0].message.content.strip()

        response_text = _parse_json_response(response_text)
        result = json.loads(response_text)

        return {
            "header": result.get("header", {}),
            "items": result.get("items", []),
            "summary": result.get("summary"),
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raise RuntimeError(f"Không thể parse kết quả OCR: {e}")
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise RuntimeError(f"Lỗi nhận diện ảnh: {e}")


async def extract_from_voice(transcript: str) -> list[ExtractedItem]:
    """Parse voice transcript to extract materials. Uses GPT-5.1 if available, else regex fallback."""
    if settings.openai_api_key:
        try:
            client = _get_openai_client()
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": VOICE_EXTRACT_PROMPT + f"\n\nNội dung ghi âm:\n{transcript}",
                    }
                ],
                temperature=0,
            )
            response_text = response.choices[0].message.content.strip()
            response_text = _parse_json_response(response_text)
            raw_items = json.loads(response_text)
            items = _normalize_items(raw_items)
            if items:
                return items
        except Exception:
            pass  # Fall through to regex

    # Regex fallback
    return _regex_extract(transcript)


def _normalize_items(raw: list[dict]) -> list[ExtractedItem]:
    """Convert raw JSON dicts to ExtractedItem list."""
    result = []
    for item in raw:
        try:
            name = str(item.get("name", "")).strip()
            quantity = float(item.get("quantity", 1.0))
            unit = str(item.get("unit", "kg")).strip().lower()
            if not name:
                continue
            result.append(ExtractedItem(name=name, quantity=quantity, unit=unit))
        except (ValueError, TypeError):
            continue
    return result


def _regex_extract(text: str) -> list[ExtractedItem]:
    """Fallback regex parser for voice input."""
    units_pattern = "|".join(re.escape(u) for u in UNITS_VI)
    pattern = rf'(\d+(?:[.,]\d+)?)\s*({units_pattern})\s+([^\d,;.]+?)(?=\d|,|;|\.|$)'
    results = []
    for match in re.finditer(pattern, text.lower(), re.IGNORECASE):
        qty_str, unit, name = match.groups()
        qty = float(qty_str.replace(",", "."))
        name = name.strip().rstrip(",; ")
        if name:
            results.append(ExtractedItem(name=name, quantity=qty, unit=unit))
    return results
```

- [ ] **Step 2: Verify the module imports correctly**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.services.ocr_service import extract_receipt_from_image, extract_from_voice; print('OCR service OK')"
```

Expected: `OCR service OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ocr_service.py
git commit -m "feat: rewrite OCR service to use GPT-5.1 with direct JSON parsing"
```

---

### Task 6: OCR Route — Return Full Receipt + Auto-Create Ingredients

**Files:**
- Modify: `backend/app/api/routes/ocr.py`

- [ ] **Step 1: Rewrite ocr.py**

Replace the entire content of `backend/app/api/routes/ocr.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import Ingredient
from app.schemas.kitchen import (
    ExtractResponse,
    OcrExtractRequest,
    OcrReceiptResponse,
    ReceiptHeader,
    ReceiptItem,
    ReceiptSummary,
    VoiceExtractRequest,
)
from app.services.ocr_service import extract_from_voice, extract_receipt_from_image

router = APIRouter(prefix="/ocr")


def _match_and_create_materials(items: list[dict], db: Session) -> list[ReceiptItem]:
    """Match extracted items to ingredients. Auto-create if not found."""
    all_mats = db.query(Ingredient).all()
    mat_map = {m.name.lower(): m for m in all_mats}

    result = []
    for raw_item in items:
        name = raw_item.get("name", "")
        name_lower = name.lower().strip()
        material_id = None
        is_new = False
        matched_unit = raw_item.get("unit", "kg")

        # Exact match
        if name_lower in mat_map:
            material_id = mat_map[name_lower].id
            matched_unit = mat_map[name_lower].unit
        else:
            # Partial match
            for mat_name, mat in mat_map.items():
                if name_lower in mat_name or mat_name in name_lower:
                    material_id = mat.id
                    matched_unit = mat.unit
                    break

        # Auto-create if not found
        if material_id is None and name.strip():
            unit = raw_item.get("unit", "kg")
            new_mat = Ingredient(name=name.strip(), unit=unit)
            db.add(new_mat)
            db.flush()
            material_id = new_mat.id
            is_new = True
            # Update map for subsequent items
            mat_map[name_lower] = new_mat

        result.append(ReceiptItem(
            item_code=raw_item.get("item_code"),
            name=name,
            unit=matched_unit,
            quantity=float(raw_item.get("quantity", 0)),
            unit_price=raw_item.get("unit_price"),
            amount=raw_item.get("amount"),
            location=raw_item.get("location"),
            acc_no=raw_item.get("acc_no"),
            material_id=material_id,
            is_new=is_new,
        ))

    db.commit()
    return result


@router.post("/image", response_model=OcrReceiptResponse)
async def extract_from_invoice_image(data: OcrExtractRequest, db: Session = Depends(get_db)):
    try:
        raw_result = await extract_receipt_from_image(data.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Match items to ingredients (auto-create if needed)
    matched_items = _match_and_create_materials(raw_result.get("items", []), db)

    header_data = raw_result.get("header", {})
    summary_data = raw_result.get("summary")

    return OcrReceiptResponse(
        header=ReceiptHeader(**header_data) if header_data else ReceiptHeader(),
        items=matched_items,
        summary=ReceiptSummary(**summary_data) if summary_data else None,
    )


def _match_voice_materials(items, db: Session):
    """Match voice-extracted items to known ingredients (no auto-create)."""
    all_mats = db.query(Ingredient).all()
    mat_map = {m.name.lower(): m for m in all_mats}

    for item in items:
        name_lower = item.name.lower()
        if name_lower in mat_map:
            item.material_id = mat_map[name_lower].id
            item.unit = mat_map[name_lower].unit
            continue
        for mat_name, mat in mat_map.items():
            if name_lower in mat_name or mat_name in name_lower:
                item.material_id = mat.id
                item.unit = mat.unit
                break
    return items


@router.post("/voice", response_model=ExtractResponse)
async def extract_from_voice_transcript(data: VoiceExtractRequest, db: Session = Depends(get_db)):
    if not data.transcript.strip():
        raise HTTPException(status_code=400, detail="Nội dung giọng nói trống")

    items = await extract_from_voice(data.transcript)
    items = _match_voice_materials(items, db)
    return ExtractResponse(items=items, raw_text=data.transcript)
```

- [ ] **Step 2: Verify import**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.api.routes.ocr import router; print('OCR routes OK')"
```

Expected: `OCR routes OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/ocr.py
git commit -m "feat: OCR route returns full receipt with auto-create ingredients"
```

---

### Task 7: Inventory Service — Handle New Fields

**Files:**
- Modify: `backend/app/services/inventory_service.py:81-158`

- [ ] **Step 1: Update create_import to save new fields**

In `backend/app/services/inventory_service.py`, replace the `create_import` function (lines 81-127) with:

```python
def create_import(db: Session, data: ImportRecordCreate) -> ImportReceipt:
    # Parse receipt_date if provided (DD/MM/YYYY format)
    parsed_date = None
    if data.receipt_date:
        try:
            from datetime import datetime as dt
            parsed_date = dt.strptime(data.receipt_date, "%d/%m/%Y")
        except ValueError:
            pass

    record = ImportReceipt(
        supplier=data.supplier_name or data.vendor_name,
        notes=data.notes,
        image_url=data.image_url,
        received_by=data.created_by,
        receipt_date=parsed_date,
        description=data.description,
        vendor_name=data.vendor_name,
        period=data.period,
        voucher_no=data.voucher_no,
        invoice_serial=data.invoice_serial,
        invoice_no=data.invoice_no,
    )
    db.add(record)
    db.flush()

    for item_in in data.items:
        # Skip items without material_id
        if not item_in.material_id:
            continue

        mat = db.query(Ingredient).filter(Ingredient.id == item_in.material_id).first()
        if not mat:
            continue

        # Add import line item with new fields
        import_item = ImportReceiptItem(
            import_receipt_id=record.id,
            ingredient_id=item_in.material_id,
            quantity=Decimal(str(item_in.quantity)),
            unit=item_in.unit,
            item_code=item_in.item_code,
            item_name=item_in.item_name,
            unit_price=Decimal(str(item_in.unit_price)) if item_in.unit_price is not None else None,
            amount=Decimal(str(item_in.amount)) if item_in.amount is not None else None,
            location=item_in.location,
            acc_no=item_in.acc_no,
        )
        db.add(import_item)

        # Unit conversion: g→kg, ml→lít
        qty = Decimal(str(item_in.quantity))
        unit_lower = item_in.unit.lower().strip()
        mat_unit_lower = mat.unit.lower().strip()
        if unit_lower == "g" and mat_unit_lower == "kg":
            qty = qty / 1000
        elif unit_lower == "ml" and mat_unit_lower in ("lít", "lit", "l"):
            qty = qty / 1000

        # Atomic stock update
        db.execute(
            update(Ingredient)
            .where(Ingredient.id == item_in.material_id)
            .values(stock_quantity=Ingredient.stock_quantity + qty)
        )

    db.commit()
    db.refresh(record)

    recalculate_all_dishes(db)

    return record
```

- [ ] **Step 2: Update build_import_out to include new fields**

Replace the `build_import_out` function (lines 140-158) with:

```python
def build_import_out(record: ImportReceipt) -> ImportRecordOut:
    items_out = []
    for it in record.items:
        items_out.append(ImportItemOut(
            id=it.id,
            material_id=it.ingredient_id,
            material_name=it.ingredient.name if it.ingredient else "?",
            quantity=float(it.quantity),
            unit=it.unit,
            item_code=it.item_code,
            item_name=it.item_name,
            unit_price=float(it.unit_price) if it.unit_price is not None else None,
            amount=float(it.amount) if it.amount is not None else None,
            location=it.location,
            acc_no=it.acc_no,
        ))

    receipt_date_str = None
    if record.receipt_date:
        receipt_date_str = record.receipt_date.strftime("%d/%m/%Y")

    return ImportRecordOut(
        id=record.id,
        supplier_name=record.supplier,
        notes=record.notes,
        image_url=record.image_url,
        created_by=record.received_by,
        created_at=record.created_at,
        receipt_date=receipt_date_str,
        description=record.description,
        vendor_name=record.vendor_name,
        period=record.period,
        voucher_no=record.voucher_no,
        invoice_serial=record.invoice_serial,
        invoice_no=record.invoice_no,
        items=items_out,
    )
```

- [ ] **Step 3: Verify import**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.services.inventory_service import create_import, build_import_out; print('Inventory service OK')"
```

Expected: `Inventory service OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/inventory_service.py
git commit -m "feat: inventory service handles new receiving note fields"
```

---

### Task 8: Import Route — Accept New Fields

**Files:**
- Modify: `backend/app/api/routes/imports.py`

- [ ] **Step 1: Update import route (no code change needed)**

The `imports.py` route already delegates to `create_import(db, data)` and `build_import_out(record)`. Since we updated `ImportRecordCreate` schema (Task 4) and `create_import`/`build_import_out` (Task 7), the route automatically accepts and returns new fields. No code change needed.

Verify it still works:

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -c "from app.api.routes.imports import router; print('Import routes OK')"
```

Expected: `Import routes OK`

---

### Task 9: Frontend — Enhanced OCR Review with Header + Items

**Files:**
- Modify: `frontend/js/app.js:45-62` (state), `280-309` (processOcrImage), `226-257` (renderImportReviewPage), `538-570` (updateReviewList), `584-622` (confirmImport)

- [ ] **Step 1: Update state to include receipt header and summary**

In `frontend/js/app.js`, replace lines 45-62 (the state object) with:

```javascript
const state = {
  currentTab: 'import',
  // Import screen
  importMethod: null,    // 'camera' | 'voice'
  reviewItems: [],       // [{name, quantity, unit, material_id, item_code, unit_price, amount, location, acc_no, is_new}]
  receiptHeader: null,   // {receipt_date, description, vendor_name, period, voucher_no, invoice_serial, invoice_no}
  receiptSummary: null,  // {sub_amount, discount, vat, total_amount}
  capturedImageB64: null,
  // Inventory screen
  invSubTab: 'materials',
  invSearch: '',
  inventoryData: [],
  dishesData: [],
  dishFilter: 'all',     // 'all'|'available'|'unavailable'
  // Reports
  reportData: null,
  historyData: [],
  lowStockData: [],
};
```

- [ ] **Step 2: Update processOcrImage to handle new response format**

Replace the `processOcrImage` function (lines 280-309) with:

```javascript
async function processOcrImage(dataUrl) {
  const content = document.getElementById('content');

  content.innerHTML = `
    <div style="padding: var(--space-xl) var(--space-lg);">
      <img src="${dataUrl}" class="camera-preview" style="width:100%; margin-bottom:var(--space-lg); border-radius:var(--radius-lg);">
      <div class="ocr-processing">
        <div style="color:var(--orange);">${icon('scan', 44)}</div>
        <div class="spinner" style="margin:0 auto;"></div>
        <p class="text-muted text-sm text-center">Đang phân tích phiếu nhập kho...<br>Vui lòng đợi trong giây lát</p>
      </div>
    </div>
  `;

  try {
    const result = await api.post('/api/ocr/image', { image_base64: dataUrl });

    // New response format: {header, items, summary}
    state.receiptHeader = result.header || null;
    state.receiptSummary = result.summary || null;
    state.reviewItems = (result.items || []).map(item => ({
      name: item.name,
      quantity: item.quantity,
      unit: item.unit,
      material_id: item.material_id,
      item_code: item.item_code || null,
      unit_price: item.unit_price || null,
      amount: item.amount || null,
      location: item.location || null,
      acc_no: item.acc_no || null,
      is_new: item.is_new || false,
    }));

    if (state.currentTab !== 'import') return;
    if (state.reviewItems.length === 0) {
      showToast('Không nhận diện được. Thử nhập thủ công.', 'error');
    } else {
      showToast(`Nhận diện được ${state.reviewItems.length} mặt hàng`, 'success');
    }
    renderImportReviewPage();
  } catch (err) {
    showToast('Lỗi nhận diện ảnh: ' + err.message, 'error');
    if (state.currentTab === 'import') renderImportReviewPage();
  }
}
```

- [ ] **Step 3: Update renderImportReviewPage to show header info**

Replace the `renderImportReviewPage` function (lines 226-257) with:

```javascript
function renderImportReviewPage() {
  document.getElementById('page-title').textContent = 'Xác nhận nhập';
  document.getElementById('page-subtitle').textContent = state.reviewItems.length > 0 ? `${state.reviewItems.length} mặt hàng` : '';
  document.getElementById('top-bar-actions').innerHTML = `
    <button class="top-bar__btn" onclick="openAddItem()" title="Thêm mặt hàng">
      ${icon('plus', 20)}
    </button>
  `;

  const h = state.receiptHeader;
  const s = state.receiptSummary;

  const headerHtml = h ? `
    <div class="receipt-header-card">
      <div class="receipt-header-card__title">${icon('clipboard', 16)} Thông tin phiếu nhập</div>
      <div class="receipt-header-grid">
        ${h.voucher_no ? `<div class="receipt-field"><span class="receipt-field__label">Số phiếu</span><span class="receipt-field__value">${escapeHtml(h.voucher_no)}</span></div>` : ''}
        ${h.receipt_date ? `<div class="receipt-field"><span class="receipt-field__label">Ngày nhập</span><span class="receipt-field__value">${escapeHtml(h.receipt_date)}</span></div>` : ''}
        ${h.vendor_name ? `<div class="receipt-field receipt-field--wide"><span class="receipt-field__label">Nhà cung cấp</span><span class="receipt-field__value">${escapeHtml(h.vendor_name)}</span></div>` : ''}
        ${h.description ? `<div class="receipt-field receipt-field--wide"><span class="receipt-field__label">Nội dung</span><span class="receipt-field__value">${escapeHtml(h.description)}</span></div>` : ''}
        ${h.invoice_no ? `<div class="receipt-field"><span class="receipt-field__label">Số HĐ</span><span class="receipt-field__value">${escapeHtml(h.invoice_no)}</span></div>` : ''}
        ${h.invoice_serial ? `<div class="receipt-field"><span class="receipt-field__label">Seri HĐ</span><span class="receipt-field__value">${escapeHtml(h.invoice_serial)}</span></div>` : ''}
        ${h.period ? `<div class="receipt-field"><span class="receipt-field__label">Kỳ KT</span><span class="receipt-field__value">${escapeHtml(h.period)}</span></div>` : ''}
      </div>
    </div>
  ` : '';

  const summaryHtml = s ? `
    <div class="receipt-summary-card">
      <div class="receipt-summary-row">
        <span>Thành tiền</span>
        <span>${s.sub_amount != null ? Number(s.sub_amount).toLocaleString('vi-VN') + ' đ' : '-'}</span>
      </div>
      ${s.discount ? `<div class="receipt-summary-row"><span>Giảm giá</span><span>${Number(s.discount).toLocaleString('vi-VN')} đ</span></div>` : ''}
      ${s.vat ? `<div class="receipt-summary-row"><span>Thuế GTGT</span><span>${Number(s.vat).toLocaleString('vi-VN')} đ</span></div>` : ''}
      <div class="receipt-summary-row receipt-summary-row--total">
        <span>Tổng cộng</span>
        <span>${s.total_amount != null ? Number(s.total_amount).toLocaleString('vi-VN') + ' đ' : '-'}</span>
      </div>
    </div>
  ` : '';

  const content = document.getElementById('content');
  content.innerHTML = `
    <div style="padding: var(--space-lg);">
      <button class="back-link" onclick="backToImportSelect()">
        ${icon('chevron-left', 16)} Chọn phương thức khác
      </button>

      ${headerHtml}

      <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin-top:var(--space-md);">
        <div id="review-list"></div>
      </div>

      ${summaryHtml}

      <div class="form-group mt-lg">
        <label class="form-label" for="supplier-input">Người bàn giao (tuỳ chọn)</label>
        <input class="form-input" type="text" id="supplier-input" placeholder="Tên bộ phận thu mua / nhà cung cấp" value="${h && h.vendor_name ? escapeHtml(h.vendor_name) : ''}">
      </div>
      <button class="btn btn--primary btn--full btn--lg" id="btn-confirm" onclick="confirmImport()">
        ${icon('check', 18)} Xác Nhận Nhập Kho
      </button>
    </div>
  `;

  updateReviewList();
}
```

- [ ] **Step 4: Update updateReviewList to show item details**

Replace the `updateReviewList` function (lines 538-570) with:

```javascript
function updateReviewList() {
  const listEl = document.getElementById('review-list');
  if (!listEl) return;

  const subtitle = document.getElementById('page-subtitle');
  if (subtitle && state.currentTab === 'import') {
    subtitle.textContent = state.reviewItems.length > 0 ? `${state.reviewItems.length} mặt hàng` : '';
  }

  if (state.reviewItems.length === 0) {
    listEl.innerHTML = `<div class="empty-state" style="padding:24px;"><div class="empty-state__icon">${icon('shopping-cart', 36)}</div><p class="empty-state__text">Chưa có nguyên vật liệu nào.<br>Nhấn nút + ở góc phải để thêm.</p></div>`;
    return;
  }

  listEl.innerHTML = state.reviewItems.map((item, idx) => {
    const badge = item.is_new
      ? `<span class="badge badge--new">Mới</span>`
      : (!item.material_id ? ` ${iconInline('alert-triangle', 13, 'var(--warning)')}` : '');
    const priceInfo = item.unit_price != null
      ? `<span class="text-xs text-muted">${Number(item.unit_price).toLocaleString('vi-VN')} đ/${item.unit}</span>`
      : '';
    const amountInfo = item.amount != null
      ? `<span class="text-xs" style="color:var(--orange);font-weight:600;">${Number(item.amount).toLocaleString('vi-VN')} đ</span>`
      : '';

    return `
      <div class="review-item">
        <div class="review-item__num">${idx + 1}</div>
        <div style="flex:1; min-width:0;">
          <div class="review-item__name">
            ${escapeHtml(item.name)} ${badge}
          </div>
          <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            ${item.item_code ? `<span class="text-xs text-muted">Mã: ${escapeHtml(item.item_code)}</span>` : ''}
            ${priceInfo}
            ${amountInfo}
          </div>
        </div>
        <div class="stepper">
          <button class="stepper__btn" onclick="changeItemQty(${idx}, -0.5)">−</button>
          <span class="stepper__value">${parseFloat(item.quantity).toFixed(item.quantity % 1 === 0 ? 0 : 1)} ${item.unit}</span>
          <button class="stepper__btn" onclick="changeItemQty(${idx}, 0.5)">+</button>
        </div>
        <button class="review-item__delete" onclick="removeReviewItem(${idx})">${icon('x', 14)}</button>
      </div>
    `;
  }).join('');
}
```

- [ ] **Step 5: Update confirmImport to send new fields**

Replace the `confirmImport` function (lines 584-622) with:

```javascript
async function confirmImport() {
  if (state.reviewItems.length === 0) { showToast('Chưa có nguyên vật liệu', 'error'); return; }

  // All items should have material_id now (auto-created by backend)
  const validItems = state.reviewItems.filter(i => i.material_id);
  if (validItems.length === 0) {
    showToast('Không có mặt hàng nào hợp lệ', 'error');
    return;
  }

  const btn = document.getElementById('btn-confirm');
  if (btn) { btn.disabled = true; btn.innerHTML = `<div class="spinner spinner--sm spinner--white"></div> Đang lưu...`; }

  const supplier = document.getElementById('supplier-input')?.value || '';
  const h = state.receiptHeader;

  try {
    await api.post('/api/imports', {
      supplier_name: supplier || null,
      created_by: 'Nhân viên kho',
      // Header fields from OCR
      receipt_date: h?.receipt_date || null,
      description: h?.description || null,
      vendor_name: h?.vendor_name || null,
      period: h?.period || null,
      voucher_no: h?.voucher_no || null,
      invoice_serial: h?.invoice_serial || null,
      invoice_no: h?.invoice_no || null,
      // Items with full details
      items: validItems.map(i => ({
        material_id: i.material_id,
        quantity: i.quantity,
        unit: i.unit,
        item_code: i.item_code || null,
        item_name: i.name || null,
        unit_price: i.unit_price || null,
        amount: i.amount || null,
        location: i.location || null,
        acc_no: i.acc_no || null,
      })),
    });

    showToast(`Nhập kho thành công ${validItems.length} mặt hàng!`, 'success');

    // Reset
    state.reviewItems = [];
    state.receiptHeader = null;
    state.receiptSummary = null;
    renderImportTab();
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = `${icon('check', 18)} Xác Nhận Nhập Kho`; }
  }
}
```

- [ ] **Step 6: Update renderImportTab to reset new state**

Replace the `renderImportTab` function (lines 166-171) with:

```javascript
function renderImportTab() {
  state.reviewItems = [];
  state.capturedImageB64 = null;
  state.importMethod = null;
  state.receiptHeader = null;
  state.receiptSummary = null;
  renderImportSelectPage();
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: frontend shows full receipt header, items, and summary from OCR"
```

---

### Task 10: Frontend CSS — Receipt Card Styles

**Files:**
- Modify: `frontend/css/style.css`

- [ ] **Step 1: Add receipt card styles**

Append the following CSS to the end of `frontend/css/style.css`:

```css
/* ─── Receipt Header Card ──────────────────────── */
.receipt-header-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  margin-top: var(--space-md);
  box-shadow: var(--shadow-sm);
  border-left: 4px solid var(--orange);
}

.receipt-header-card__title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--text);
  margin-bottom: var(--space-md);
  display: flex;
  align-items: center;
  gap: 6px;
}

.receipt-header-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm) var(--space-md);
}

.receipt-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.receipt-field--wide {
  grid-column: 1 / -1;
}

.receipt-field__label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.receipt-field__value {
  font-size: var(--text-sm);
  color: var(--text);
  font-weight: 500;
}

/* ─── Receipt Summary Card ─────────────────────── */
.receipt-summary-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: var(--space-md) var(--space-lg);
  margin-top: var(--space-md);
  box-shadow: var(--shadow-sm);
}

.receipt-summary-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-xs) 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.receipt-summary-row--total {
  border-top: 1px solid var(--border);
  margin-top: var(--space-xs);
  padding-top: var(--space-sm);
  font-weight: 700;
  color: var(--text);
  font-size: var(--text-base);
}

/* ─── New Badge ────────────────────────────────── */
.badge--new {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: #DBEAFE;
  color: #2563EB;
  vertical-align: middle;
  margin-left: 4px;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "style: add receipt header, summary, and new-badge styles"
```

---

### Task 11: End-to-End Verification

- [ ] **Step 1: Start the backend server**

```bash
cd /home/sonktx/Mini-App-Lambda/vedana-apps/khobep_v1/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 2701 --reload
```

Verify it starts without errors.

- [ ] **Step 2: Test OCR endpoint with curl**

Use a test image (the Vedana receiving note). If not available, verify the endpoint responds correctly:

```bash
curl -s http://localhost:2701/api/ocr/image \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "data:image/jpeg;base64,/9j/4AAQ..."}' | python -m json.tool
```

Expected: JSON with `header`, `items`, `summary` keys.

- [ ] **Step 3: Test import endpoint with new fields**

```bash
curl -s -X POST http://localhost:2701/api/imports \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_name": "DK FOOD",
    "vendor_name": "Cong ty tnhh thuong mai va dich vu DK FOOD",
    "voucher_no": "NK0072",
    "receipt_date": "09/02/2026",
    "items": [{"material_id": 12, "quantity": 5.6, "unit": "kg", "item_code": "10210016", "item_name": "Ca hoi fillet", "unit_price": 604914, "amount": 3387520}]
  }' | python -m json.tool
```

Expected: 201 response with all header and item fields populated.

- [ ] **Step 4: Verify database**

```bash
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -P 3306 -u admin -psonktx12345 --skip-ssl nha_hang_v1 -e "SELECT id, vendor_name, voucher_no, receipt_date FROM import_receipts ORDER BY id DESC LIMIT 3; SELECT id, item_name, unit_price, amount FROM import_receipt_items ORDER BY id DESC LIMIT 3;"
```

Expected: new receipt shows vendor_name, voucher_no, receipt_date; items show item_name, unit_price, amount.

- [ ] **Step 5: Open frontend in browser and test camera OCR**

Open `http://localhost:8386` (or the frontend URL), take a photo of a Vedana receiving note, and verify:
1. Header card appears with receipt info
2. Items list shows name, code, price, amount
3. Summary card shows totals
4. Confirm import works and saves to database

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete OCR upgrade for Vedana receiving notes"
```
