# Tính năng Xếp phòng — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm tính năng xếp phòng cho app Checkin Vedana — landing screen chọn Check-in / Xếp phòng, luồng xếp phòng với chọn building → chọn phòng, trả phòng thủ công.

**Architecture:** Landing screen thay thế trang chính hiện tại, điều hướng vào 2 luồng riêng biệt. Backend thêm model Room/RoomAssignment, 5 endpoint mới cho rooms và room-assignments. Frontend thêm logic render landing, danh sách checkin phân nhóm, grid chọn building/phòng.

**Tech Stack:** FastAPI + SQLAlchemy (backend), vanilla JS + CSS (frontend), MySQL (database)

**Spec:** `docs/superpowers/specs/2026-03-23-room-assignment-design.md`

---

## File Structure

### Files to create
- `database/004_room_assignments.sql` — Migration tạo bảng room_assignments
- `backend/app/models/room.py` — SQLAlchemy models: Room, RoomAssignment
- `backend/app/schemas/room.py` — Pydantic schemas cho rooms/assignments API
- `backend/app/api/routes/rooms.py` — API endpoints: buildings, rooms by building
- `backend/app/api/routes/room_assignments.py` — API endpoints: gán phòng, trả phòng, grouped checkins

### Files to modify
- `backend/app/api/routes/__init__.py` — Đăng ký router mới
- `frontend/js/api.js` — Thêm API helpers cho rooms/assignments
- `frontend/js/app.js` — Thêm landing screen, luồng xếp phòng
- `frontend/css/style.css` — Thêm styles landing, room grid
- `frontend/index.html` — Không thay đổi cấu trúc, chỉ giữ nguyên

---

## Chunk 1: Database & Backend Models

### Task 1: Migration file room_assignments

**Files:**
- Create: `database/004_room_assignments.sql`

- [ ] **Step 1: Tạo migration file**

```sql
CREATE TABLE IF NOT EXISTS room_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checkin_id INT NOT NULL,
    room_id INT NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME DEFAULT NULL,
    CONSTRAINT fk_ra_checkin FOREIGN KEY (checkin_id) REFERENCES checkins(id) ON DELETE CASCADE,
    CONSTRAINT fk_ra_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO schema_migrations (version) VALUES ('004_room_assignments');
```

- [ ] **Step 2: Chạy migration trên MySQL**

Run: Dùng credentials từ `backend/.env` để chạy migration: `mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < database/004_room_assignments.sql`
Expected: Không có lỗi.

- [ ] **Step 3: Verify bảng đã tạo**

Run: `mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE -e "DESCRIBE room_assignments;"`
Expected: 5 cột (id, checkin_id, room_id, assigned_at, released_at).

- [ ] **Step 4: Commit**

```bash
git add database/004_room_assignments.sql
git commit -m "feat: thêm migration bảng room_assignments"
```

---

### Task 2: SQLAlchemy models Room & RoomAssignment

**Files:**
- Create: `backend/app/models/room.py`

- [ ] **Step 1: Tạo model file**

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_number = Column(String(50), nullable=False, unique=True)
    room_type = Column(String(50), nullable=False)
    building = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assignments = relationship("RoomAssignment", back_populates="room")


class RoomAssignment(Base):
    __tablename__ = "room_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    released_at = Column(DateTime, nullable=True)

    checkin = relationship("Checkin")
    room = relationship("Room", back_populates="assignments")
```

- [ ] **Step 2: Verify import không lỗi**

Run: `cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend && python -c "from app.models.room import Room, RoomAssignment; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/room.py
git commit -m "feat: thêm SQLAlchemy models Room và RoomAssignment"
```

---

### Task 3: Pydantic schemas cho rooms/assignments

**Files:**
- Create: `backend/app/schemas/room.py`

- [ ] **Step 1: Tạo schemas**

```python
from datetime import datetime

from pydantic import BaseModel, Field


# --- Room ---
class RoomResponse(BaseModel):
    id: int
    room_number: str
    room_type: str
    building: str
    status: str  # "available" | "occupied"
    checkin_id: int | None = None
    assignment_id: int | None = None

    model_config = {"from_attributes": True}


