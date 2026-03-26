from datetime import datetime

from pydantic import BaseModel, Field, model_validator


# --- OCR Booking ---
class BookingOCRResult(BaseModel):
    booking_code: str | None = None
    room_type: str | None = None
    num_guests: int | None = None
    arrival_date: str | None = None
    departure_date: str | None = None


# --- OCR Batch Extract ---
class GuestExtracted(BaseModel):
    guest_type: str = "vietnamese"
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


class CheckinCreate(BaseModel):
    booking: BookingInfo
    contact: ContactInfo | None = None
    guests: list[GuestCreate] = Field(..., min_length=1)


# --- Checkin Response ---
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
