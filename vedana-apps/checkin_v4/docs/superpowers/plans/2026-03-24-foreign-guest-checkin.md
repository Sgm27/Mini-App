# Foreign Guest Check-in Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add foreign guest support to the check-in wizard — OCR passport extraction, mixed VN/foreign guest per booking, XML export for foreign guests.

**Architecture:** Extend existing Guest model with `guest_type`, `passport_number`, `nationality_code` fields. Separate OCR pipeline for passports. Frontend Step 2 gets two buttons (VN/Foreign). Export splits into Excel (VN) and XML (foreign).

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI GPT-5.1 Vision, MySQL, vanilla JS

**Spec:** `docs/superpowers/specs/2026-03-24-foreign-guest-checkin-design.md`

---

## Chunk 1: Database + Models + Schemas

### Task 1: Database Migration

**Files:**
- Create: `database/005_foreign_guests.sql`

- [ ] **Step 1: Create migration file**

```sql
-- database/005_foreign_guests.sql
ALTER TABLE guests
  ADD COLUMN guest_type VARCHAR(20) NOT NULL DEFAULT 'vietnamese',
  ADD COLUMN passport_number VARCHAR(50) DEFAULT NULL,
  ADD COLUMN nationality_code VARCHAR(10) DEFAULT NULL;

ALTER TABLE guests MODIFY identification_number VARCHAR(50) NULL;

ALTER TABLE guests DROP INDEX uq_guest_per_checkin;
ALTER TABLE guests
  ADD UNIQUE INDEX uq_vn_guest (checkin_id, identification_number),
  ADD UNIQUE INDEX uq_foreign_guest (checkin_id, passport_number);

INSERT IGNORE INTO schema_migrations (version) VALUES ('005_foreign_guests');
```

- [ ] **Step 2: Run migration**

Run: `mysql -u root -p checkin_db < database/005_foreign_guests.sql`
Expected: Query OK, no errors

- [ ] **Step 3: Commit**

```bash
git add database/005_foreign_guests.sql
git commit -m "feat: add migration for foreign guest fields"
```

---

### Task 2: Update ORM Model

**Files:**
- Modify: `backend/app/models/checkin.py:26-44`

- [ ] **Step 1: Update Guest model — change table_args and add new columns**

In `backend/app/models/checkin.py`, replace the entire `Guest` class (lines 26-44):

```python
class Guest(Base):
    __tablename__ = "guests"
    __table_args__ = (
        UniqueConstraint("checkin_id", "identification_number", name="uq_vn_guest"),
        UniqueConstraint("checkin_id", "passport_number", name="uq_foreign_guest"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    guest_type = Column(String(20), nullable=False, default="vietnamese")
    full_name = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    identification_number = Column(String(50), nullable=True)
    passport_number = Column(String(50), nullable=True)
    nationality_code = Column(String(10), nullable=True)
    address = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    checkin = relationship("Checkin", back_populates="guests")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/checkin.py
git commit -m "feat: add guest_type, passport_number, nationality_code to Guest model"
```

---

### Task 3: Update Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/checkin.py`

- [ ] **Step 1: Add model_validator import and update GuestCreate**

At line 1 of `backend/app/schemas/checkin.py`, add `model_validator` import:

```python
from datetime import datetime

from pydantic import BaseModel, Field, model_validator
```

Replace `GuestCreate` class (lines 45-52) with:

```python
class GuestCreate(BaseModel):
    guest_type: str = "vietnamese"
    full_name: str = Field(..., min_length=1)
    gender: str | None = None
    date_of_birth: str | None = None
    identification_number: str | None = None
    address: str | None = None
    document_type: str | None = None
    nationality: str | None = None
    passport_number: str | None = None
    nationality_code: str | None = None

    @model_validator(mode="after")
    def validate_guest_type_fields(self):
        if self.guest_type == "vietnamese":
            if not self.identification_number or not self.identification_number.strip():
                raise ValueError("identification_number required for Vietnamese guests")
        elif self.guest_type == "foreign":
            if not self.passport_number or not self.passport_number.strip():
                raise ValueError("passport_number required for foreign guests")
        return self
```

- [ ] **Step 2: Update GuestExtracted — add guest_type**

Replace `GuestExtracted` class (lines 16-23) with:

```python
class GuestExtracted(BaseModel):
    guest_type: str = "vietnamese"
    full_name: str = ""
    gender: str | None = None
    date_of_birth: str | None = None
    identification_number: str = ""
    address: str | None = None
    document_type: str | None = None
    nationality: str | None = None
```

- [ ] **Step 3: Add new foreign guest schemas**

After `BatchExtractResult`, add:

```python
class ForeignGuestExtracted(BaseModel):
    guest_type: str = "foreign"
    full_name: str = ""
    gender: str | None = None
    date_of_birth: str | None = None
    passport_number: str = ""
    nationality_code: str | None = None
    document_type: str = "passport"


class BatchExtractForeignResult(BaseModel):
    guests: list[ForeignGuestExtracted] = []
    total_profiles: int = 0
```

