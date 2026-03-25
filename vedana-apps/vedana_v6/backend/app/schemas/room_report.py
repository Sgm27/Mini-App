from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class RoomReportCreate(BaseModel):
    room_id: str
    note_text: Optional[str] = None
    voice_url: Optional[str] = None
    image_urls: list[str]

    @field_validator("room_id")
    @classmethod
    def room_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("room_id is required")
        return v.strip().upper()

    @field_validator("image_urls")
    @classmethod
    def images_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one image is required")
        return v


class RoomReportResponse(BaseModel):
    id: int
    room_id: str
    note_text: Optional[str]
    voice_url: Optional[str]
    image_urls: list[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
