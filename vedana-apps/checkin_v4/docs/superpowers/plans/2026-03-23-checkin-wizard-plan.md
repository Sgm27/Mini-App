# Check-in Wizard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Scan tab with a 3-step check-in wizard (booking upload → ID upload → review/confirm) with redesigned database.

**Architecture:** Frontend wizard with JS state management drives 3 steps. Backend adds OCR booking extraction, batch ID extraction with merge-by-ID-number logic, and checkins CRUD. Database replaces `documents` table with `checkins` + `guests` tables.

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI GPT vision API, vanilla JS, MySQL

**Spec:** `docs/superpowers/specs/2026-03-23-checkin-wizard-design.md`

---

## File Map

### New Files
- `database/003_checkin_wizard.sql` — SQL migration (drop documents, create checkins + guests)
- `backend/app/models/checkin.py` — Checkin + Guest SQLAlchemy models
- `backend/app/schemas/checkin.py` — Pydantic schemas for all new endpoints
- `backend/app/api/routes/checkins.py` — POST/GET checkins endpoints

### Modified Files
- `backend/app/services/ocr_service.py` — add `extract_booking_info_async()`, `batch_extract_info_async()`
- `backend/app/api/routes/ocr.py` — add `/ocr/booking` and `/ocr/batch-extract` endpoints
- `backend/app/api/routes/__init__.py` — register checkins, remove documents
- `backend/app/db/base.py` — import new models instead of Document
- `frontend/index.html` — rename Scan tab label to "Check-in"
- `frontend/js/app.js` — complete rewrite of scan tab → wizard, update history tab
- `frontend/js/api.js` — add new API helper functions
- `frontend/css/style.css` — add wizard step indicator, guest card, warning banner styles

### Removed Files
- `backend/app/api/routes/documents.py`
- `backend/app/models/document.py`
- `backend/app/schemas/document.py`

---

## Chunk 1: Database & Backend Models

### Task 1: SQL Migration

**Files:**
- Create: `database/003_checkin_wizard.sql`

- [ ] **Step 1: Write migration SQL**

```sql
-- 003_checkin_wizard.sql
-- Drop old documents table and create checkins + guests

DROP TABLE IF EXISTS documents;

CREATE TABLE checkins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_code VARCHAR(100) NOT NULL,
    room_type VARCHAR(100),
    num_guests INT NOT NULL,
    arrival_date VARCHAR(20) NOT NULL,
    departure_date VARCHAR(20) NOT NULL,
    contact_name VARCHAR(255),
    contact_phone VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE guests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checkin_id INT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    gender VARCHAR(20),
    date_of_birth VARCHAR(20),
    identification_number VARCHAR(50) NOT NULL,
    address TEXT,
    document_type VARCHAR(50),
    nationality VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_guests_checkin FOREIGN KEY (checkin_id) REFERENCES checkins(id) ON DELETE CASCADE,
    CONSTRAINT uq_guest_per_checkin UNIQUE (checkin_id, identification_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

- [ ] **Step 2: Run migration against database**

```bash
cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4
mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -P 3306 -u admin -psonktx12345 checkin_v4 < database/003_checkin_wizard.sql
```

Expected: Tables created successfully. If `documents` doesn't exist, the DROP IF EXISTS handles it gracefully.

- [ ] **Step 3: Commit**

```bash
git add database/003_checkin_wizard.sql
git commit -m "feat: add migration for checkins and guests tables"
```

### Task 2: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/checkin.py`
- Modify: `backend/app/db/base.py`
- Remove: `backend/app/models/document.py`

- [ ] **Step 1: Create Checkin and Guest models**