- [ ] **Step 4: Update GuestResponse — add new fields, make identification_number optional**

Replace `GuestResponse` class (lines 62-73) with:

```python
class GuestResponse(BaseModel):
    id: int
    guest_type: str
    full_name: str
    gender: str | None
    date_of_birth: str | None
    identification_number: str | None
    address: str | None
    document_type: str | None
    nationality: str | None
    passport_number: str | None
    nationality_code: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/checkin.py
git commit -m "feat: update schemas for foreign guest support"
```

---

## Chunk 2: OCR Service + API Endpoint

### Task 4: Add Passport OCR Functions

**Files:**
- Modify: `backend/app/services/ocr_service.py` (append after line 591)

- [ ] **Step 1: Add extract_passport_info_async function**

Append to `backend/app/services/ocr_service.py`:

```python
async def extract_passport_info_async(image_path: str) -> dict:
    """Extract info from a passport image."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"status": "error", "error_message": "Image encode failed"}

    mime_type = get_mime_type(image_path)

    prompt = """
    Extract information from this PASSPORT image.

Extract the following:
- Full name of the passport holder
- Date of birth (DD/MM/YYYY)
- Gender (M or F)
- Nationality code (ISO 3166-1 alpha-3, e.g., GBR, CHN, DEU, KOR, USA, FRA, JPN, AUS)
- Passport number

Return JSON (NO explanation):
{
  "ho_ten": "GARY LEWIS",
  "ngay_sinh": "25/06/1968",
  "gioi_tinh": "M",
  "ma_quoc_tich": "GBR",
  "so_ho_chieu": "549588610"
}

If any field cannot be found, write "Unknown"."""

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

        response_text = response.choices[0].message.content.strip()
        response_text = _parse_json_response(response_text)
        result = json.loads(response_text)
        result["source_image"] = str(Path(image_path).name)
        result["status"] = "success"
        return result

    except Exception as e:
        return {
            "ho_ten": "Unknown",
            "ngay_sinh": "Unknown",
            "gioi_tinh": "Unknown",
            "ma_quoc_tich": "Unknown",
            "so_ho_chieu": "Unknown",
            "source_image": str(Path(image_path).name),
            "status": "error",
            "error_message": str(e),
        }
```

- [ ] **Step 2: Add process_single_passport function**

Append to `backend/app/services/ocr_service.py`:

```python
async def process_single_passport(image_path: str) -> dict | None:
    """Process a single passport image: orientation check -> rotate -> extract."""
    orientation_info = await check_image_orientation_async(image_path)
    rotation_angle = orientation_info["rotation_angle"]

    rotated_image_path = rotate_image(image_path, rotation_angle, TEMP_ROTATED_FOLDER)
    result = await extract_passport_info_async(rotated_image_path)

    if not result or result.get("status") != "success":
        return None

    result["loai_giay_to"] = "passport"
    return result
```

- [ ] **Step 3: Add batch_extract_foreign_info_async function**

Append to `backend/app/services/ocr_service.py`:

```python
async def batch_extract_foreign_info_async(image_paths: list[str]) -> dict:
    """Process multiple passport images and merge profiles by passport number."""
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    tasks = [process_single_passport(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    if not all_results:
        return {"guests": [], "total_profiles": 0}

    profiles: dict[str, dict] = {}

    for result in all_results:
        passport_num = result.get("so_ho_chieu", "")
        if not passport_num or passport_num == "Unknown":
            import uuid
            passport_num = f"temp_{uuid.uuid4().hex[:8]}"

        if passport_num in profiles:
            existing = profiles[passport_num]
            for field, vn_field in [
                ("full_name", "ho_ten"),
                ("gender", "gioi_tinh"),
                ("date_of_birth", "ngay_sinh"),
                ("nationality_code", "ma_quoc_tich"),
            ]:
                if not existing.get(field) or existing[field] == "Unknown":
                    new_val = result.get(vn_field, "")
                    if new_val and new_val != "Unknown":
                        existing[field] = new_val
        else:
            profiles[passport_num] = {
                "guest_type": "foreign",
                "full_name": result.get("ho_ten", ""),
                "gender": result.get("gioi_tinh", ""),
                "date_of_birth": result.get("ngay_sinh", ""),
                "passport_number": passport_num if not passport_num.startswith("temp_") else "",
                "nationality_code": result.get("ma_quoc_tich", ""),
                "document_type": "passport",
            }

    guest_list = []
    for profile in profiles.values():
        cleaned = {}
        for k, v in profile.items():
            cleaned[k] = None if v == "Unknown" else v
        guest_list.append(cleaned)

    return {"guests": guest_list, "total_profiles": len(guest_list)}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ocr_service.py
git commit -m "feat: add passport OCR extraction pipeline"
```

---

### Task 5: Add batch-extract-foreign API Endpoint

**Files:**
- Modify: `backend/app/api/routes/ocr.py` (after line 152)

- [ ] **Step 1: Update import in ocr.py**

At line 10 of `backend/app/api/routes/ocr.py`, update the import:

