# Thiết kế tính năng Xếp phòng

## Tổng quan

Thêm tính năng "Xếp phòng" cho app Checkin Vedana. Khi vào app, người dùng thấy 2 lựa chọn: **Check-in** (luồng hiện tại) hoặc **Xếp phòng** (gán phòng cho checkin đã tạo). Một checkin có thể được gán nhiều phòng, phòng đã gán bị khóa cho đến khi trả phòng thủ công.

## Luồng người dùng

### Màn hình Landing
- Hiện khi vào app, ẩn bottom nav
- 2 card lớn: "Check-in" và "Xếp phòng"
- Top bar giữ nguyên "Checkin Vedana"

### Luồng Check-in
- Giữ nguyên wizard 3 bước hiện tại
- Bottom nav hiện lại (Check-in, Lịch sử, Thông tin)
- Thêm nút back (←) trên top bar để quay lại landing

### Luồng Xếp phòng
1. **Danh sách checkin** - chia 2 nhóm:
   - "Chưa xếp phòng" (ở trên, có badge đếm số lượng)
   - "Đã xếp phòng" (ở dưới, hiện danh sách phòng đã gán + nút "Trả phòng" từng phòng)
   - Nhấn vào checkin ở **cả 2 nhóm** đều mở luồng chọn phòng (để thêm phòng mới)
2. **Nhấn vào 1 checkin** → chọn Building (grid: danh sách lấy động từ API)
3. **Chọn phòng** trong building:
   - Grid phòng: trắng = trống, xám = đã gán (disabled), cam = đang chọn
   - Mỗi ô hiện số phòng và loại phòng (room_type)
   - Chọn được nhiều phòng
   - Nút "Xác nhận" để gán
4. Bottom nav ẩn, chỉ có nút back trên top bar

## Database

### Bảng `rooms` (đã tạo)
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INT AUTO_INCREMENT PK | |
| room_number | VARCHAR(50) NOT NULL UNIQUE | Số phòng |
| room_type | VARCHAR(50) NOT NULL | Loại phòng |
| building | VARCHAR(50) NOT NULL | Tòa nhà |
| created_at | DATETIME DEFAULT NOW() | |

### Bảng `room_assignments` (mới)
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INT AUTO_INCREMENT PK | |
| checkin_id | INT FK → checkins.id | Checkin được gán phòng |
| room_id | INT FK → rooms.id | Phòng được gán |
| assigned_at | DATETIME DEFAULT NOW() | Thời điểm gán |
| released_at | DATETIME NULL | NULL = đang sử dụng, có giá trị = đã trả |

**Ràng buộc:** UNIQUE trên `(room_id)` khi `released_at IS NULL` — đảm bảo 1 phòng chỉ gán cho 1 checkin tại 1 thời điểm. Vì MySQL không hỗ trợ partial unique index, sẽ kiểm tra logic này ở backend.

**Migration file:** `database/004_room_assignments.sql`

**SQLAlchemy models:** Tạo `Room` và `RoomAssignment` trong `backend/app/models/room.py`

### Bảng `checkins` và `guests`
Giữ nguyên, không cần thêm cột.

## Backend API