Create `backend/app/models/checkin.py`:

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_code = Column(String(100), nullable=False)
    room_type = Column(String(100), nullable=True)
    num_guests = Column(Integer, nullable=False)
    arrival_date = Column(String(20), nullable=False)
    departure_date = Column(String(20), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    guests = relationship("Guest", back_populates="checkin", cascade="all, delete-orphan")


class Guest(Base):
    __tablename__ = "guests"
    __table_args__ = (
        UniqueConstraint("checkin_id", "identification_number", name="uq_guest_per_checkin"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    identification_number = Column(String(50), nullable=False)
    address = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    checkin = relationship("Checkin", back_populates="guests")
```

- [ ] **Step 2: Update `backend/app/db/base.py`**

Replace the Document import with Checkin imports:

```python
"""Import models here so Alembic can discover them."""

from app.db.base_class import Base  # noqa: F401
from app.models.checkin import Checkin, Guest  # noqa: F401
```

- [ ] **Step 3: Delete `backend/app/models/document.py`**

```bash
rm backend/app/models/document.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/checkin.py backend/app/db/base.py
git rm backend/app/models/document.py
git commit -m "feat: add Checkin and Guest SQLAlchemy models, remove Document"
```

### Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/checkin.py`
- Remove: `backend/app/schemas/document.py`

- [ ] **Step 1: Create checkin schemas**

Create `backend/app/schemas/checkin.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


# --- OCR Booking ---
class BookingOCRResult(BaseModel):
    booking_code: str | None = None
    room_type: str | None = None
    num_guests: int | None = None
    arrival_date: str | None = None
    departure_date: str | None = None


# --- OCR Batch Extract ---
class GuestExtracted(BaseModel):
    full_name: str = ""
    gender: str | None = None
    date_of_birth: str | None = None
    identification_number: str = ""
    address: str | None = None
    document_type: str | None = None
    nationality: str | None = None


class BatchExtractResult(BaseModel):
    guests: list[GuestExtracted] = []
    total_profiles: int = 0


# --- Checkin Create ---
class BookingInfo(BaseModel):
    booking_code: str = Field(..., min_length=1)
    room_type: str | None = None
    num_guests: int = Field(..., ge=1)
    arrival_date: str = Field(..., min_length=1)
    departure_date: str = Field(..., min_length=1)


class ContactInfo(BaseModel):
    name: str | None = None
    phone: str | None = None


class GuestCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    gender: str | None = None
    date_of_birth: str | None = None
    identification_number: str = Field(..., min_length=1)
    address: str | None = None
    document_type: str | None = None
    nationality: str | None = None


class CheckinCreate(BaseModel):
    booking: BookingInfo
    contact: ContactInfo | None = None
    guests: list[GuestCreate] = Field(..., min_length=1)


# --- Checkin Response ---
class GuestResponse(BaseModel):
    id: int
    full_name: str
    gender: str | None
    date_of_birth: str | None
    identification_number: str
    address: str | None
    document_type: str | None
    nationality: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckinResponse(BaseModel):
    id: int
    booking_code: str
    room_type: str | None
    num_guests: int
    arrival_date: str
    departure_date: str
    contact_name: str | None
    contact_phone: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckinDetailResponse(CheckinResponse):
    guests: list[GuestResponse] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Delete `backend/app/schemas/document.py`**

```bash
rm backend/app/schemas/document.py
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/checkin.py
git rm backend/app/schemas/document.py
git commit -m "feat: add Pydantic schemas for checkin API, remove document schemas"
```

---

## Chunk 2: Backend OCR & API

### Task 4: OCR Service — Booking Extraction

**Files:**
- Modify: `backend/app/services/ocr_service.py`

- [ ] **Step 1: Add `extract_booking_info_async()` function**

Add at the end of `ocr_service.py`, before `process_document()`:

```python
async def extract_booking_info_async(image_path: str) -> dict:
    """Extract booking information from a confirmation image."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"error": "encode_failed", "message": "Không thể đọc ảnh"}

    mime_type = get_mime_type(image_path)

    prompt = """Trích xuất thông tin đặt phòng khách sạn từ ảnh. Ảnh có thể là ảnh chụp màn hình từ app đặt phòng, email xác nhận, hoặc giấy xác nhận.

Trích xuất các thông tin sau:
- booking_code: Mã đặt phòng / Mã xác nhận / Confirmation number
- room_type: Loại phòng
- num_guests: Số người ở (số nguyên)
- arrival_date: Ngày nhận phòng (DD/MM/YYYY)
- departure_date: Ngày trả phòng (DD/MM/YYYY)

Trả về JSON (KHÔNG giải thích):
{
  "booking_code": "ABC123",
  "room_type": "Deluxe King",
  "num_guests": 2,
  "arrival_date": "25/03/2026",
  "departure_date": "28/03/2026"
}

Nếu không tìm thấy thông tin nào, ghi null cho trường đó.
Nếu ảnh không phải xác nhận đặt phòng, trả về: {"error": "not_booking"}"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = _parse_json_response(
            response.choices[0].message.content.strip()
        )
        result = json.loads(response_text)

        if result.get("error") == "not_booking":
            return {"error": "not_booking", "message": "Ảnh không phải xác nhận đặt phòng"}

        return {
            "booking_code": result.get("booking_code"),
            "room_type": result.get("room_type"),
            "num_guests": result.get("num_guests"),
            "arrival_date": result.get("arrival_date"),
            "departure_date": result.get("departure_date"),
        }
    except Exception as e:
        logger.error(f"Booking OCR error: {e}")
        return {"error": "ocr_error", "message": "Không thể trích xuất thông tin đặt phòng"}
```

- [ ] **Step 2: Add `batch_extract_info_async()` function**

Add after `extract_booking_info_async()`:

```python
async def batch_extract_info_async(image_paths: list[str]) -> dict:
    """Process multiple ID images and merge profiles by identification_number."""
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    # Process all images concurrently
    tasks = [process_single_image(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    if not all_results:
        return {"guests": [], "total_profiles": 0}

    # Map missing info (front/back matching by CCCD number)
    all_results = map_missing_info(all_results)

    # Convert to frontend format and group by identification_number
    profiles: dict[str, dict] = {}

    for result in all_results:
        id_number = result.get("so_dinh_danh", "")
        if not id_number or id_number == "Không xác định":
            # Assign temporary key for unidentified profiles
            import uuid
            id_number = f"temp_{uuid.uuid4().hex[:8]}"

        if id_number in profiles:
            # Merge: fill null fields only
            existing = profiles[id_number]
            for field, vn_field in [
                ("full_name", "ho_ten"),
                ("gender", "gioi_tinh"),
                ("date_of_birth", "ngay_sinh"),
                ("address", "noi_o"),
            ]:
                if not existing.get(field) or existing[field] == "Không xác định":
                    new_val = result.get(vn_field, "")
                    if new_val and new_val != "Không xác định":
                        existing[field] = new_val
        else:
            profiles[id_number] = {
                "full_name": result.get("ho_ten", ""),
                "gender": result.get("gioi_tinh", ""),
                "date_of_birth": result.get("ngay_sinh", ""),
                "identification_number": id_number if not id_number.startswith("temp_") else "",
                "address": result.get("noi_o", ""),
                "document_type": "cccd",
                "nationality": None,
            }

    # Clean up "Không xác định" values
    guest_list = []
    for profile in profiles.values():
        cleaned = {}
        for k, v in profile.items():
            if v == "Không xác định":
                cleaned[k] = None
            else:
                cleaned[k] = v
        guest_list.append(cleaned)

    return {"guests": guest_list, "total_profiles": len(guest_list)}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ocr_service.py
git commit -m "feat: add booking OCR and batch extraction with merge logic"
```

### Task 5: OCR API Routes

**Files:**
- Modify: `backend/app/api/routes/ocr.py`

- [ ] **Step 1: Add booking and batch-extract endpoints**

Add these two new endpoints to `ocr.py` after the existing `/extract` endpoint:

```python
@router.post("/booking")
async def extract_booking(file: UploadFile = File(...)):
    """Extract booking confirmation info via OCR."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Định dạng file không hợp lệ. Chỉ chấp nhận JPG, PNG, WEBP"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File quá lớn. Kích thước tối đa 10MB")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File rỗng")

    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        result = await extract_booking_info_async(temp_path)

        if result.get("error") == "not_booking":
            raise HTTPException(status_code=422, detail=result["message"])
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/batch-extract")
async def batch_extract_documents(files: list[UploadFile] = File(...)):
    """Extract info from multiple ID document images, merge by identification number."""
    if not files:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_paths = []

    try:
        for file in files:
            if not file.filename:
                continue
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            content = await file.read()
            if len(content) == 0 or len(content) > MAX_FILE_SIZE:
                continue

            temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_paths.append(temp_path)

        if not temp_paths:
            raise HTTPException(status_code=400, detail="Không có file hợp lệ")

        result = await batch_extract_info_async(temp_paths)

        if not result["guests"]:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được thông tin từ các ảnh"
            )

        return result
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
```

- [ ] **Step 2: Add import for new functions**

Update the import at top of `ocr.py`:

```python
from app.services.ocr_service import process_document, extract_booking_info_async, batch_extract_info_async
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/ocr.py
git commit -m "feat: add /ocr/booking and /ocr/batch-extract API endpoints"
```

### Task 6: Checkins CRUD Routes

**Files:**
- Create: `backend/app/api/routes/checkins.py`

- [ ] **Step 1: Create checkins route file**

```python
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import DBSession
from app.models.checkin import Checkin, Guest
from app.schemas.checkin import (
    CheckinCreate,
    CheckinDetailResponse,
    CheckinResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkins")


@router.post("", response_model=CheckinResponse, status_code=201)
def create_checkin(data: CheckinCreate, db: Session = DBSession):
    """Submit a complete check-in record."""
    # Validate dates
    try:
        arrival = datetime.strptime(data.booking.arrival_date, "%d/%m/%Y")
        departure = datetime.strptime(data.booking.departure_date, "%d/%m/%Y")
        if departure < arrival:
            raise HTTPException(
                status_code=400,
                detail="Ngày trả phòng phải sau ngày nhận phòng"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày không hợp lệ. Định dạng: DD/MM/YYYY"
        )

    checkin = Checkin(
        booking_code=data.booking.booking_code.strip(),
        room_type=data.booking.room_type.strip() if data.booking.room_type else None,
        num_guests=data.booking.num_guests,
        arrival_date=data.booking.arrival_date.strip(),
        departure_date=data.booking.departure_date.strip(),
        contact_name=data.contact.name.strip() if data.contact and data.contact.name else None,
        contact_phone=data.contact.phone.strip() if data.contact and data.contact.phone else None,
        status="confirmed",
        created_at=datetime.utcnow(),
    )

    for guest_data in data.guests:
        guest = Guest(
            full_name=guest_data.full_name.strip(),
            gender=guest_data.gender.strip() if guest_data.gender else None,
            date_of_birth=guest_data.date_of_birth.strip() if guest_data.date_of_birth else None,
            identification_number=guest_data.identification_number.strip(),
            address=guest_data.address.strip() if guest_data.address else None,
            document_type=guest_data.document_type.strip() if guest_data.document_type else None,
            nationality=guest_data.nationality.strip() if guest_data.nationality else None,
            created_at=datetime.utcnow(),
        )
        checkin.guests.append(guest)

    try:
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving checkin: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu dữ liệu check-in")

    return checkin


@router.get("", response_model=list[CheckinResponse])
def list_checkins(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = DBSession,
):
    """List all check-ins, newest first."""
    checkins = (
        db.query(Checkin)
        .order_by(Checkin.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return checkins


@router.get("/{checkin_id}", response_model=CheckinDetailResponse)
def get_checkin(checkin_id: int, db: Session = DBSession):
    """Get full check-in detail including guest list."""
    checkin = db.query(Checkin).filter(Checkin.id == checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi check-in")
    return checkin
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/routes/checkins.py
git commit -m "feat: add checkins CRUD API endpoints"
```

### Task 7: Route Registration

**Files:**
- Modify: `backend/app/api/routes/__init__.py`
- Remove: `backend/app/api/routes/documents.py`

- [ ] **Step 1: Update route registration**

Replace contents of `backend/app/api/routes/__init__.py`:

```python
from fastapi import APIRouter, FastAPI

from app.api.routes import checkins, health, ocr, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(ocr.router, tags=["ocr"])
    api_router.include_router(checkins.router, tags=["checkins"])
    app.include_router(api_router)
```

- [ ] **Step 2: Delete documents route**

```bash
rm backend/app/api/routes/documents.py
```

- [ ] **Step 3: Verify backend starts**

```bash
cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend
python -c "from app.main import app; print('OK')"
```

Expected: `OK` — no import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/__init__.py
git rm backend/app/api/routes/documents.py
git commit -m "feat: register checkin routes, remove document routes"
```

---

## Chunk 3: Frontend — CSS & API

### Task 8: CSS — Wizard Styles

**Files:**
- Modify: `frontend/css/style.css`

- [ ] **Step 1: Add wizard step indicator, guest card, and warning banner styles**

Append to end of `frontend/css/style.css`:

```css
/* ============================================
   WIZARD STEP INDICATOR
   ============================================ */
.wizard-steps {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin-bottom: var(--space-xl);
    padding: var(--space-lg) 0;
}

.wizard-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-xs);
    flex: 0 0 auto;
    position: relative;
}

.wizard-step__circle {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-full);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    border: 2px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    transition: all var(--transition-normal);
    position: relative;
    z-index: 1;
}

.wizard-step--active .wizard-step__circle {
    border-color: var(--color-primary);
    background: var(--color-primary);
    color: #fff;
}

.wizard-step--done .wizard-step__circle {
    border-color: var(--color-success);
    background: var(--color-success);
    color: #fff;
}

.wizard-step__label {
    font-size: 11px;
    font-weight: 600;
    color: var(--color-text-muted);
    white-space: nowrap;
}

.wizard-step--active .wizard-step__label {
    color: var(--color-primary);
}

.wizard-step--done .wizard-step__label {
    color: var(--color-success);
}

.wizard-step__line {
    width: 48px;
    height: 2px;
    background: var(--color-border);
    margin: 0 var(--space-sm);
    margin-bottom: 18px;
    transition: background var(--transition-normal);
}

.wizard-step__line--done {
    background: var(--color-success);
}

/* ============================================
   WIZARD NAVIGATION
   ============================================ */
.wizard-nav {
    display: flex;
    gap: var(--space-md);
    margin-top: var(--space-xl);
    padding-top: var(--space-lg);
}

/* ============================================
   GUEST CARD
   ============================================ */
.guest-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-sm);
    position: relative;
    transition: all var(--transition-fast);
}

.guest-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-md);
}

.guest-card__name {
    font-weight: 700;
    font-size: 15px;
    color: var(--color-text);
}

.guest-card__remove {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-full);
    background: var(--color-error-bg);
    color: var(--color-error);
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 14px;
    transition: all var(--transition-fast);
}

.guest-card__remove:active {
    transform: scale(0.9);
    background: var(--color-error);
    color: #fff;
}

.guest-card__meta {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    font-size: 13px;
    color: var(--color-text-muted);
}

.guest-card__warn {
    border-color: var(--color-warning);
    background: var(--color-warning-bg);
}

/* ============================================
   WARNING BANNER
   ============================================ */
.warning-banner {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-md) var(--space-lg);
    border-radius: var(--radius-lg);
    background: var(--color-warning-bg);
    border: 1px solid var(--color-warning);
    color: var(--color-text);
    font-size: 13px;
    font-weight: 500;
    margin-bottom: var(--space-lg);
}

.warning-banner__icon {
    color: var(--color-warning);
    flex-shrink: 0;
}

/* ============================================
   REVIEW SECTION
   ============================================ */
.review-section {
    margin-bottom: var(--space-xl);
}

.review-section__title {
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: var(--space-md);
}

.review-summary {
    background: var(--color-primary-bg);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
}

.review-summary__row {
    display: flex;
    justify-content: space-between;
    padding: var(--space-sm) 0;
    font-size: 14px;
    border-bottom: 1px solid rgba(242,107,33,0.1);
}

.review-summary__row:last-child {
    border-bottom: none;
}

.review-summary__label {
    color: var(--color-text-muted);
    font-weight: 500;
}

.review-summary__value {
    color: var(--color-text);
    font-weight: 600;
    text-align: right;
}

/* ============================================
   ADD MORE BUTTON
   ============================================ */
.add-more-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    width: 100%;
    padding: var(--space-md);
    border: 2px dashed var(--color-border);
    border-radius: var(--radius-lg);
    background: transparent;
    color: var(--color-text-muted);
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
    margin-top: var(--space-sm);
}

.add-more-btn:active {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background: var(--color-primary-bg);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: add wizard, guest card, warning banner CSS styles"
```

### Task 9: API Helpers

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Add checkin-specific API helpers**

Append before `window.api = api;` line in `api.js`:

```javascript
  /**
   * Upload file for booking OCR
   * @param {File} file - Image file
   * @returns {Promise<object>} Booking info
   */
  async ocrBooking(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.uploadForm('/api/ocr/booking', formData);
  },

  /**
   * Upload multiple files for batch ID extraction
   * @param {File[]} files - Array of image files
   * @returns {Promise<object>} Batch extract result with guests array
   */
  async ocrBatchExtract(files) {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    return this.uploadForm('/api/ocr/batch-extract', formData);
  },

  /**
   * Submit checkin
   * @param {object} data - { booking, contact, guests }
   * @returns {Promise<object>} Checkin response
   */
  async createCheckin(data) {
    return this.post('/api/checkins', data);
  },

  /**
   * Get checkin list
   * @param {object} params - { limit, offset }
   * @returns {Promise<object[]>} Checkin list
   */
  async getCheckins(params = {}) {
    return this.get('/api/checkins', params);
  },

  /**
   * Get checkin detail with guests
   * @param {number} id - Checkin ID
   * @returns {Promise<object>} Checkin with guests
   */
  async getCheckinDetail(id) {
    return this.get(`/api/checkins/${id}`);
  },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: add checkin API helper methods"
```

---

## Chunk 4: Frontend — Wizard UI

### Task 10: HTML Tab Label + App.js Wizard

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`

- [ ] **Step 1: Update tab label in index.html**

Change the scan tab button label from "Quét" to "Check-in" and update the icon:

In `frontend/index.html`, replace the scan tab `<button>` (lines 42-50):

```html
            <button class="bottom-nav__item bottom-nav__item--active" data-tab="scan">
                <span class="bottom-nav__icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                </span>
                <span class="bottom-nav__label">Check-in</span>
            </button>
```

- [ ] **Step 2: Rewrite app.js with wizard logic**

Complete rewrite of `frontend/js/app.js`. This is a full replacement:

```javascript
/**
 * Smart OCR — Check-in Wizard Application
 * 3-step wizard: Booking → ID Documents → Review & Confirm
 */

let currentTab = 'scan';

let wizardState = {
    currentStep: 1,
    booking: {
        booking_code: null,
        room_type: null,
        num_guests: null,
        arrival_date: null,
        departure_date: null,
    },
    contact: {
        name: null,
        phone: null,
    },
    guests: [],
};

document.addEventListener('DOMContentLoaded', () => {
    initBottomNav();
    loadCheckinTab();
    checkBackend();
});

async function checkBackend() {
    try {
        await api.get('/api/health');
        console.log('Backend connected');
    } catch (e) {
        console.warn('Backend not available:', e.message);
    }
}

/* ============================================
   BOTTOM NAV
   ============================================ */
function initBottomNav() {
    const navItems = document.querySelectorAll('.bottom-nav__item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('bottom-nav__item--active'));
            item.classList.add('bottom-nav__item--active');
            onTabChange(item.dataset.tab);
        });
    });
}

function onTabChange(tab) {
    currentTab = tab;
    switch (tab) {
        case 'scan': loadCheckinTab(); break;
        case 'history': loadHistoryTab(); break;
        case 'info': loadInfoTab(); break;
    }
}

/* ============================================
   WIZARD — Core
   ============================================ */
function resetWizard() {
    wizardState = {
        currentStep: 1,
        booking: { booking_code: null, room_type: null, num_guests: null, arrival_date: null, departure_date: null },
        contact: { name: null, phone: null },
        guests: [],
    };
}

function loadCheckinTab() {
    renderWizardStep();
}

function renderWizardStep() {
    const content = document.getElementById('content');
    const step = wizardState.currentStep;

    const stepsHtml = renderStepIndicator(step);

    let bodyHtml = '';
    switch (step) {
        case 1: bodyHtml = renderStep1(); break;
        case 2: bodyHtml = renderStep2(); break;
        case 3: bodyHtml = renderStep3(); break;
    }

    content.innerHTML = `<div class="fade-in">${stepsHtml}${bodyHtml}</div>`;

    switch (step) {
        case 1: bindStep1Events(); break;
        case 2: bindStep2Events(); break;
        case 3: bindStep3Events(); break;
    }
}

function renderStepIndicator(current) {
    const steps = [
        { num: 1, label: 'Đặt phòng' },
        { num: 2, label: 'Giấy tờ' },
        { num: 3, label: 'Xác nhận' },
    ];

    let html = '<div class="wizard-steps">';
    steps.forEach((s, i) => {
        const cls = s.num < current ? 'wizard-step--done' : s.num === current ? 'wizard-step--active' : '';
        const icon = s.num < current ? '&#10003;' : s.num;
        html += `<div class="wizard-step ${cls}">
            <div class="wizard-step__circle">${icon}</div>
            <span class="wizard-step__label">${s.label}</span>
        </div>`;
        if (i < steps.length - 1) {
            const lineCls = s.num < current ? 'wizard-step__line--done' : '';
            html += `<div class="wizard-step__line ${lineCls}"></div>`;
        }
    });
    html += '</div>';
    return html;
}

/* ============================================
   STEP 1 — Booking Upload
   ============================================ */
function renderStep1() {
    const b = wizardState.booking;
    const hasData = b.booking_code || b.room_type || b.num_guests || b.arrival_date || b.departure_date;

    let formHtml = '';
    if (hasData) {
        formHtml = `
            <div style="margin-top: var(--space-lg);">
                <div style="font-size:12px;font-weight:600;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:var(--space-md);">Thông tin đặt phòng</div>
                <div class="result-form">
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Mã đặt phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_booking_code" value="${escapeHtml(b.booking_code || '')}" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Loại phòng</span></div>
                        <input class="result-field__input" type="text" id="f_room_type" value="${escapeHtml(b.room_type || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Số người *</span></div>
                        <input class="result-field__input" type="number" id="f_num_guests" value="${b.num_guests || ''}" min="1" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày nhận phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_arrival_date" value="${escapeHtml(b.arrival_date || '')}" placeholder="DD/MM/YYYY" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày trả phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_departure_date" value="${escapeHtml(b.departure_date || '')}" placeholder="DD/MM/YYYY" required>
                    </div>
                </div>
            </div>
            <div class="wizard-nav">
                <button class="btn btn--secondary flex-1" id="btnReuploadBooking">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
                    Upload lại
                </button>
                <button class="btn btn--primary flex-1 btn--lg" id="btnStep1Next">
                    Tiếp tục
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                </button>
            </div>
        `;
    }

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Check-in</div>
                <div class="section-header__subtitle">Tải ảnh xác nhận đặt phòng</div>
            </div>
        </div>
        <div class="upload-zone" id="uploadZoneBooking" ${hasData ? 'style="display:none"' : ''}>
            <div class="upload-zone__icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2"/>
                    <path d="M8 21h8"/><path d="M12 17v4"/>
                    <path d="M7 8h.01"/><path d="M12 8l-3 3h6l-3-3z"/>
                </svg>
            </div>
            <div class="upload-zone__title">Tải ảnh xác nhận đặt phòng</div>
            <div class="upload-zone__subtitle">Ảnh chụp màn hình, email hoặc giấy xác nhận</div>
            <div class="upload-zone__actions">
                <button class="upload-zone__btn upload-zone__btn--primary" id="btnBookingCamera">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
                    Chụp ảnh
                </button>
                <button class="upload-zone__btn upload-zone__btn--secondary" id="btnBookingGallery">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                    Thư viện
                </button>
            </div>
            <div class="upload-zone__hint">Hỗ trợ JPG, PNG, WEBP — Tối đa 10MB</div>
        </div>
        <input type="file" id="bookingFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="bookingFileGallery" accept="image/jpeg,image/png,image/webp" style="display:none">
        ${formHtml}
    `;
}

function bindStep1Events() {
    const hasData = wizardState.booking.booking_code || wizardState.booking.num_guests;

    const btnCamera = document.getElementById('btnBookingCamera');
    const btnGallery = document.getElementById('btnBookingGallery');
    const uploadZone = document.getElementById('uploadZoneBooking');

    if (btnCamera) btnCamera.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('bookingFileCamera').click(); });
    if (btnGallery) btnGallery.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('bookingFileGallery').click(); });
    if (uploadZone) uploadZone.addEventListener('click', () => document.getElementById('bookingFileGallery').click());

    document.getElementById('bookingFileCamera').addEventListener('change', handleBookingFile);
    document.getElementById('bookingFileGallery').addEventListener('change', handleBookingFile);

    if (hasData) {
        document.getElementById('btnReuploadBooking').addEventListener('click', () => {
            wizardState.booking = { booking_code: null, room_type: null, num_guests: null, arrival_date: null, departure_date: null };
            renderWizardStep();
        });
        document.getElementById('btnStep1Next').addEventListener('click', handleStep1Next);
    }
}

async function handleBookingFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        showToast('Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP', 'error');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showToast('File quá lớn. Tối đa 10MB', 'error');
        return;
    }

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">${renderStepIndicator(1)}
        <div class="ocr-processing">
            <div class="ocr-processing__scanner"><div class="ocr-processing__scanner-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/></svg>
            </div></div>
            <div class="ocr-processing__title">Đang phân tích ảnh đặt phòng</div>
            <div class="ocr-processing__subtitle">Vui lòng đợi trong giây lát...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBooking(file);
        wizardState.booking = {
            booking_code: result.booking_code || '',
            room_type: result.room_type || '',
            num_guests: result.num_guests || 1,
            arrival_date: result.arrival_date || '',
            departure_date: result.departure_date || '',
        };
        renderWizardStep();
        showToast('Trích xuất thành công', 'success');
    } catch (error) {
        showToast(error.message || 'Không thể trích xuất thông tin đặt phòng', 'error');
        renderWizardStep();
    }
}

function handleStep1Next() {
    // Read form values
    const code = document.getElementById('f_booking_code').value.trim();
    const roomType = document.getElementById('f_room_type').value.trim();
    const numGuests = parseInt(document.getElementById('f_num_guests').value) || 0;
    const arrival = document.getElementById('f_arrival_date').value.trim();
    const departure = document.getElementById('f_departure_date').value.trim();

    if (!code) { showToast('Mã đặt phòng không được để trống', 'error'); return; }
    if (numGuests < 1) { showToast('Số người phải lớn hơn 0', 'error'); return; }
    if (!arrival) { showToast('Ngày nhận phòng không được để trống', 'error'); return; }
    if (!departure) { showToast('Ngày trả phòng không được để trống', 'error'); return; }

    wizardState.booking = { booking_code: code, room_type: roomType || null, num_guests: numGuests, arrival_date: arrival, departure_date: departure };
    wizardState.currentStep = 2;
    renderWizardStep();
}

/* ============================================
   STEP 2 — ID Document Upload
   ============================================ */
function renderStep2() {
    const guests = wizardState.guests;
    const numExpected = wizardState.booking.num_guests;

    let warningHtml = '';
    if (guests.length > 0 && guests.length !== numExpected) {
        warningHtml = `
            <div class="warning-banner">
                <div class="warning-banner__icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
                <span>Số lượng không khớp: Booking ghi ${numExpected} người, hiện có ${guests.length} hồ sơ.</span>
            </div>
        `;
    }

    let guestsHtml = '';
    if (guests.length > 0) {
        guestsHtml = `<div style="font-size:12px;font-weight:600;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:var(--space-md);">Hồ sơ đã quét (${guests.length})</div>`;
        guests.forEach((g, i) => {
            const name = g.full_name || 'Không xác định';
            const idNum = g.identification_number || 'Chưa có số giấy tờ';
            const docType = getDocTypeLabel(g.document_type);
            guestsHtml += `
                <div class="guest-card ${!g.identification_number ? 'guest-card__warn' : ''}">
                    <div class="guest-card__header">
                        <div class="guest-card__name">${escapeHtml(name)}</div>
                        <button class="guest-card__remove" onclick="removeGuest(${i})">&#10005;</button>
                    </div>
                    <div class="guest-card__meta">
                        <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${docType}</span>
                        <span>${escapeHtml(idNum)}</span>
                    </div>
                </div>
            `;
        });
    }

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Giấy tờ tùy thân</div>
                <div class="section-header__subtitle">Tải ảnh CCCD, Hộ chiếu, VNeID, Khai sinh</div>
            </div>
        </div>
        ${warningHtml}
        <div class="upload-zone" id="uploadZoneID">
            <div class="upload-zone__icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="4" width="20" height="16" rx="2"/>
                    <path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/>
                </svg>
            </div>
            <div class="upload-zone__title">Tải ảnh giấy tờ</div>
            <div class="upload-zone__subtitle">Có thể chọn nhiều ảnh cùng lúc</div>
            <div class="upload-zone__actions">
                <button class="upload-zone__btn upload-zone__btn--primary" id="btnIDCamera">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
                    Chụp ảnh
                </button>
                <button class="upload-zone__btn upload-zone__btn--secondary" id="btnIDGallery">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                    Thư viện
                </button>
            </div>
            <div class="upload-zone__hint">Hỗ trợ JPG, PNG, WEBP — Tối đa 10MB mỗi ảnh</div>
        </div>
        <input type="file" id="idFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="idFileGallery" accept="image/jpeg,image/png,image/webp" multiple style="display:none">
        ${guestsHtml}
        ${guests.length > 0 ? `
            <button class="add-more-btn" id="btnAddMore">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Thêm ảnh
            </button>
        ` : ''}
        <div class="wizard-nav">
            <button class="btn btn--secondary flex-1" id="btnStep2Back">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Quay lại
            </button>
            <button class="btn btn--primary flex-1 btn--lg" id="btnStep2Next" ${guests.length === 0 ? 'disabled' : ''}>
                Tiếp tục
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
        </div>
    `;
}

function bindStep2Events() {
    const btnCamera = document.getElementById('btnIDCamera');
    const btnGallery = document.getElementById('btnIDGallery');
    const uploadZone = document.getElementById('uploadZoneID');
    const btnAddMore = document.getElementById('btnAddMore');

    if (btnCamera) btnCamera.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('idFileCamera').click(); });
    if (btnGallery) btnGallery.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('idFileGallery').click(); });
    if (uploadZone) uploadZone.addEventListener('click', () => document.getElementById('idFileGallery').click());
    if (btnAddMore) btnAddMore.addEventListener('click', () => document.getElementById('idFileGallery').click());

    document.getElementById('idFileCamera').addEventListener('change', handleIDFiles);
    document.getElementById('idFileGallery').addEventListener('change', handleIDFiles);

    document.getElementById('btnStep2Back').addEventListener('click', () => { wizardState.currentStep = 1; renderWizardStep(); });
    document.getElementById('btnStep2Next').addEventListener('click', () => { wizardState.currentStep = 3; renderWizardStep(); });
}

function removeGuest(index) {
    wizardState.guests.splice(index, 1);
    renderWizardStep();
}

async function handleIDFiles(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    const validFiles = files.filter(f => {
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) return false;
        if (f.size > 10 * 1024 * 1024) return false;
        return true;
    });

    if (!validFiles.length) {
        showToast('Không có file hợp lệ', 'error');
        return;
    }

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">${renderStepIndicator(2)}
        <div class="ocr-processing">
            <div class="ocr-processing__scanner"><div class="ocr-processing__scanner-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/></svg>
            </div></div>
            <div class="ocr-processing__title">Đang quét ${validFiles.length} ảnh giấy tờ</div>
            <div class="ocr-processing__subtitle">Vui lòng đợi trong giây lát...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBatchExtract(validFiles);

        // Merge new guests with existing ones by identification_number
        const newGuests = result.guests || [];
        newGuests.forEach(newG => {
            if (!newG.identification_number) {
                // No ID — add as separate profile
                wizardState.guests.push(newG);
                return;
            }
            const existing = wizardState.guests.find(g => g.identification_number === newG.identification_number);
            if (existing) {
                // Merge: fill null fields
                for (const key of Object.keys(newG)) {
                    if ((!existing[key] || existing[key] === 'Không xác định') && newG[key] && newG[key] !== 'Không xác định') {
                        existing[key] = newG[key];
                    }
                }
            } else {
                wizardState.guests.push(newG);
            }
        });

        renderWizardStep();
        showToast(`Đã quét ${result.total_profiles} hồ sơ`, 'success');
    } catch (error) {
        showToast(error.message || 'Lỗi khi quét giấy tờ', 'error');
        renderWizardStep();
    }

    // Reset file inputs
    e.target.value = '';
}

/* ============================================
   STEP 3 — Review & Confirm
   ============================================ */
function renderStep3() {
    const b = wizardState.booking;
    const c = wizardState.contact;

    // Booking summary
    let bookingHtml = `
        <div class="review-section">
            <div class="review-section__title">Thông tin đặt phòng</div>
            <div class="review-summary">
                <div class="review-summary__row"><span class="review-summary__label">Mã đặt phòng</span><span class="review-summary__value">${escapeHtml(b.booking_code)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Loại phòng</span><span class="review-summary__value">${escapeHtml(b.room_type || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Số người</span><span class="review-summary__value">${b.num_guests}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Nhận phòng</span><span class="review-summary__value">${escapeHtml(b.arrival_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Trả phòng</span><span class="review-summary__value">${escapeHtml(b.departure_date)}</span></div>
            </div>
        </div>
    `;

    // Contact section
    let contactHtml = `
        <div class="review-section">
            <div class="review-section__title">Thông tin liên hệ</div>
            <div class="result-form">
                <div class="result-field">
                    <div class="result-field__header"><span class="result-field__label">Họ tên liên hệ *</span></div>
                    <input class="result-field__input" type="text" id="f_contact_name" value="${escapeHtml(c.name || '')}" placeholder="Nhập họ tên">
                </div>
                <div class="result-field">
                    <div class="result-field__header"><span class="result-field__label">Số điện thoại *</span></div>
                    <input class="result-field__input" type="tel" id="f_contact_phone" value="${escapeHtml(c.phone || '')}" placeholder="Nhập SĐT">
                </div>
            </div>
        </div>
    `;

    // Guest list — editable
    let guestsHtml = `<div class="review-section"><div class="review-section__title">Danh sách khách (${wizardState.guests.length})</div>`;
    wizardState.guests.forEach((g, i) => {
        guestsHtml += `
            <div class="guest-card" style="margin-bottom:var(--space-md);">
                <div style="font-weight:700;font-size:14px;color:var(--color-primary);margin-bottom:var(--space-md);">Khách ${i + 1}</div>
                <div class="result-form">
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Họ và tên *</span></div>
                        <input class="result-field__input" type="text" id="g_name_${i}" value="${escapeHtml(g.full_name || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Giới tính</span></div>
                        <select class="result-field__select" id="g_gender_${i}">
                            <option value="">-- Chọn --</option>
                            <option value="Nam" ${g.gender === 'Nam' ? 'selected' : ''}>Nam</option>
                            <option value="Nữ" ${g.gender === 'Nữ' ? 'selected' : ''}>Nữ</option>
                        </select>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày sinh</span></div>
                        <input class="result-field__input" type="text" id="g_dob_${i}" value="${escapeHtml(g.date_of_birth || '')}" placeholder="DD/MM/YYYY">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Số giấy tờ *</span></div>
                        <input class="result-field__input" type="text" id="g_id_${i}" value="${escapeHtml(g.identification_number || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Địa chỉ</span></div>
                        <textarea class="result-field__input" id="g_addr_${i}" rows="2" style="resize:none;min-height:auto;">${escapeHtml(g.address || '')}</textarea>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Loại giấy tờ</span></div>
                        <select class="result-field__select" id="g_doctype_${i}">
                            <option value="cccd" ${(g.document_type || 'cccd') === 'cccd' ? 'selected' : ''}>CCCD</option>
                            <option value="cmnd" ${g.document_type === 'cmnd' ? 'selected' : ''}>CMND</option>
                            <option value="passport" ${g.document_type === 'passport' ? 'selected' : ''}>Hộ chiếu</option>
                            <option value="birth_certificate" ${g.document_type === 'birth_certificate' ? 'selected' : ''}>Giấy khai sinh</option>
                        </select>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Quốc tịch</span></div>
                        <input class="result-field__input" type="text" id="g_nationality_${i}" value="${escapeHtml(g.nationality || '')}" placeholder="VD: Việt Nam">
                    </div>
                </div>
            </div>
        `;
    });
    guestsHtml += '</div>';

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Xác nhận check-in</div>
                <div class="section-header__subtitle">Kiểm tra và xác nhận thông tin</div>
            </div>
        </div>
        ${bookingHtml}
        ${contactHtml}
        ${guestsHtml}
        <div class="wizard-nav">
            <button class="btn btn--secondary flex-1" id="btnStep3Back">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Quay lại
            </button>
            <button class="btn btn--primary flex-1 btn--lg" id="btnConfirmCheckin">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Xác nhận
            </button>
        </div>
    `;
}

function bindStep3Events() {
    document.getElementById('btnStep3Back').addEventListener('click', () => {
        saveStep3ToState();
        wizardState.currentStep = 2;
        renderWizardStep();
    });
    document.getElementById('btnConfirmCheckin').addEventListener('click', handleConfirmCheckin);
}

function saveStep3ToState() {
    const contactName = document.getElementById('f_contact_name');
    const contactPhone = document.getElementById('f_contact_phone');
    if (contactName) wizardState.contact.name = contactName.value.trim() || null;
    if (contactPhone) wizardState.contact.phone = contactPhone.value.trim() || null;

    wizardState.guests.forEach((g, i) => {
        const name = document.getElementById(`g_name_${i}`);
        const gender = document.getElementById(`g_gender_${i}`);
        const dob = document.getElementById(`g_dob_${i}`);
        const id = document.getElementById(`g_id_${i}`);
        const addr = document.getElementById(`g_addr_${i}`);
        const docType = document.getElementById(`g_doctype_${i}`);
        const nationality = document.getElementById(`g_nationality_${i}`);

        if (name) g.full_name = name.value.trim();
        if (gender) g.gender = gender.value || null;
        if (dob) g.date_of_birth = dob.value.trim() || null;
        if (id) g.identification_number = id.value.trim();
        if (addr) g.address = addr.value.trim() || null;
        if (docType) g.document_type = docType.value || null;
        if (nationality) g.nationality = nationality.value.trim() || null;
    });
}

async function handleConfirmCheckin() {
    saveStep3ToState();

    // Validate
    if (!wizardState.contact.name) { showToast('Vui lòng nhập họ tên liên hệ', 'error'); return; }
    if (!wizardState.contact.phone) { showToast('Vui lòng nhập số điện thoại', 'error'); return; }

    for (let i = 0; i < wizardState.guests.length; i++) {
        const g = wizardState.guests[i];
        if (!g.full_name) { showToast(`Khách ${i + 1}: Họ tên không được để trống`, 'error'); return; }
        if (!g.identification_number) { showToast(`Khách ${i + 1}: Số giấy tờ không được để trống`, 'error'); return; }
    }

    const btn = document.getElementById('btnConfirmCheckin');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Đang xử lý...';

    try {
        const payload = {
            booking: wizardState.booking,
            contact: wizardState.contact,
            guests: wizardState.guests.map(g => ({
                full_name: g.full_name,
                gender: g.gender || null,
                date_of_birth: g.date_of_birth || null,
                identification_number: g.identification_number,
                address: g.address || null,
                document_type: g.document_type || null,
                nationality: g.nationality || null,
            })),
        };

        await api.createCheckin(payload);
        showCheckinSuccess();
    } catch (error) {
        btn.disabled = false;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Xác nhận';
        showToast(error.message || 'Lỗi khi lưu check-in', 'error');
    }
}

function showCheckinSuccess() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="success-state fade-in">
            <div class="success-state__icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <div class="success-state__title">Check-in thành công!</div>
            <div class="success-state__text">Thông tin đặt phòng và hồ sơ khách đã được lưu vào hệ thống.</div>
            <div class="flex flex-col gap-3" style="margin-top:var(--space-xl);">
                <button class="btn btn--primary btn--full btn--lg" id="btnNewCheckin">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    Check-in mới
                </button>
                <button class="btn btn--secondary btn--full" id="btnGoHistory">
                    Xem lịch sử
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnNewCheckin').addEventListener('click', () => {
        resetWizard();
        renderWizardStep();
    });
    document.getElementById('btnGoHistory').addEventListener('click', () => {
        onTabChange('history');
        document.querySelectorAll('.bottom-nav__item').forEach(i => i.classList.remove('bottom-nav__item--active'));
        document.querySelector('[data-tab=history]').classList.add('bottom-nav__item--active');
    });
}

/* ============================================
   HISTORY TAB
   ============================================ */
async function loadHistoryTab() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header">
            <div>
                <div class="section-header__title">Lịch sử</div>
                <div class="section-header__subtitle">Các lần check-in</div>
            </div>
        </div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const checkins = await api.getCheckins();
        if (!checkins || checkins.length === 0) {
            content.innerHTML = `
                <div class="section-header">
                    <div>
                        <div class="section-header__title">Lịch sử</div>
                        <div class="section-header__subtitle">Các lần check-in</div>
                    </div>
                </div>
                <div class="empty-state">
                    <div class="empty-state__icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    </div>
                    <div class="empty-state__title">Chưa có check-in</div>
                    <div class="empty-state__text">Hãy thực hiện check-in để thấy dữ liệu ở đây.</div>
                </div>
            `;
            return;
        }

        const listHtml = checkins.map((ci, i) => `
            <div class="history-item fade-in stagger-${Math.min(i + 1, 5)}" onclick="showCheckinDetail(${ci.id})">
                <div class="history-item__avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <div class="history-item__body">
                    <div class="history-item__name">${escapeHtml(ci.booking_code)}</div>
                    <div class="history-item__meta">
                        <span>${escapeHtml(ci.room_type || '—')}</span>
                        <span>•</span>
                        <span>${ci.num_guests} khách</span>
                        <span>•</span>
                        <span>${escapeHtml(ci.arrival_date)} → ${escapeHtml(ci.departure_date)}</span>
                    </div>
                </div>
                <div class="history-item__arrow">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
            </div>
        `).join('');

        content.innerHTML = `
            <div class="section-header">
                <div>
                    <div class="section-header__title">Lịch sử</div>
                    <div class="section-header__subtitle">${checkins.length} lần check-in</div>
                </div>
            </div>
            <div class="flex flex-col gap-1">${listHtml}</div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="section-header"><div><div class="section-header__title">Lịch sử</div></div></div>
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadHistoryTab()">Thử lại</button></div>
            </div>
        `;
    }
}

async function showCheckinDetail(checkinId) {
    try {
        const ci = await api.getCheckinDetail(checkinId);

        const guestsHtml = ci.guests.map(g => `
            <div style="padding:var(--space-md) 0;border-bottom:1px solid var(--color-divider);">
                <div style="font-weight:600;font-size:14px;">${escapeHtml(g.full_name)}</div>
                <div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">
                    <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${getDocTypeLabel(g.document_type)}</span>
                    ${escapeHtml(g.identification_number)} ${g.gender ? '• ' + escapeHtml(g.gender) : ''} ${g.date_of_birth ? '• ' + escapeHtml(g.date_of_birth) : ''}
                </div>
                ${g.address ? `<div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">${escapeHtml(g.address)}</div>` : ''}
            </div>
        `).join('');

        const overlay = openBottomSheet(`
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-xl);">
                <h3 style="font-family:var(--font-display);font-size:17px;font-weight:700;">Chi tiết Check-in</h3>
                <span class="doc-type-badge doc-type-badge--cccd">${escapeHtml(ci.status)}</span>
            </div>
            <div class="review-summary" style="margin-bottom:var(--space-xl);">
                <div class="review-summary__row"><span class="review-summary__label">Mã đặt phòng</span><span class="review-summary__value">${escapeHtml(ci.booking_code)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Loại phòng</span><span class="review-summary__value">${escapeHtml(ci.room_type || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Nhận phòng</span><span class="review-summary__value">${escapeHtml(ci.arrival_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Trả phòng</span><span class="review-summary__value">${escapeHtml(ci.departure_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Liên hệ</span><span class="review-summary__value">${escapeHtml(ci.contact_name || '—')} • ${escapeHtml(ci.contact_phone || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Ngày tạo</span><span class="review-summary__value">${formatDateVN(ci.created_at)}</span></div>
            </div>
            <div style="font-weight:700;font-size:14px;margin-bottom:var(--space-md);">Khách (${ci.guests.length})</div>
            ${guestsHtml}
            <div style="margin-top:var(--space-xl);">
                <button class="btn btn--secondary btn--full" id="btnCloseDetail">Đóng</button>
            </div>
        `);

        overlay.querySelector('#btnCloseDetail').addEventListener('click', () => closeBottomSheet(overlay));
    } catch (error) {
        showToast('Không thể tải chi tiết', 'error');
    }
}

/* ============================================
   INFO TAB (unchanged)
   ============================================ */
function loadInfoTab() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">
            <div class="section-header">
                <div>
                    <div class="section-header__title">Thông tin</div>
                    <div class="section-header__subtitle">Về ứng dụng Smart OCR</div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Tính năng</div>
                <div class="info-card">
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Check-in thông minh</div>
                            <div class="info-card__desc">Luồng 3 bước: Booking → Giấy tờ → Xác nhận</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v4a1 1 0 001 1h4M23 4v4a1 1 0 01-1 1h-4M1 20v-4a1 1 0 011-1h4M23 20v-4a1 1 0 00-1-1h-4"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Nhận diện OCR thông minh</div>
                            <div class="info-card__desc">Tự động trích xuất từ booking và giấy tờ</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Bảo mật dữ liệu</div>
                            <div class="info-card__desc">Ảnh gốc được xóa ngay sau khi xử lý</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--green">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Xác minh & chỉnh sửa</div>
                            <div class="info-card__desc">Cho phép chỉnh sửa trước khi xác nhận</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Giấy tờ hỗ trợ</div>
                <div class="info-card">
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">CCCD / CMND</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">Hộ chiếu</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--green"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">Giấy khai sinh</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">VNeID (ảnh chụp màn hình)</div></div>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Bảo mật</div>
                <div class="info-card" style="padding:var(--space-lg);font-size:13px;color:var(--color-text-secondary);line-height:1.7;">
                    Ảnh giấy tờ gốc <strong>không được lưu trữ</strong> trên hệ thống. Ảnh chỉ được xử lý tạm thời để trích xuất thông tin, sau đó bị xóa ngay lập tức.
                </div>
            </div>
        </div>
    `;
}

/* ============================================
   UTILITIES
   ============================================ */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateVN(dateString) {
    if (!dateString) return '';
    const d = new Date(dateString);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const mins = String(d.getMinutes()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${mins}`;
}

function getDocTypeLabel(type) {
    const map = { 'cccd': 'CCCD', 'cmnd': 'CMND', 'passport': 'Hộ chiếu', 'birth_certificate': 'Khai sinh' };
    return map[type] || 'Giấy tờ';
}

function showToast(message, type = 'error') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    const icon = type === 'success'
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast--visible'));
    setTimeout(() => { toast.classList.remove('toast--visible'); setTimeout(() => toast.remove(), 400); }, 3000);
}

function openBottomSheet(content) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="bottom-sheet"><div class="bottom-sheet__handle"></div>${content}</div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('modal-overlay--active'));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeBottomSheet(overlay); });
    return overlay;
}

function closeBottomSheet(overlay) {
    overlay.classList.remove('modal-overlay--active');
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html frontend/js/app.js
git commit -m "feat: implement 3-step check-in wizard UI with history tab update"
```

---

## Chunk 5: Verification

### Task 11: End-to-End Verification

- [ ] **Step 1: Start backend and verify no import errors**

```bash
cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend
python -c "from app.main import app; print('Backend OK')"
```

- [ ] **Step 2: Check API docs load**

Start backend and visit `http://localhost:2701/docs` — verify new endpoints appear:
- `/api/ocr/booking`
- `/api/ocr/batch-extract`
- `/api/checkins` (POST, GET)
- `/api/checkins/{checkin_id}` (GET)

- [ ] **Step 3: Start frontend and test wizard**

```bash
cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/frontend
python3 -m http.server 8386
```

Open `http://localhost:8386` and verify:
1. Tab shows "Check-in" instead of "Quét"
2. Step indicator shows 3 steps
3. Upload zone for booking image appears
4. After OCR, editable booking fields appear
5. Step 2 allows multiple ID uploads
6. Step 3 shows review form with contact + guest editing
7. Confirm submits and shows success
8. History tab shows checkin records

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete check-in wizard implementation"
```