```python
from app.services.ocr_service import process_document, extract_booking_info_async, batch_extract_info_async, batch_extract_foreign_info_async
```

- [ ] **Step 2: Add the endpoint**

Append to `backend/app/api/routes/ocr.py`:

```python
@router.post("/batch-extract-foreign")
async def batch_extract_foreign_documents(files: list[UploadFile] = File(...)):
    """Extract info from multiple passport images for foreign guests."""
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

        result = await batch_extract_foreign_info_async(temp_paths)

        if not result["guests"]:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được thông tin từ các ảnh hộ chiếu"
            )

        return result
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/ocr.py
git commit -m "feat: add /api/ocr/batch-extract-foreign endpoint"
```

---

## Chunk 3: Backend — Checkin Create + Export + Zalo

### Task 6: Update create_checkin for Foreign Guests

**Files:**
- Modify: `backend/app/api/routes/checkins.py:54-64`

- [ ] **Step 1: Fix Guest creation in create_checkin — null-safe fields + new columns**

In `backend/app/api/routes/checkins.py`, replace lines 54-65 (the guest creation loop):

```python
    for guest_data in data.guests:
        guest = Guest(
            guest_type=guest_data.guest_type,
            full_name=guest_data.full_name.strip(),
            gender=guest_data.gender.strip() if guest_data.gender else None,
            date_of_birth=guest_data.date_of_birth.strip() if guest_data.date_of_birth else None,
            identification_number=guest_data.identification_number.strip() if guest_data.identification_number else None,
            passport_number=guest_data.passport_number.strip() if guest_data.passport_number else None,
            nationality_code=guest_data.nationality_code.strip() if guest_data.nationality_code else None,
            address=guest_data.address.strip() if guest_data.address else None,
            document_type=guest_data.document_type.strip() if guest_data.document_type else None,
            nationality=guest_data.nationality.strip() if guest_data.nationality else None,
            created_at=datetime.utcnow(),
        )
        checkin.guests.append(guest)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/routes/checkins.py
git commit -m "feat: update create_checkin for foreign guest fields"
```

---

### Task 7: Update Excel Export + Add XML Export

**Files:**
- Modify: `backend/app/api/routes/checkins.py`

- [ ] **Step 1: Filter VN guests only in Excel export**

In `backend/app/api/routes/checkins.py`, replace lines 133-135 (the Excel row-building loop):

```python
    for checkin in checkins:
        for guest in checkin.guests:
            if getattr(guest, 'guest_type', 'vietnamese') in ('vietnamese', None):
                ws.append(_build_guest_row(guest, checkin))
```

- [ ] **Step 2: Add _ALPHA3_TO_NAME mapping and XML export endpoint**

Add these imports at the top of `backend/app/api/routes/checkins.py` (after existing imports):

```python
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
```

Then add before the `_GENDER_MAP` definition (before line 158):

```python
_ALPHA3_TO_NAME = {
    "GBR": "United Kingdom", "CHN": "China", "DEU": "Germany",
    "KOR": "Korea", "ARG": "Argentina", "FRA": "France",
    "USA": "United States", "JPN": "Japan", "AUS": "Australia",
    "THA": "Thailand", "SGP": "Singapore", "IND": "India",
    "RUS": "Russia", "MYS": "Malaysia", "IDN": "Indonesia",
    "PHL": "Philippines", "MMR": "Myanmar", "TWN": "Taiwan",
    "VNM": "Vietnam", "LAO": "Laos", "KHM": "Cambodia",
    "NZL": "New Zealand", "CAN": "Canada", "ITA": "Italy",
    "ESP": "Spain", "NLD": "Netherlands", "BRA": "Brazil",
}
```

Then add the XML export endpoint — insert it **before** the `/{checkin_id}` route (before line 149, since `/{checkin_id}` is a catch-all pattern):

