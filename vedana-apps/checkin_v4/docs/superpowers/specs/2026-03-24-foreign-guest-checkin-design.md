# Foreign Guest Check-in Flow — Design Spec

## Overview

Mở rộng luồng check-in hiện tại để hỗ trợ khách nước ngoài. Một booking có thể mix cả khách Việt Nam và khách nước ngoài. User chọn loại khách trước khi upload ảnh giấy tờ. Export tách riêng: Excel cho khách VN, XML cho khách nước ngoài.

## Design Decisions

| Quyết định | Lựa chọn |
|---|---|
| Mix khách trong 1 booking | Có — VN + NN cùng lúc |
| Nhập thông tin khách NN | OCR từ ảnh hộ chiếu |
| UI chọn loại khách | 2 nút riêng: "+ Thêm khách VN" / "+ Thêm khách NN" |
| Export | Excel (khách VN) + XML (khách NN) tách riêng |
| Số phòng cho XML | Lấy tự động từ room_assignments |
| Database approach | Mở rộng bảng guests hiện tại (thêm trường) |

---

## 1. Database Schema

Migration file: `database/005_foreign_guests.sql`

Mở rộng bảng `guests` — thêm các cột:

```sql
ALTER TABLE guests
  ADD COLUMN guest_type VARCHAR(20) NOT NULL DEFAULT 'vietnamese',
  ADD COLUMN passport_number VARCHAR(50) DEFAULT NULL,
  ADD COLUMN nationality_code VARCHAR(10) DEFAULT NULL;

-- Đổi identification_number thành nullable
ALTER TABLE guests MODIFY identification_number VARCHAR(50) NULL;

-- Bỏ unique constraint cũ, thay bằng 2 constraint riêng
ALTER TABLE guests DROP INDEX uq_guest_per_checkin;
ALTER TABLE guests
  ADD UNIQUE INDEX uq_vn_guest (checkin_id, identification_number),
  ADD UNIQUE INDEX uq_foreign_guest (checkin_id, passport_number);

INSERT IGNORE INTO schema_migrations (version) VALUES ('005_foreign_guests');
```

**Note on MySQL NULL uniqueness:** MySQL unique indexes allow multiple NULL values. This means `uq_vn_guest` won't block foreign guests (who have `identification_number = NULL`), and `uq_foreign_guest` won't block VN guests (who have `passport_number = NULL`). This is the intended behavior. Application-level validation (Pydantic) enforces the correct required field per guest type.

### Field usage by guest type

| Field | Vietnamese | Foreign |
|---|---|---|
| `guest_type` | "vietnamese" | "foreign" |
| `identification_number` | Số CCCD/CMND (required) | NULL |
| `passport_number` | NULL | Số hộ chiếu (required) |
| `nationality_code` | NULL | ISO alpha-3 (GBR, CHN, DEU...) |
| `nationality` (text) | "Việt Nam" | Derived from `nationality_code` via mapping |
| `address` | Địa chỉ VN | NULL |
| `document_type` | cccd/cmnd/vneid/birth_certificate | "passport" |
| `gender` | "Nam"/"Nữ" | "M"/"F" |

### Nationality code systems

Hệ thống hiện tại dùng **ISO alpha-2** (VN, GB, DE) cho Excel export khách VN. Khách nước ngoài lưu **ISO alpha-3** (GBR, DEU, CHN) trong `nationality_code` — đây là yêu cầu của format XML khai báo tạm trú.

Hai hệ thống tách biệt:
- Excel export (VN guests): `nationality` text → alpha-2 qua `_NATIONALITY_CODE_MAP` hiện tại
- XML export (foreign guests): `nationality_code` alpha-3 trực tiếp từ DB

Thêm mapping `_ALPHA3_TO_NAME` để hiển thị tên quốc gia từ alpha-3 code (cho Zalo notification, UI display):

