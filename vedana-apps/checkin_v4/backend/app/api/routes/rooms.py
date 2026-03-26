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