```python
@router.get("/export-foreign")
def export_foreign_checkins_xml(
    from_date: str = Query(..., description="DD/MM/YYYY"),
    to_date: str = Query(..., description="DD/MM/YYYY"),
    db: Session = DBSession,
):
    """Export foreign guests within a date range as XML."""
    try:
        dt_from = datetime.strptime(from_date, "%d/%m/%Y")
        dt_to = datetime.strptime(to_date, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày không hợp lệ. Định dạng: DD/MM/YYYY")

    if dt_to < dt_from:
        raise HTTPException(status_code=400, detail="Ngày kết thúc phải sau ngày bắt đầu")

    checkins = (
        db.query(Checkin)
        .filter(Checkin.created_at >= dt_from, Checkin.created_at <= dt_to)
        .order_by(Checkin.created_at.asc())
        .all()
    )

    # Collect foreign guests with room info
    from app.models.room import Room, RoomAssignment
    root = Element("KHAI_BAO_TAM_TRU")
    counter = 0

    for checkin in checkins:
        # Get room number for this checkin
        room_assignment = (
            db.query(RoomAssignment)
            .filter(RoomAssignment.checkin_id == checkin.id, RoomAssignment.released_at.is_(None))
            .order_by(RoomAssignment.assigned_at.asc())
            .first()
        )
        room_number = ""
        if room_assignment:
            room = db.query(Room).filter(Room.id == room_assignment.room_id).first()
            if room:
                room_number = room.room_number or ""

        for guest in checkin.guests:
            if getattr(guest, 'guest_type', 'vietnamese') != 'foreign':
                continue
            counter += 1
            khach = SubElement(root, "THONG_TIN_KHACH")
            SubElement(khach, "so_thu_tu").text = str(counter)
            SubElement(khach, "ho_ten").text = guest.full_name or ""
            SubElement(khach, "ngay_sinh").text = guest.date_of_birth or ""
            SubElement(khach, "ngay_sinh_dung_den").text = "D"
            SubElement(khach, "gioi_tinh").text = guest.gender or ""
            SubElement(khach, "ma_quoc_tich").text = guest.nationality_code or ""
            SubElement(khach, "so_ho_chieu").text = guest.passport_number or ""
            SubElement(khach, "so_phong").text = room_number
            SubElement(khach, "ngay_den").text = checkin.arrival_date or ""
            SubElement(khach, "ngay_di_du_kien").text = checkin.departure_date or ""
            SubElement(khach, "ngay_tra_phong").text = checkin.departure_date or ""

    if counter == 0:
        raise HTTPException(status_code=404, detail="Không có khách nước ngoài trong khoảng thời gian này")

    xml_str = parseString(tostring(root, encoding="unicode")).toprettyxml(indent="  ", encoding=None)
    # Remove extra XML declaration from minidom, add our own
    lines = xml_str.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_output = "\n".join(lines)

    filename = f"foreign_checkin_{from_date.replace('/', '')}_{to_date.replace('/', '')}.xml"
    return StreamingResponse(
        iter([xml_output.encode("utf-8")]),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/checkins.py
git commit -m "feat: filter VN guests in Excel export, add XML export for foreign guests"
```

---

### Task 8: Update Zalo Notification

**Files:**
- Modify: `backend/app/services/zalo_service.py:92-102`

- [ ] **Step 1: Update _build_checkin_message to handle foreign guests**

In `backend/app/services/zalo_service.py`, add the alpha-3 to name mapping at the top (after `DOC_TYPE_LABELS`):

```python
ALPHA3_TO_NAME = {
    "GBR": "United Kingdom", "CHN": "China", "DEU": "Germany",
    "KOR": "Korea", "ARG": "Argentina", "FRA": "France",
    "USA": "United States", "JPN": "Japan", "AUS": "Australia",
    "THA": "Thailand", "SGP": "Singapore", "IND": "India",
    "RUS": "Russia", "MYS": "Malaysia", "IDN": "Indonesia",
}
```

Then replace lines 92-102 (the guest list building section):

```python
    if guests:
        lines.append("")
        lines.append(f"👥 Danh sách khách ({len(guests)}):")
        for i, g in enumerate(guests, 1):
            guest_type = getattr(g, 'guest_type', 'vietnamese') or 'vietnamese'
            if guest_type == 'foreign':
                nat_code = getattr(g, 'nationality_code', '') or ''
                nat_name = ALPHA3_TO_NAME.get(nat_code, nat_code)
                passport = getattr(g, 'passport_number', '') or ''
                parts = [f"[NN] {g.full_name}"]
                if passport:
                    parts.append(passport)
                if nat_code:
                    parts.append(f"({nat_name})")
                lines.append(f"  {i}. {' - '.join(parts)}")
            else:
                doc_label = DOC_TYPE_LABELS.get(g.document_type, g.document_type or "")
                parts = [f"[VN] {g.full_name}"]
                if g.identification_number:
                    parts.append(g.identification_number)
                if doc_label:
                    parts.append(f"({doc_label})")
                lines.append(f"  {i}. {' - '.join(parts)}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/zalo_service.py
git commit -m "feat: update Zalo notification for foreign guests"
```

---

**Note:** `frontend/index.html` is listed in the spec's "Files to modify" but requires no changes — all Step 2/3 HTML is dynamically rendered in `app.js`.

## Chunk 4: Frontend — API + Step 2 UI

### Task 9: Add Frontend API Methods

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Add ocrBatchExtractForeign and exportForeignCheckins methods**

In `frontend/js/api.js`, after `ocrBatchExtract` method (after line 135), add:

```javascript
  /**
   * Upload multiple files for batch foreign passport extraction
   */
  async ocrBatchExtractForeign(files) {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    return this.uploadForm('/api/ocr/batch-extract-foreign', formData);
  },
```

After `exportCheckinsByRange` method (after line 201), add:

```javascript
  /**
   * Export foreign guest check-ins as XML and trigger download
   */
  async exportForeignCheckinsByRange(fromDate, toDate) {
    const url = new URL(`${API_URL}/api/checkins/export-foreign`);
    url.searchParams.append('from_date', fromDate);
    url.searchParams.append('to_date', toDate);
    const response = await fetch(url.toString());
    if (!response.ok) {
      const err = await response.json().catch(() => null);
      throw new Error(err?.detail || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `foreign_checkin_export.xml`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: add foreign guest API methods to frontend"
```