```python
_ALPHA3_TO_NAME = {
    "GBR": "United Kingdom", "CHN": "China", "DEU": "Germany",
    "KOR": "Korea", "ARG": "Argentina", "FRA": "France",
    "USA": "United States", "JPN": "Japan", "AUS": "Australia",
    "THA": "Thailand", "SGP": "Singapore", "IND": "India",
    "RUS": "Russia", "MYS": "Malaysia", "IDN": "Indonesia",
    # ... mở rộng khi cần
}
```

---

## 2. OCR Service — Passport Extraction

### New function: `extract_passport_info_async(image_path)`

Gửi ảnh hộ chiếu tới GPT-5.1 Vision. Trích xuất:
- `ho_ten` — full name
- `ngay_sinh` — date of birth (DD/MM/YYYY)
- `gioi_tinh` — gender (M/F)
- `ma_quoc_tich` — nationality code ISO alpha-3
- `so_ho_chieu` — passport number

Cơ chế tự sửa ảnh ngược: nếu LLM trả "0" → xoay 180° → retry.

### New function: `process_single_passport(image_path)`

Pipeline riêng cho hộ chiếu, **không đi qua `process_single_image`** hiện tại:
1. `check_image_orientation_async(image_path)` → nhận diện hướng + xoay
2. `rotate_image(image_path, angle)` → xoay nếu cần
3. `extract_passport_info_async(rotated_path)` → trích xuất thông tin

Lý do tách riêng: `process_single_image` route tới `extract_mat_truoc_info_async` / `extract_mat_sau_info_async` dựa trên `loai_mat` — các hàm này có prompt tiếng Việt chuyên cho CCCD/CMND, không phù hợp cho hộ chiếu nước ngoài.

### New function: `batch_extract_foreign_info_async(image_paths)`

- Gọi `process_single_passport` cho từng ảnh song song
- Group profile theo `so_ho_chieu`
- Convert sang frontend format:

```json
{
  "full_name": "GARY LEWIS",
  "gender": "M",
  "date_of_birth": "25/06/1968",
  "passport_number": "549588610",
  "nationality_code": "GBR",
  "document_type": "passport",
  "guest_type": "foreign"
}
```

### Existing function reuse

- `check_image_orientation_async` — không đổi, đã nhận diện `loai_giay_to: "passport"`
- `rotate_image` — không đổi
- `encode_image_to_base64`, `get_mime_type`, `_parse_json_response` — reuse

### New API endpoint

`POST /api/ocr/batch-extract-foreign` — thêm vào file `backend/app/api/routes/ocr.py` (cùng file với `/batch-extract` hiện tại). Nhận multipart files, gọi `batch_extract_foreign_info_async`, trả `BatchExtractForeignResult`.

---

## 3. Frontend UI Changes

### Step 1 (Booking): Không thay đổi.

### Step 2 (Upload giấy tờ): Thay đổi lớn.

**Before:** Một vùng upload duy nhất + nút camera/gallery.

**After:**
- Bỏ vùng upload mặc định ở đầu trang
- Thay bằng 2 nút luôn hiển thị:
  - **"+ Thêm khách VN"** (xanh lá `#16a34a`) → mở camera/gallery → gọi `POST /api/ocr/batch-extract`
  - **"+ Thêm khách NN"** (xanh dương `#2563eb`) → mở camera/gallery → gọi `POST /api/ocr/batch-extract-foreign`
- Danh sách khách hiển thị chung bên dưới, mỗi card có:
  - Badge **VN** (xanh lá): tên + số CCCD
  - Badge **NN** (xanh dương): tên + số hộ chiếu + mã quốc tịch
  - Nút xóa (×)
- Có thể thêm nhiều lần xen kẽ VN/NN

### Frontend handler functions

Tách thành 2 handler riêng:
- `handleVNIDFiles(files)` — gọi `api.ocrBatchExtract(files)`, merge theo `identification_number` (logic hiện tại)
- `handleForeignIDFiles(files)` — gọi `api.ocrBatchExtractForeign(files)`, merge theo `passport_number`

Cả hai đều append kết quả vào `wizardState.guests[]` chung.

### Step 3 (Review & Confirm): Form khác nhau theo loại khách.