# --- Room Assignment ---
class RoomAssignmentCreate(BaseModel):
    checkin_id: int
    room_ids: list[int] = Field(..., min_length=1)


class AssignmentItem(BaseModel):
    id: int
    checkin_id: int
    room_id: int
    room_number: str
    assigned_at: datetime

    model_config = {"from_attributes": True}


class RoomAssignmentResponse(BaseModel):
    assignments: list[AssignmentItem]


class ReleaseResponse(BaseModel):
    id: int
    released_at: datetime


# --- Grouped Checkins ---
class RoomInfo(BaseModel):
    assignment_id: int
    room_id: int
    room_number: str
    room_type: str
    assigned_at: datetime


class CheckinWithRooms(BaseModel):
    id: int
    booking_code: str
    room_type: str | None = None
    num_guests: int
    arrival_date: str
    departure_date: str
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str
    created_at: datetime
    rooms: list[RoomInfo] = []


class GroupedCheckinsResponse(BaseModel):
    unassigned: list[CheckinWithRooms]
    assigned: list[CheckinWithRooms]
```

- [ ] **Step 2: Verify import**

Run: `cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend && python -c "from app.schemas.room import RoomResponse, GroupedCheckinsResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/room.py
git commit -m "feat: thêm Pydantic schemas cho rooms và room assignments"
```

---

## Chunk 2: Backend API Endpoints

### Task 4: Rooms API — buildings & rooms by building

**Files:**
- Create: `backend/app/api/routes/rooms.py`

- [ ] **Step 1: Tạo rooms router**

```python
from fastapi import APIRouter, Query
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.api.deps import DBSession
from app.models.room import Room, RoomAssignment
from app.schemas.room import RoomResponse

router = APIRouter(prefix="/rooms")


@router.get("/buildings", response_model=list[str])
def list_buildings(db: Session = DBSession):
    """Danh sách building (lấy DISTINCT từ DB)."""
    rows = db.query(distinct(Room.building)).order_by(Room.building).all()
    return [r[0] for r in rows]


@router.get("", response_model=list[RoomResponse])
def list_rooms(
    building: str = Query(..., min_length=1),
    db: Session = DBSession,
):
    """Danh sách phòng theo building, kèm trạng thái."""
    rooms = (
        db.query(Room)
        .filter(Room.building == building)
        .order_by(Room.room_number)
        .all()
    )

    # Lấy các assignment đang active (released_at IS NULL) cho building này
    room_ids = [r.id for r in rooms]
    active_assignments = (
        db.query(RoomAssignment)
        .filter(
            RoomAssignment.room_id.in_(room_ids),
            RoomAssignment.released_at.is_(None),
        )
        .all()
    )
    occupied_map = {a.room_id: a for a in active_assignments}

    result = []
    for room in rooms:
        assignment = occupied_map.get(room.id)
        result.append(RoomResponse(
            id=room.id,
            room_number=room.room_number,
            room_type=room.room_type,
            building=room.building,
            status="occupied" if assignment else "available",
            checkin_id=assignment.checkin_id if assignment else None,
            assignment_id=assignment.id if assignment else None,
        ))
    return result