---

### Task 10: Rewrite Step 2 UI — Guest Type Buttons

**Files:**
- Modify: `frontend/js/app.js` (lines 492-664)

- [ ] **Step 1: Replace renderStep2 function**

In `frontend/js/app.js`, replace the entire `renderStep2` function (lines 492-578) with:

```javascript
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
            const isForeign = g.guest_type === 'foreign';
            const name = g.full_name || 'Không xác định';
            const idDisplay = isForeign
                ? (g.passport_number || 'Chưa có số hộ chiếu')
                : (g.identification_number || 'Chưa có số giấy tờ');
            const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
            const badgeText = isForeign ? 'NN' : 'VN';
            const extraInfo = isForeign && g.nationality_code ? ` • ${g.nationality_code}` : '';
            const hasWarning = isForeign ? !g.passport_number : !g.identification_number;

            guestsHtml += `
                <div class="guest-card ${hasWarning ? 'guest-card__warn' : ''}">
                    <div class="guest-card__header">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="guest-badge ${badgeClass}">${badgeText}</span>
                            <span class="guest-card__name">${escapeHtml(name)}</span>
                        </div>
                        <button class="guest-card__remove" onclick="removeGuest(${i})">&#10005;</button>
                    </div>
                    <div class="guest-card__meta">
                        <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${getDocTypeLabel(g.document_type)}</span>
                        <span>${escapeHtml(idDisplay)}${escapeHtml(extraInfo)}</span>
                    </div>
                </div>
            `;
        });
    }

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Giấy tờ tùy thân</div>
                <div class="section-header__subtitle">Chọn loại khách và tải ảnh giấy tờ</div>
            </div>
        </div>
        ${warningHtml}
        <div class="guest-type-buttons">
            <button class="guest-type-btn guest-type-btn--vn" id="btnAddVN">
                <span style="font-size:20px;">🇻🇳</span>
                <span class="guest-type-btn__label">+ Thêm khách VN</span>
            </button>
            <button class="guest-type-btn guest-type-btn--foreign" id="btnAddForeign">
                <span style="font-size:20px;">🌍</span>
                <span class="guest-type-btn__label">+ Thêm khách NN</span>
            </button>
        </div>
        <input type="file" id="vnFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="vnFileGallery" accept="image/jpeg,image/png,image/webp" multiple style="display:none">
        <input type="file" id="foreignFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="foreignFileGallery" accept="image/jpeg,image/png,image/webp" multiple style="display:none">
        ${guestsHtml}
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
```

- [ ] **Step 2: Replace bindStep2Events function**

Replace `bindStep2Events` (lines 581-597) with:

```javascript
function bindStep2Events() {
    const btnAddVN = document.getElementById('btnAddVN');
    const btnAddForeign = document.getElementById('btnAddForeign');

    if (btnAddVN) {
        btnAddVN.addEventListener('click', () => {
            _showUploadChoice('vn');
        });
    }
    if (btnAddForeign) {
        btnAddForeign.addEventListener('click', () => {
            _showUploadChoice('foreign');
        });
    }

    document.getElementById('vnFileCamera').addEventListener('change', (e) => handleVNIDFiles(e));
    document.getElementById('vnFileGallery').addEventListener('change', (e) => handleVNIDFiles(e));
    document.getElementById('foreignFileCamera').addEventListener('change', (e) => handleForeignIDFiles(e));
    document.getElementById('foreignFileGallery').addEventListener('change', (e) => handleForeignIDFiles(e));

    document.getElementById('btnStep2Back').addEventListener('click', () => { wizardState.currentStep = 1; renderWizardStep(); });
    document.getElementById('btnStep2Next').addEventListener('click', () => { wizardState.currentStep = 3; renderWizardStep(); });
}

function _showUploadChoice(guestType) {
    const cameraId = guestType === 'vn' ? 'vnFileCamera' : 'foreignFileCamera';
    const galleryId = guestType === 'vn' ? 'vnFileGallery' : 'foreignFileGallery';
    const typeLabel = guestType === 'vn' ? 'khách Việt Nam' : 'khách nước ngoài';

    const overlay = openBottomSheet(`
        <div style="text-align:center;margin-bottom:var(--space-lg);">
            <h3 style="font-size:16px;font-weight:700;">Tải ảnh giấy tờ ${typeLabel}</h3>
            <p style="font-size:13px;color:var(--color-text-muted);margin-top:4px;">${guestType === 'vn' ? 'CCCD, CMND, VNeID, Khai sinh' : 'Hộ chiếu (Passport)'}</p>
        </div>
        <div style="display:flex;gap:var(--space-md);">
            <button class="btn btn--primary flex-1" id="btnSheetCamera">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
                Chụp ảnh
            </button>
            <button class="btn btn--secondary flex-1" id="btnSheetGallery">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                Thư viện
            </button>
        </div>
        <div style="text-align:center;margin-top:var(--space-md);">
            <div style="font-size:11px;color:var(--color-text-muted);">JPG, PNG, WEBP — Tối đa 10MB</div>
        </div>
    `);

    overlay.querySelector('#btnSheetCamera').addEventListener('click', () => {
        closeBottomSheet(overlay);
        document.getElementById(cameraId).click();
    });
    overlay.querySelector('#btnSheetGallery').addEventListener('click', () => {
        closeBottomSheet(overlay);
        document.getElementById(galleryId).click();
    });
}
```