**Khách VN (giữ nguyên):**
- Họ tên, Giới tính (Nam/Nữ dropdown), Ngày sinh, Số CCCD, Địa chỉ, Loại giấy tờ, Quốc tịch

**Khách NN (form mới):**
- Họ tên, Giới tính (M/F dropdown), Ngày sinh, Số hộ chiếu, Mã quốc tịch (dropdown ISO alpha-3)

### Frontend validation updates

Validation ở Step 3 phân nhánh theo `guest_type`:
- **VN:** `full_name` + `identification_number` required (giữ nguyên)
- **NN:** `full_name` + `passport_number` required (thay cho `identification_number`)

### wizardState changes

```javascript
wizardState.guests = [
  {
    guest_type: "vietnamese",
    full_name: "Nguyễn Văn A",
    gender: "Nam",
    date_of_birth: "01/01/1990",
    identification_number: "001202009143",
    address: "...",
    document_type: "cccd",
    nationality: "Việt Nam"
  },
  {
    guest_type: "foreign",
    full_name: "GARY LEWIS",
    gender: "M",
    date_of_birth: "25/06/1968",
    passport_number: "549588610",
    nationality_code: "GBR",
    document_type: "passport"
  }
]
```

---

## 4. Backend API Changes

### Schema updates (`schemas/checkin.py`)

**GuestCreate** — thêm trường + validation:

```python
class GuestCreate(BaseModel):
    guest_type: str = "vietnamese"  # "vietnamese" | "foreign"
    full_name: str = Field(..., min_length=1)
    gender: str | None = None
    date_of_birth: str | None = None
    # Vietnamese fields
    identification_number: str | None = None  # Was: str = Field(..., min_length=1)
    address: str | None = None
    document_type: str | None = None
    nationality: str | None = None
    # Foreign fields
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

**GuestResponse** — thêm trường (tất cả optional cho backward compat):

```python
class GuestResponse(BaseModel):
    id: int
    guest_type: str
    full_name: str
    gender: str | None
    date_of_birth: str | None
    identification_number: str | None  # Was: str (required)
    address: str | None
    document_type: str | None
    nationality: str | None
    passport_number: str | None
    nationality_code: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

**GuestExtracted** — thêm trường:

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

**New schemas:**

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

### POST /api/checkins — code changes needed

File `backend/app/api/routes/checkins.py`, hàm `create_checkin`:

```python
# Line 59 hiện tại (sẽ crash nếu identification_number is None):
identification_number=guest_data.identification_number.strip()

# Đổi thành:
identification_number=guest_data.identification_number.strip() if guest_data.identification_number else None,
passport_number=guest_data.passport_number.strip() if guest_data.passport_number else None,
nationality_code=guest_data.nationality_code.strip() if guest_data.nationality_code else None,
guest_type=guest_data.guest_type,
```

### ORM Model updates (`models/checkin.py`)

```python
class Guest(Base):
    # ... existing fields ...
    identification_number = Column(String(50), nullable=True)  # Was: nullable=False
    # New fields:
    guest_type = Column(String(20), nullable=False, default="vietnamese")
    passport_number = Column(String(50), nullable=True)
    nationality_code = Column(String(10), nullable=True)
```

---

## 5. Export

### Excel export (existing endpoint)

`GET /api/checkins/export?from_date=...&to_date=...`

Filter thêm: chỉ lấy guests có `guest_type == "vietnamese"` (hoặc `guest_type IS NULL` cho backward compat với data cũ).

### XML export (new endpoint)

`GET /api/checkins/export-foreign?from_date=...&to_date=...`

Output format theo `KHAI_BAO_TAM_TRU`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<KHAI_BAO_TAM_TRU>
  <THONG_TIN_KHACH>
    <so_thu_tu>1</so_thu_tu>
    <ho_ten>GARY LEWIS</ho_ten>
    <ngay_sinh>25/06/1968</ngay_sinh>
    <ngay_sinh_dung_den>D</ngay_sinh_dung_den>
    <gioi_tinh>M</gioi_tinh>
    <ma_quoc_tich>GBR</ma_quoc_tich>
    <so_ho_chieu>549588610</so_ho_chieu>
    <so_phong>A1.404</so_phong>
    <ngay_den>15/03/2026</ngay_den>
    <ngay_di_du_kien>16/03/2026</ngay_di_du_kien>
    <ngay_tra_phong>16/03/2026</ngay_tra_phong>
  </THONG_TIN_KHACH>
