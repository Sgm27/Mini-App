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