- [ ] **Step 3: Rename existing handleIDFiles to handleVNIDFiles and add handleForeignIDFiles**

Replace `handleIDFiles` function (lines 604-664) with:

```javascript
async function handleVNIDFiles(e) {
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
            <div class="ocr-processing__title">Đang quét ${validFiles.length} ảnh giấy tờ VN</div>
            <div class="ocr-processing__subtitle">Vui lòng đợi trong giây lát...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBatchExtract(validFiles);
        const newGuests = result.guests || [];
        newGuests.forEach(newG => {
            newG.guest_type = 'vietnamese';
            if (!newG.identification_number) {
                wizardState.guests.push(newG);
                return;
            }
            const existing = wizardState.guests.find(g => g.guest_type === 'vietnamese' && g.identification_number === newG.identification_number);
            if (existing) {
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
        showToast(`Đã quét ${result.total_profiles} hồ sơ VN`, 'success');
    } catch (error) {
        showToast(error.message || 'Lỗi khi quét giấy tờ', 'error');
        renderWizardStep();
    }
    e.target.value = '';
}

async function handleForeignIDFiles(e) {
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
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg>
            </div></div>
            <div class="ocr-processing__title">Đang quét ${validFiles.length} ảnh hộ chiếu</div>
            <div class="ocr-processing__subtitle">Vui lòng đợi trong giây lát...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBatchExtractForeign(validFiles);
        const newGuests = result.guests || [];
        newGuests.forEach(newG => {
            if (!newG.passport_number) {
                wizardState.guests.push(newG);
                return;
            }
            const existing = wizardState.guests.find(g => g.guest_type === 'foreign' && g.passport_number === newG.passport_number);
            if (existing) {
                for (const key of Object.keys(newG)) {
                    if ((!existing[key] || existing[key] === 'Unknown') && newG[key] && newG[key] !== 'Unknown') {
                        existing[key] = newG[key];
                    }
                }
            } else {
                wizardState.guests.push(newG);
            }
        });
        renderWizardStep();
        showToast(`Đã quét ${result.total_profiles} hồ sơ nước ngoài`, 'success');
    } catch (error) {
        showToast(error.message || 'Lỗi khi quét hộ chiếu', 'error');
        renderWizardStep();
    }
    e.target.value = '';
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: rewrite Step 2 with VN/foreign guest type buttons"
```

---

## Chunk 5: Frontend — Step 3 Review + Export + CSS

### Task 11: Rewrite Step 3 Review Form for Mixed Guests

**Files:**
- Modify: `frontend/js/app.js` (lines 669-851)

- [ ] **Step 1: Replace renderStep3 guest list section**

In `frontend/js/app.js`, replace the guest list rendering in `renderStep3` (lines 704-753) with:

```javascript
    // Guest list — editable, different form per guest_type
    let guestsHtml = `<div class="review-section"><div class="review-section__title">Danh sách khách (${wizardState.guests.length})</div>`;
    wizardState.guests.forEach((g, i) => {
        const isForeign = g.guest_type === 'foreign';
        const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
        const badgeText = isForeign ? 'Nước ngoài' : 'Việt Nam';

        guestsHtml += `
            <div class="guest-card" style="margin-bottom:var(--space-md);">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:var(--space-md);">
                    <span class="guest-badge ${badgeClass}">${badgeText}</span>
                    <span style="font-weight:700;font-size:14px;color:var(--color-primary);">Khách ${i + 1}</span>
                </div>
                <div class="result-form">
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Họ và tên *</span></div>
                        <input class="result-field__input" type="text" id="g_name_${i}" value="${escapeHtml(g.full_name || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Giới tính</span></div>
                        <select class="result-field__select" id="g_gender_${i}">
                            <option value="">-- Chọn --</option>
                            ${isForeign ? `
                                <option value="M" ${g.gender === 'M' ? 'selected' : ''}>M (Male)</option>
                                <option value="F" ${g.gender === 'F' ? 'selected' : ''}>F (Female)</option>
                            ` : `
                                <option value="Nam" ${g.gender === 'Nam' ? 'selected' : ''}>Nam</option>
                                <option value="Nữ" ${g.gender === 'Nữ' ? 'selected' : ''}>Nữ</option>
                            `}
                        </select>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày sinh</span></div>
                        <input class="result-field__input" type="text" id="g_dob_${i}" value="${escapeHtml(g.date_of_birth || '')}" placeholder="DD/MM/YYYY">
                    </div>
                    ${isForeign ? `
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Số hộ chiếu *</span></div>
                            <input class="result-field__input" type="text" id="g_passport_${i}" value="${escapeHtml(g.passport_number || '')}">
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Mã quốc tịch (ISO alpha-3)</span></div>
                            <input class="result-field__input" type="text" id="g_natcode_${i}" value="${escapeHtml(g.nationality_code || '')}" placeholder="VD: GBR, CHN, DEU" maxlength="3" style="text-transform:uppercase;">
                        </div>
                    ` : `
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
                                <option value="vneid" ${g.document_type === 'vneid' ? 'selected' : ''}>VNeID</option>
                            </select>
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Quốc tịch</span></div>
                            <input class="result-field__input" type="text" id="g_nationality_${i}" value="${escapeHtml(g.nationality || '')}" placeholder="VD: Việt Nam">
                        </div>
                    `}
                </div>
            </div>
        `;
    });
    guestsHtml += '</div>';
```