</KHAI_BAO_TAM_TRU>
```

**Field mapping:**

| XML field | Source |
|---|---|
| `so_thu_tu` | Auto-increment counter |
| `ho_ten` | guests.full_name |
| `ngay_sinh` | guests.date_of_birth |
| `ngay_sinh_dung_den` | Default "D" |
| `gioi_tinh` | guests.gender (M/F) |
| `ma_quoc_tich` | guests.nationality_code |
| `so_ho_chieu` | guests.passport_number |
| `so_phong` | See room number logic below |
| `ngay_den` | checkins.arrival_date |
| `ngay_di_du_kien` | checkins.departure_date |
| `ngay_tra_phong` | checkins.departure_date |

### Room number logic for XML export

`room_assignments` links `checkin_id` → `room_id`. Một checkin có thể có nhiều room assignments.

Query logic:
```sql
SELECT r.room_number
FROM room_assignments ra
JOIN rooms r ON ra.room_id = r.id
WHERE ra.checkin_id = :checkin_id
  AND ra.released_at IS NULL
ORDER BY ra.assigned_at ASC
LIMIT 1
```

Nếu checkin chưa được gán phòng → `<so_phong></so_phong>` (empty). Nếu có nhiều phòng → lấy phòng đầu tiên (assigned sớm nhất). Tất cả foreign guests trong cùng 1 checkin sẽ dùng chung room number này.

---

## 6. Zalo Notification

File `backend/app/services/zalo_service.py`, hàm `_build_checkin_message`.

Hiện tại truy cập `g.identification_number` trực tiếp — sẽ crash nếu NULL cho foreign guests.

Đổi thành phân nhánh theo `guest_type`:

```
👥 Danh sách khách (3):
  1. [VN] Nguyễn Văn A - 001202009143 (CCCD)
  2. [NN] GARY LEWIS - 549588610 (GBR)
  3. [NN] KATIE ROUTLEDGE - 129141489 (GBR)
```

Logic:
- Nếu `guest_type == "foreign"`: hiển thị `passport_number` + `nationality_code`
- Nếu `guest_type == "vietnamese"` (hoặc None cho data cũ): hiển thị `identification_number` + `document_type`

---

## Files to modify

| File | Change |
|---|---|
| `database/005_foreign_guests.sql` | New migration |
| `backend/app/models/checkin.py` | Add `guest_type`, `passport_number`, `nationality_code` columns; make `identification_number` nullable |
| `backend/app/schemas/checkin.py` | Update `GuestCreate` (validation), `GuestResponse`, `GuestExtracted`; add `ForeignGuestExtracted`, `BatchExtractForeignResult` |
| `backend/app/services/ocr_service.py` | Add `extract_passport_info_async`, `process_single_passport`, `batch_extract_foreign_info_async` |
| `backend/app/api/routes/ocr.py` | Add `POST /batch-extract-foreign` endpoint |
| `backend/app/api/routes/checkins.py` | Fix null-safe `identification_number` in `create_checkin`; filter VN-only in Excel export; add XML export endpoint + `_ALPHA3_TO_NAME` mapping |
| `backend/app/services/zalo_service.py` | Branch notification format by `guest_type`; null-safe `identification_number` |
| `frontend/js/app.js` | Step 2: add 2 buttons + `handleForeignIDFiles`; Step 3: conditional form per `guest_type`; validation branching |
| `frontend/js/api.js` | Add `api.ocrBatchExtractForeign()` and `api.exportForeignCheckins()` |
| `frontend/index.html` | Update Step 2 & 3 HTML structure |
| `frontend/css/style.css` | Badge styles (VN green, NN blue), foreign guest form styles |
