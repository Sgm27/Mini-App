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