- [ ] **Step 2: Update saveStep3ToState for foreign guest fields**

Replace `saveStep3ToState` (lines 787-809) with:

```javascript
function saveStep3ToState() {
    const contactName = document.getElementById('f_contact_name');
    const contactPhone = document.getElementById('f_contact_phone');
    if (contactName) wizardState.contact.name = contactName.value.trim() || null;
    if (contactPhone) wizardState.contact.phone = contactPhone.value.trim() || null;

    wizardState.guests.forEach((g, i) => {
        const name = document.getElementById(`g_name_${i}`);
        const gender = document.getElementById(`g_gender_${i}`);
        const dob = document.getElementById(`g_dob_${i}`);

        if (name) g.full_name = name.value.trim();
        if (gender) g.gender = gender.value || null;
        if (dob) g.date_of_birth = dob.value.trim() || null;

        if (g.guest_type === 'foreign') {
            const passport = document.getElementById(`g_passport_${i}`);
            const natCode = document.getElementById(`g_natcode_${i}`);
            if (passport) g.passport_number = passport.value.trim();
            if (natCode) g.nationality_code = natCode.value.trim().toUpperCase() || null;
        } else {
            const id = document.getElementById(`g_id_${i}`);
            const addr = document.getElementById(`g_addr_${i}`);
            const docType = document.getElementById(`g_doctype_${i}`);
            const nationality = document.getElementById(`g_nationality_${i}`);
            if (id) g.identification_number = id.value.trim();
            if (addr) g.address = addr.value.trim() || null;
            if (docType) g.document_type = docType.value || null;
            if (nationality) g.nationality = nationality.value.trim() || null;
        }
    });
}
```

- [ ] **Step 3: Update handleConfirmCheckin validation and payload**

Replace the validation + payload section of `handleConfirmCheckin` (lines 812-841) with:

```javascript
async function handleConfirmCheckin() {
    saveStep3ToState();

    // Validate
    if (!wizardState.contact.name) { showToast('Vui lòng nhập họ tên liên hệ', 'error'); return; }
    if (!wizardState.contact.phone) { showToast('Vui lòng nhập số điện thoại', 'error'); return; }

    for (let i = 0; i < wizardState.guests.length; i++) {
        const g = wizardState.guests[i];
        if (!g.full_name) { showToast(`Khách ${i + 1}: Họ tên không được để trống`, 'error'); return; }
        if (g.guest_type === 'foreign') {
            if (!g.passport_number) { showToast(`Khách ${i + 1}: Số hộ chiếu không được để trống`, 'error'); return; }
        } else {
            if (!g.identification_number) { showToast(`Khách ${i + 1}: Số giấy tờ không được để trống`, 'error'); return; }
        }
    }

    const btn = document.getElementById('btnConfirmCheckin');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Đang xử lý...';

    try {
        const payload = {
            booking: wizardState.booking,
            contact: wizardState.contact,
            guests: wizardState.guests.map(g => ({
                guest_type: g.guest_type || 'vietnamese',
                full_name: g.full_name,
                gender: g.gender || null,
                date_of_birth: g.date_of_birth || null,
                identification_number: g.identification_number || null,
                address: g.address || null,
                document_type: g.document_type || null,
                nationality: g.nationality || null,
                passport_number: g.passport_number || null,
                nationality_code: g.nationality_code || null,
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
```

- [ ] **Step 4: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: rewrite Step 3 with conditional forms per guest type"
```

---

### Task 12: Update Export UI for XML Option

**Files:**
- Modify: `frontend/js/app.js` (export section, lines 178-257)

- [ ] **Step 1: Add XML export button to export mode**

In `frontend/js/app.js`, in the `enterExportMode` function, after the closing `</button>` tag of `btnDoExport` (line 217), add a second button inside the template literal:

```html
                <button class="btn btn--secondary btn--full" id="btnDoExportForeign" style="margin-top:var(--space-md);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M2 12h20"/>
                    </svg>
                    Xuất XML khách nước ngoài
                </button>
```

After `document.getElementById('btnDoExport').addEventListener('click', handleExport);` (line 222), add:

```javascript
    document.getElementById('btnDoExportForeign').addEventListener('click', handleExportForeign);