```

- [ ] **Step 2: Verify import**

Run: `cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend && python -c "from app.api.routes.rooms import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/rooms.py
git commit -m "feat: thêm API endpoints danh sách buildings và phòng"
```

---

### Task 5: Room Assignments API — gán phòng, trả phòng, grouped checkins

**Files:**
- Create: `backend/app/api/routes/room_assignments.py`

- [ ] **Step 1: Tạo room_assignments router**

```python
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DBSession
from app.models.checkin import Checkin
from app.models.room import Room, RoomAssignment
from app.schemas.room import (
    AssignmentItem,
    CheckinWithRooms,
    GroupedCheckinsResponse,
    ReleaseResponse,
    RoomAssignmentCreate,
    RoomAssignmentResponse,
    RoomInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/room-assignments")


@router.post("", response_model=RoomAssignmentResponse, status_code=201)
def create_assignments(data: RoomAssignmentCreate, db: Session = DBSession):
    """Gán phòng cho checkin."""
    # Validate checkin exists
    checkin = db.query(Checkin).filter(Checkin.id == data.checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=404, detail="Không tìm thấy checkin")

    assignments = []
    for room_id in data.room_ids:
        # Validate room exists
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy phòng (id={room_id})")

        # Check room not already occupied
        existing = (
            db.query(RoomAssignment)
            .filter(
                RoomAssignment.room_id == room_id,
                RoomAssignment.released_at.is_(None),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Phòng {room.room_number} đã được sử dụng",
            )

        assignment = RoomAssignment(
            checkin_id=data.checkin_id,
            room_id=room_id,
            assigned_at=datetime.utcnow(),
        )
        db.add(assignment)
        assignments.append((assignment, room))

    try:
        db.commit()
        for a, _ in assignments:
            db.refresh(a)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating assignments: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu dữ liệu xếp phòng")

    return RoomAssignmentResponse(
        assignments=[
            AssignmentItem(
                id=a.id,
                checkin_id=a.checkin_id,
                room_id=a.room_id,
                room_number=r.room_number,
                assigned_at=a.assigned_at,
            )
            for a, r in assignments
        ]
    )


@router.post("/{assignment_id}/release", response_model=ReleaseResponse)
def release_assignment(assignment_id: int, db: Session = DBSession):
    """Trả phòng."""
    assignment = db.query(RoomAssignment).filter(RoomAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi xếp phòng")
    if assignment.released_at is not None:
        raise HTTPException(status_code=400, detail="Phòng đã được trả trước đó")

    assignment.released_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(assignment)
    except Exception as e:
        db.rollback()
        logger.error(f"Error releasing assignment: {e}")
        raise HTTPException(status_code=500, detail="Lỗi trả phòng")

    return ReleaseResponse(id=assignment.id, released_at=assignment.released_at)


@router.get("/checkins", response_model=GroupedCheckinsResponse)
def grouped_checkins(db: Session = DBSession):
    """Danh sách checkin chia 2 nhóm: chưa xếp phòng / đã xếp phòng."""
    checkins = db.query(Checkin).order_by(Checkin.created_at.desc()).all()

    # Lấy tất cả active assignments
    active_assignments = (
        db.query(RoomAssignment, Room)
        .join(Room, RoomAssignment.room_id == Room.id)
        .filter(RoomAssignment.released_at.is_(None))
        .all()
    )

    # Group assignments by checkin_id
    assignments_by_checkin: dict[int, list[tuple]] = {}
    for assignment, room in active_assignments:
        assignments_by_checkin.setdefault(assignment.checkin_id, []).append((assignment, room))

    unassigned = []
    assigned = []

    for ci in checkins:
        room_list = assignments_by_checkin.get(ci.id, [])
        rooms = [
            RoomInfo(
                assignment_id=a.id,
                room_id=a.room_id,
                room_number=r.room_number,
                room_type=r.room_type,
                assigned_at=a.assigned_at,
            )
            for a, r in room_list
        ]

        item = CheckinWithRooms(
            id=ci.id,
            booking_code=ci.booking_code,
            room_type=ci.room_type,
            num_guests=ci.num_guests,
            arrival_date=ci.arrival_date,
            departure_date=ci.departure_date,
            contact_name=ci.contact_name,
            contact_phone=ci.contact_phone,
            status=ci.status,
            created_at=ci.created_at,
            rooms=rooms,
        )

        if rooms:
            assigned.append(item)
        else:
            unassigned.append(item)

    return GroupedCheckinsResponse(unassigned=unassigned, assigned=assigned)
```

- [ ] **Step 2: Verify import**

Run: `cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend && python -c "from app.api.routes.room_assignments import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/room_assignments.py
git commit -m "feat: thêm API endpoints gán phòng, trả phòng, grouped checkins"
```

---

### Task 6: Đăng ký routes mới

**Files:**
- Modify: `backend/app/api/routes/__init__.py`

- [ ] **Step 1: Thêm import và đăng ký routers mới**

Sửa file `backend/app/api/routes/__init__.py`:

```python
from fastapi import APIRouter, FastAPI

from app.api.routes import checkins, health, ocr, room_assignments, rooms, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(ocr.router, tags=["ocr"])
    api_router.include_router(checkins.router, tags=["checkins"])
    api_router.include_router(rooms.router, tags=["rooms"])
    api_router.include_router(room_assignments.router, tags=["room-assignments"])
    app.include_router(api_router)
```

- [ ] **Step 2: Khởi động backend để kiểm tra**

Run: `cd /home/sonktx/Mini-app-lambda/workspace/checkin_v4/backend && timeout 5 python -c "from app.main import app; print('Routes:', [r.path for r in app.routes if hasattr(r, 'path')])" 2>&1 || true`
Expected: Thấy các routes mới `/api/rooms/buildings`, `/api/rooms`, `/api/room-assignments`, v.v.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/__init__.py
git commit -m "feat: đăng ký routes rooms và room-assignments"
```

---

## Chunk 3: Frontend — API Helpers & Landing Screen

### Task 7: Thêm API helpers cho rooms/assignments

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Thêm các hàm API mới vào object `api`**

Thêm trước dòng `};` cuối cùng trong object `api` (trước dòng 157 hiện tại):

```javascript
  /**
   * Lấy danh sách buildings
   */
  async getBuildings() {
    return this.get('/api/rooms/buildings');
  },

  /**
   * Lấy danh sách phòng theo building
   */
  async getRoomsByBuilding(building) {
    return this.get('/api/rooms', { building });
  },

  /**
   * Lấy danh sách checkin chia nhóm (xếp phòng)
   */
  async getGroupedCheckins() {
    return this.get('/api/room-assignments/checkins');
  },

  /**
   * Gán phòng cho checkin
   */
  async assignRooms(checkinId, roomIds) {
    return this.post('/api/room-assignments', { checkin_id: checkinId, room_ids: roomIds });
  },

  /**
   * Trả phòng
   */
  async releaseRoom(assignmentId) {
    return this.post(`/api/room-assignments/${assignmentId}/release`);
  },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: thêm API helpers cho rooms và room assignments"
```

---

### Task 8: Landing screen & điều hướng

**Files:**
- Modify: `frontend/js/app.js`

- [ ] **Step 1: Sửa DOMContentLoaded để hiện landing thay vì checkin tab**

Thay thế block `document.addEventListener('DOMContentLoaded', ...)` (dòng 24-28):

```javascript
document.addEventListener('DOMContentLoaded', () => {
    initBottomNav();
    showLanding();
    checkBackend();
});
```

- [ ] **Step 2: Thêm biến và hàm điều hướng**

Thêm sau biến `currentTab` (sau dòng 6):

```javascript
let currentMode = 'landing'; // 'landing' | 'checkin' | 'room-assignment'
```

- [ ] **Step 3: Thêm hàm showLanding()**

Thêm sau hàm `onTabChange()` (sau dòng 60):

```javascript
/* ============================================
   LANDING SCREEN
   ============================================ */
function showLanding() {
    currentMode = 'landing';
    document.querySelector('.bottom-nav').style.display = 'none';
    document.getElementById('topBarLeft').innerHTML = '';
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="landing fade-in">
            <div class="landing__header">
                <div class="landing__title">Xin chào!</div>
                <div class="landing__subtitle">Chọn thao tác bạn muốn thực hiện</div>
            </div>
            <div class="landing__cards">
                <button class="landing-card" id="btnLandingCheckin">
                    <div class="landing-card__icon landing-card__icon--orange">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </div>
                    <div class="landing-card__text">
                        <div class="landing-card__title">Check-in</div>
                        <div class="landing-card__desc">Đăng ký khách mới</div>
                    </div>
                    <div class="landing-card__arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </button>
                <button class="landing-card" id="btnLandingRoomAssign">
                    <div class="landing-card__icon landing-card__icon--blue">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                            <polyline points="9 22 9 12 15 12 15 22"/>
                        </svg>
                    </div>
                    <div class="landing-card__text">
                        <div class="landing-card__title">Xếp phòng</div>
                        <div class="landing-card__desc">Gán phòng cho khách</div>
                    </div>
                    <div class="landing-card__arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnLandingCheckin').addEventListener('click', enterCheckinMode);
    document.getElementById('btnLandingRoomAssign').addEventListener('click', enterRoomAssignMode);
}

function showBackButton(onBack) {
    document.getElementById('topBarLeft').innerHTML = `
        <button class="top-bar__action" id="btnTopBarBack">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
    `;
    document.getElementById('btnTopBarBack').addEventListener('click', onBack);
}

function enterCheckinMode() {
    currentMode = 'checkin';
    document.querySelector('.bottom-nav').style.display = 'flex';
    showBackButton(showLanding);
    loadCheckinTab();
}

function enterRoomAssignMode() {
    currentMode = 'room-assignment';
    document.querySelector('.bottom-nav').style.display = 'none';
    showBackButton(showLanding);
    loadRoomAssignmentList();
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: thêm landing screen và điều hướng Check-in / Xếp phòng"
```

---

### Task 9: CSS cho landing screen

**Files:**
- Modify: `frontend/css/style.css`

- [ ] **Step 1: Thêm styles landing vào cuối file CSS**

```css
/* ============================================
   LANDING SCREEN
   ============================================ */
.landing {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 60vh;
    padding: var(--space-xl) 0;
}

.landing__header {
    text-align: center;
    margin-bottom: var(--space-3xl);
}

.landing__title {
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 800;
    color: var(--color-text);
    letter-spacing: -0.02em;
    margin-bottom: var(--space-xs);
}

.landing__subtitle {
    font-size: 14px;
    color: var(--color-text-muted);
}

.landing__cards {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
}

.landing-card {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-xl);
    cursor: pointer;
    transition: all var(--transition-fast);
    -webkit-tap-highlight-color: transparent;
    text-align: left;
    width: 100%;
    font-family: var(--font-body);
}

.landing-card:active {
    transform: scale(0.98);
    border-color: var(--color-primary);
    box-shadow: var(--shadow-md);
}

.landing-card__icon {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.landing-card__icon--orange {
    background: var(--color-primary-bg);
    color: var(--color-primary);
}

.landing-card__icon--blue {
    background: var(--color-info-bg);
    color: var(--color-info);
}

.landing-card__text {
    flex: 1;
}

.landing-card__title {
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 700;
    color: var(--color-text);
    margin-bottom: 2px;
}

.landing-card__desc {
    font-size: 13px;
    color: var(--color-text-muted);
}

.landing-card__arrow {
    color: var(--color-text-muted);
    flex-shrink: 0;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: thêm CSS cho landing screen"
```

---

## Chunk 4: Frontend — Xếp phòng Flow

### Task 10: Màn hình danh sách checkin phân nhóm

**Files:**
- Modify: `frontend/js/app.js`

- [ ] **Step 1: Thêm hàm loadRoomAssignmentList()**

Thêm vào cuối file app.js, trước các hàm utility (showToast, escapeHtml):

```javascript
/* ============================================
   ROOM ASSIGNMENT — Danh sách checkin
   ============================================ */
async function loadRoomAssignmentList() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header">
            <div>
                <div class="section-header__title">Xếp phòng</div>
                <div class="section-header__subtitle">Chọn checkin để gán phòng</div>
            </div>
        </div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const data = await api.getGroupedCheckins();

        if (data.unassigned.length === 0 && data.assigned.length === 0) {
            content.innerHTML = `
                <div class="section-header"><div><div class="section-header__title">Xếp phòng</div></div></div>
                <div class="empty-state">
                    <div class="empty-state__icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    </div>
                    <div class="empty-state__title">Chưa có checkin</div>
                    <div class="empty-state__text">Hãy thực hiện check-in trước để xếp phòng.</div>
                </div>
            `;
            return;
        }

        let html = `
            <div class="section-header"><div>
                <div class="section-header__title">Xếp phòng</div>
                <div class="section-header__subtitle">Chọn checkin để gán phòng</div>
            </div></div>
        `;

        // Nhóm chưa xếp phòng
        if (data.unassigned.length > 0) {
            html += `<div class="ra-section__title">Chưa xếp phòng <span class="ra-badge">${data.unassigned.length}</span></div>`;
            html += data.unassigned.map((ci, i) => renderCheckinItem(ci, i)).join('');
        }

        // Nhóm đã xếp phòng
        if (data.assigned.length > 0) {
            html += `<div class="ra-section__title" style="margin-top:var(--space-xl);">Đã xếp phòng</div>`;
            html += data.assigned.map((ci, i) => renderAssignedCheckinItem(ci, i)).join('');
        }

        content.innerHTML = `<div class="fade-in">${html}</div>`;

    } catch (error) {
        content.innerHTML = `
            <div class="section-header"><div><div class="section-header__title">Xếp phòng</div></div></div>
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadRoomAssignmentList()">Thử lại</button></div>
            </div>
        `;
    }
}

function renderCheckinItem(ci, index) {
    return `
        <div class="history-item fade-in stagger-${Math.min(index + 1, 5)}" onclick="startRoomSelection(${ci.id}, '${escapeHtml(ci.booking_code)}')">
            <div class="history-item__avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
            <div class="history-item__body">
                <div class="history-item__name">${escapeHtml(ci.booking_code)}${ci.contact_name ? ' — ' + escapeHtml(ci.contact_name) : ''}</div>
                <div class="history-item__meta">
                    <span>${ci.num_guests} khách</span>
                    <span>•</span>
                    <span>${escapeHtml(ci.arrival_date)}</span>
                </div>
            </div>
            <div class="history-item__arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
        </div>
    `;
}

function renderAssignedCheckinItem(ci, index) {
    const roomTags = ci.rooms.map(r => `
        <span class="ra-room-tag">
            ${escapeHtml(r.room_number)}
            <button class="ra-room-tag__remove" onclick="event.stopPropagation(); handleReleaseRoom(${r.assignment_id}, '${escapeHtml(r.room_number)}')" title="Trả phòng">&#10005;</button>
        </span>
    `).join('');

    return `
        <div class="history-item fade-in stagger-${Math.min(index + 1, 5)}" onclick="startRoomSelection(${ci.id}, '${escapeHtml(ci.booking_code)}')">
            <div class="history-item__avatar" style="background:var(--color-success-bg);color:var(--color-success);">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div class="history-item__body">
                <div class="history-item__name">${escapeHtml(ci.booking_code)}${ci.contact_name ? ' — ' + escapeHtml(ci.contact_name) : ''}</div>
                <div class="history-item__meta">
                    <span>${ci.num_guests} khách</span>
                    <span>•</span>
                    <span>${escapeHtml(ci.arrival_date)}</span>
                </div>
                <div class="ra-room-tags">${roomTags}</div>
            </div>
            <div class="history-item__arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
        </div>
    `;
}

async function handleReleaseRoom(assignmentId, roomNumber) {
    if (!confirm(`Bạn có chắc muốn trả phòng ${roomNumber}?`)) return;
    try {
        await api.releaseRoom(assignmentId);
        showToast(`Đã trả phòng ${roomNumber}`, 'success');
        loadRoomAssignmentList();
    } catch (error) {
        showToast(error.message || 'Lỗi khi trả phòng', 'error');
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: thêm màn hình danh sách checkin phân nhóm cho xếp phòng"
```

---

### Task 11: Màn hình chọn building & chọn phòng

**Files:**
- Modify: `frontend/js/app.js`

- [ ] **Step 1: Thêm hàm chọn building**

Thêm tiếp sau các hàm ở Task 10:

```javascript
/* ============================================
   ROOM ASSIGNMENT — Chọn Building & Phòng
   ============================================ */
let selectedRooms = [];
let currentCheckinId = null;
let currentBookingCode = '';
let cachedRooms = [];

function startRoomSelection(checkinId, bookingCode) {
    currentCheckinId = checkinId;
    currentBookingCode = bookingCode;
    selectedRooms = [];
    showBackButton(() => {
        showBackButton(showLanding);
        loadRoomAssignmentList();
    });
    loadBuildingSelection();
}

async function loadBuildingSelection() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header"><div>
            <div class="section-header__title">Chọn tòa nhà</div>
            <div class="section-header__subtitle">Booking: ${escapeHtml(currentBookingCode)}</div>
        </div></div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const buildings = await api.getBuildings();
        const gridHtml = buildings.map(b => `
            <button class="building-card" onclick="loadRoomGrid('${escapeHtml(b)}')">
                <div class="building-card__icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                </div>
                <div class="building-card__name">${escapeHtml(b)}</div>
            </button>
        `).join('');

        content.innerHTML = `
            <div class="fade-in">
                <div class="section-header"><div>
                    <div class="section-header__title">Chọn tòa nhà</div>
                    <div class="section-header__subtitle">Booking: ${escapeHtml(currentBookingCode)}</div>
                </div></div>
                <div class="building-grid">${gridHtml}</div>
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadBuildingSelection()">Thử lại</button></div>
            </div>
        `;
    }
}

async function loadRoomGrid(building) {
    selectedRooms = [];
    const content = document.getElementById('content');

    showBackButton(() => {
        showBackButton(() => {
            showBackButton(showLanding);
            loadRoomAssignmentList();
        });
        loadBuildingSelection();
    });

    content.innerHTML = `
        <div class="section-header"><div>
            <div class="section-header__title">Tòa ${escapeHtml(building)}</div>
            <div class="section-header__subtitle">Chọn phòng cho ${escapeHtml(currentBookingCode)}</div>
        </div></div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        cachedRooms = await api.getRoomsByBuilding(building);
        renderRoomGrid(building, cachedRooms);
    } catch (error) {
        content.innerHTML = `
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadRoomGrid('${escapeHtml(building)}')">Thử lại</button></div>
            </div>
        `;
    }
}

function renderRoomGrid(building, rooms) {
    const content = document.getElementById('content');
    const gridHtml = rooms.map(r => {
        const isOccupied = r.status === 'occupied';
        const isSelected = selectedRooms.includes(r.id);
        let cls = 'room-cell';
        if (isOccupied) cls += ' room-cell--occupied';
        else if (isSelected) cls += ' room-cell--selected';

        return `
            <button class="${cls}" ${isOccupied ? 'disabled' : ''} onclick="toggleRoom(${r.id}, '${escapeHtml(building)}')">
                <div class="room-cell__number">${escapeHtml(r.room_number)}</div>
                <div class="room-cell__type">${escapeHtml(r.room_type)}</div>
            </button>
        `;
    }).join('');

    const selectedCount = selectedRooms.length;

    content.innerHTML = `
        <div class="fade-in">
            <div class="section-header"><div>
                <div class="section-header__title">Tòa ${escapeHtml(building)}</div>
                <div class="section-header__subtitle">Chọn phòng cho ${escapeHtml(currentBookingCode)}</div>
            </div></div>
            <div class="room-grid-legend">
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--available"></span>Trống</span>
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--occupied"></span>Đã gán</span>
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--selected"></span>Đang chọn</span>
            </div>
            <div class="room-grid">${gridHtml}</div>
            <div class="wizard-nav" style="margin-top:var(--space-xl);">
                <button class="btn btn--secondary flex-1" onclick="loadBuildingSelection()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                    Đổi tòa
                </button>
                <button class="btn btn--primary flex-1 btn--lg" id="btnConfirmRooms" ${selectedCount === 0 ? 'disabled' : ''}>
                    Xác nhận (${selectedCount})
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnConfirmRooms').addEventListener('click', () => confirmRoomAssignment(building));
}

function toggleRoom(roomId, building) {
    const idx = selectedRooms.indexOf(roomId);
    if (idx >= 0) {
        selectedRooms.splice(idx, 1);
    } else {
        selectedRooms.push(roomId);
    }
    // Re-render từ cached data (không gọi API)
    renderRoomGrid(building, cachedRooms);
}

async function confirmRoomAssignment(building) {
    if (selectedRooms.length === 0) return;

    const btn = document.getElementById('btnConfirmRooms');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Đang xử lý...';

    try {
        await api.assignRooms(currentCheckinId, selectedRooms);
        showToast('Xếp phòng thành công!', 'success');
        selectedRooms = [];
        showBackButton(showLanding);
        loadRoomAssignmentList();
    } catch (error) {
        showToast(error.message || 'Lỗi khi xếp phòng', 'error');
        // Refresh room grid
        loadRoomGrid(building);
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: thêm màn hình chọn building và grid chọn phòng"
```

---

### Task 12: CSS cho room assignment

**Files:**
- Modify: `frontend/css/style.css`

- [ ] **Step 1: Thêm styles room assignment vào cuối file CSS**

```css
/* ============================================
   ROOM ASSIGNMENT
   ============================================ */
.ra-section__title {
    font-family: var(--font-display);
    font-size: 13px;
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: var(--space-md);
    margin-top: var(--space-lg);
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.ra-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: var(--radius-full);
    background: var(--color-primary);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    font-family: var(--font-body);
}

.ra-room-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: var(--space-xs);
}

.ra-room-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: var(--radius-full);
    background: var(--color-success-bg);
    color: var(--color-success);
    font-size: 11px;
    font-weight: 600;
}

.ra-room-tag__remove {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: var(--radius-full);
    background: transparent;
    color: var(--color-error);
    border: none;
    cursor: pointer;
    font-size: 10px;
    padding: 0;
    transition: all var(--transition-fast);
}

.ra-room-tag__remove:active {
    background: var(--color-error);
    color: #fff;
}

/* Building Grid */
.building-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-md);
}

.building-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-xl);
    cursor: pointer;
    transition: all var(--transition-fast);
    -webkit-tap-highlight-color: transparent;
    font-family: var(--font-body);
}

.building-card:active {
    transform: scale(0.96);
    border-color: var(--color-primary);
    box-shadow: var(--shadow-orange);
}

.building-card__icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-lg);
    background: var(--color-info-bg);
    color: var(--color-info);
    display: flex;
    align-items: center;
    justify-content: center;
}

.building-card__name {
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 700;
    color: var(--color-text);
}

/* Room Grid */
.room-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-sm);
}

.room-grid-legend {
    display: flex;
    justify-content: center;
    gap: var(--space-lg);
    margin-bottom: var(--space-lg);
    font-size: 12px;
    color: var(--color-text-muted);
}

.room-legend__item {
    display: flex;
    align-items: center;
    gap: 4px;
}

.room-legend__dot {
    width: 10px;
    height: 10px;
    border-radius: var(--radius-full);
}

.room-legend__dot--available {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
}

.room-legend__dot--occupied {
    background: var(--color-divider);
}

.room-legend__dot--selected {
    background: var(--color-primary);
}

.room-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: var(--space-md) var(--space-sm);
    background: var(--color-surface);
    border: 1.5px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    -webkit-tap-highlight-color: transparent;
    font-family: var(--font-body);
    min-height: 56px;
}

.room-cell:active:not(:disabled) {
    transform: scale(0.95);
}

.room-cell--occupied {
    background: var(--color-divider);
    border-color: var(--color-divider);
    opacity: 0.5;
    cursor: not-allowed;
}

.room-cell--selected {
    background: var(--color-primary-bg);
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(242,107,33,0.15);
}

.room-cell__number {
    font-size: 13px;
    font-weight: 700;
    color: var(--color-text);
}

.room-cell--occupied .room-cell__number {
    color: var(--color-text-muted);
}

.room-cell--selected .room-cell__number {
    color: var(--color-primary);
}

.room-cell__type {
    font-size: 10px;
    font-weight: 600;
    color: var(--color-text-muted);
}

.room-cell--selected .room-cell__type {
    color: var(--color-primary);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: thêm CSS cho room assignment, building grid, room grid"
```

---

## Chunk 5: Kiểm tra tổng thể

### Task 13: Kiểm tra end-to-end

- [ ] **Step 1: Chạy migration**

Run: Dùng credentials từ `backend/.env`: `mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < database/004_room_assignments.sql`

- [ ] **Step 2: Khởi động backend và kiểm tra API**

Run backend, sau đó test:
- `curl http://localhost:2701/api/rooms/buildings` → danh sách building
- `curl "http://localhost:2701/api/rooms?building=A1"` → danh sách phòng A1
- `curl http://localhost:2701/api/room-assignments/checkins` → grouped checkins

- [ ] **Step 3: Kiểm tra frontend**

Mở browser, kiểm tra:
1. Landing screen hiện 2 card
2. Nhấn "Check-in" → wizard 3 bước, nút back quay về landing
3. Nhấn "Xếp phòng" → danh sách checkin phân nhóm
4. Nhấn checkin → chọn building → chọn phòng → xác nhận
5. Phòng đã gán hiện xám, trả phòng hoạt động

- [ ] **Step 4: Commit tất cả (nếu có thay đổi sửa lỗi)**

```bash
git add -A
git commit -m "fix: sửa lỗi phát hiện trong kiểm tra end-to-end"
```