### Endpoints mới

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/api/rooms/buildings` | Danh sách building (lấy DISTINCT từ DB) |
| GET | `/api/rooms?building=A1` | Phòng theo building, kèm trạng thái, sắp xếp theo room_number |
| POST | `/api/room-assignments` | Gán phòng `{checkin_id, room_ids: [1,2]}` |
| POST | `/api/room-assignments/{assignment_id}/release` | Trả phòng (set released_at) |
| GET | `/api/room-assignments/checkins` | Checkin chia 2 nhóm (endpoint riêng, không dùng chung /api/checkins) |

### Response mẫu

**GET `/api/rooms/buildings`:**
```json
["A1", "L1", "L2", "L3", "VB"]
```

**GET `/api/rooms?building=A1`:**
```json
[
  {"id": 1, "room_number": "A1.101", "room_type": "JSF", "building": "A1", "status": "available"},
  {"id": 2, "room_number": "A1.102", "room_type": "SUF", "building": "A1", "status": "occupied", "checkin_id": 5, "assignment_id": 12}
]
```

**GET `/api/room-assignments/checkins`:**
```json
{
  "unassigned": [
    {"id": 1, "booking_code": "BK001", "num_guests": 2, "arrival_date": "25/03/2026", "departure_date": "27/03/2026", "contact_name": "Nguyễn Văn A", "status": "confirmed", "created_at": "..."}
  ],
  "assigned": [
    {"id": 2, "booking_code": "BK002", "num_guests": 3, "arrival_date": "25/03/2026", "departure_date": "28/03/2026", "contact_name": "Trần Thị B", "status": "confirmed", "created_at": "...",
     "rooms": [
       {"assignment_id": 1, "room_id": 5, "room_number": "A1.105", "room_type": "DLD", "assigned_at": "..."},
       {"assignment_id": 2, "room_id": 8, "room_number": "A1.108", "room_type": "JSF", "assigned_at": "..."}
     ]}
  ]
}
```

**POST `/api/room-assignments`:**
- Request: `{"checkin_id": 1, "room_ids": [1, 2, 3]}`
- Response 201: `{"assignments": [{"id": 10, "checkin_id": 1, "room_id": 1, "room_number": "A1.101", "assigned_at": "..."}]}`

**POST `/api/room-assignments/{id}/release`:**
- Response 200: `{"id": 10, "released_at": "2026-03-23T14:30:00"}`

### Xử lý lỗi

Tất cả lỗi trả về dạng `{"detail": "Thông báo lỗi"}` (theo chuẩn FastAPI HTTPException).

| Tình huống | HTTP Status | detail |
|------------|-------------|--------|
| Phòng đã được gán cho checkin khác | 409 Conflict | "Phòng {room_number} đã được sử dụng" |
| checkin_id không tồn tại | 404 Not Found | "Không tìm thấy checkin" |
| room_id không tồn tại | 404 Not Found | "Không tìm thấy phòng" |
| assignment_id không tồn tại | 404 Not Found | "Không tìm thấy bản ghi xếp phòng" |
| Trả phòng đã trả rồi | 400 Bad Request | "Phòng đã được trả trước đó" |
| room_ids rỗng | 422 Validation Error | (Pydantic tự xử lý) |

**Xử lý race condition:** Backend kiểm tra phòng trống trong transaction. Nếu 2 người cùng gán 1 phòng, người thứ 2 nhận lỗi 409. Frontend hiện thông báo lỗi và refresh lại danh sách phòng.

## Frontend

### Cấu trúc file
- `frontend/js/app.js` — thêm logic landing, xếp phòng
- `frontend/css/style.css` — thêm styles cho landing, room grid
- `frontend/index.html` — giữ nguyên cấu trúc shell

### Màn hình Landing
- Ẩn bottom nav
- 2 card lớn với icon, tiêu đề và mô tả ngắn:
  - Card "Check-in": icon scan, mô tả "Đăng ký khách mới"
  - Card "Xếp phòng": icon phòng, mô tả "Gán phòng cho khách"

### Màn hình Danh sách checkin (xếp phòng)
- Top bar có nút back (←)
- Section "Chưa xếp phòng" với badge đếm
- Section "Đã xếp phòng" — mỗi phòng có nút "Trả phòng"
- Nhấn vào checkin ở cả 2 nhóm đều mở luồng thêm phòng
- Mỗi item: mã booking, số khách, ngày đến, phòng đã gán (nếu có)
- Loading state: spinner khi tải
- Empty state: thông báo khi chưa có checkin nào

### Màn hình chọn phòng
- Bước 1: Grid chọn building
- Bước 2: Grid phòng, mỗi ô hiện số phòng + loại phòng (room_type)
  - Trắng = trống, xám = đã gán (disabled), cam = đang chọn
  - Chọn nhiều phòng
  - Sắp xếp theo room_number
- Nút "Xác nhận" gán phòng
- Loading state khi tải danh sách phòng

### Xử lý trả phòng
- Trong danh sách "Đã xếp phòng", mỗi phòng có nút trả phòng
- Confirm trước khi trả
- Gọi POST release API, cập nhật lại danh sách

### Xử lý lỗi frontend
- Lỗi 409 (phòng đã gán): hiện toast cảnh báo, refresh lại grid phòng
- Lỗi mạng: hiện toast lỗi với nút thử lại