```

- [ ] **Step 2: Add handleExportForeign function**

After `handleExport` function (after line 257), add:

```javascript
async function handleExportForeign() {
    const fromInput = document.getElementById('exportFromDate').value;
    const toInput = document.getElementById('exportToDate').value;

    if (!fromInput || !toInput) {
        showToast('Vui lòng chọn đầy đủ ngày', 'error');
        return;
    }

    const fromDate = _fromInputDate(fromInput);
    const toDate = _fromInputDate(toInput);

    const btn = document.getElementById('btnDoExportForeign');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin-right:6px;vertical-align:middle;"></span> Đang xuất...';

    try {
        await api.exportForeignCheckinsByRange(fromDate, toDate);
        showToast('Đã tải file XML thành công', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                <circle cx="12" cy="12" r="10"/>
                <path d="M2 12h20"/>
            </svg>
            Xuất XML khách nước ngoài`;
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: add XML export button for foreign guests"
```

---

### Task 13: Add CSS Styles for Guest Badges and Type Buttons

**Files:**
- Modify: `frontend/css/style.css` (append at end)

- [ ] **Step 1: Add guest badge and type button styles**

Append to `frontend/css/style.css`:

```css
/* ============================================
   GUEST TYPE BADGES & BUTTONS
   ============================================ */
.guest-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.03em;
}

.guest-badge--vn {
    background: #DCFCE7;
    color: #16A34A;
}

.guest-badge--foreign {
    background: #DBEAFE;
    color: #2563EB;
}

.guest-type-buttons {
    display: flex;
    gap: var(--space-md);
    margin-bottom: var(--space-xl);
}

.guest-type-btn {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: var(--space-lg) var(--space-md);
    border-radius: var(--radius-lg);
    border: 2px solid;
    background: none;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: var(--font-body);
}

.guest-type-btn--vn {
    border-color: #16A34A;
    background: #F0FDF4;
}

.guest-type-btn--vn:active {
    background: #DCFCE7;
}

.guest-type-btn--foreign {
    border-color: #2563EB;
    background: #EFF6FF;
}

.guest-type-btn--foreign:active {
    background: #DBEAFE;
}

.guest-type-btn__label {
    font-size: 13px;
    font-weight: 600;
}

.guest-type-btn--vn .guest-type-btn__label {
    color: #16A34A;
}

.guest-type-btn--foreign .guest-type-btn__label {
    color: #2563EB;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: add CSS styles for guest type badges and buttons"
```

---

### Task 14: Update History Detail for Foreign Guests

**Files:**
- Modify: `frontend/js/app.js` (showCheckinDetail function, lines 987-1026)

- [ ] **Step 1: Update guest rendering in detail view**

In `showCheckinDetail`, replace the guest HTML template (lines 991-999) with:

```javascript
        const guestsHtml = ci.guests.map(g => {
            const isForeign = (g.guest_type === 'foreign');
            const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
            const badgeLabel = isForeign ? 'NN' : 'VN';
            const idDisplay = isForeign ? (g.passport_number || '') : (g.identification_number || '');
            const natInfo = isForeign && g.nationality_code ? ` • ${g.nationality_code}` : '';

            return `
                <div style="padding:var(--space-md) 0;border-bottom:1px solid var(--color-divider);">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span class="guest-badge ${badgeClass}">${badgeLabel}</span>
                        <span style="font-weight:600;font-size:14px;">${escapeHtml(g.full_name)}</span>
                    </div>
                    <div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">
                        <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${getDocTypeLabel(g.document_type)}</span>
                        ${escapeHtml(idDisplay)}${escapeHtml(natInfo)} ${g.gender ? '• ' + escapeHtml(g.gender) : ''} ${g.date_of_birth ? '• ' + escapeHtml(g.date_of_birth) : ''}
                    </div>
                    ${!isForeign && g.address ? `<div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">${escapeHtml(g.address)}</div>` : ''}
                </div>
            `;
        }).join('');
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: update history detail view for foreign guests"
```

---

### Task 15: Final Integration Test

- [ ] **Step 1: Start the backend**

Run: `cd backend && python -m uvicorn app.main:app --port 2701 --reload`

- [ ] **Step 2: Run migration if not done**

Run: `mysql -u root -p checkin_db < database/005_foreign_guests.sql`

- [ ] **Step 3: Manual test — mixed guest check-in**

1. Open `http://localhost:2701` (or frontend URL)
2. Click Check-in → upload booking image
3. In Step 2, click "+ Thêm khách VN" → upload CCCD images
4. Click "+ Thêm khách NN" → upload passport images
5. Verify both types appear with correct badges
6. In Step 3, verify VN guests show CCCD fields, foreign guests show passport fields
7. Submit → verify success

- [ ] **Step 4: Manual test — export**

1. Go to Export screen
2. Click "Xuất file Excel" → verify only VN guests in file
3. Click "Xuất XML khách nước ngoài" → verify XML format matches template

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete foreign guest check-in flow"
```
