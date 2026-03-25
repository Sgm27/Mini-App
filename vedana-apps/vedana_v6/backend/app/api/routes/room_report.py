import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from app.api.deps import DBSession
from app.core.config import settings
from app.schemas.room_report import RoomReportCreate, RoomReportResponse
from app.services import room_report as report_service
from app.services.zalo_notify import notify_group

logger = logging.getLogger(__name__)

router = APIRouter()

VN_TZ = timezone(timedelta(hours=7))


def _send_zalo_notification(report) -> None:
    """Gửi thông báo Zalo sau khi dọn phòng xong (fire-and-forget)."""
    try:
        now = datetime.now(VN_TZ).strftime("%H:%M %d/%m/%Y")
        lines = [
            f"🏨 Phòng {report.room_id} đã dọn xong",
            f"🕐 {now}",
            f"📸 {len(report.image_urls)} ảnh đính kèm",
        ]
        if report.note_text:
            lines.append(f"📝 {report.note_text}")

        text = "\n".join(lines)
        notify_group(
            access_token=settings.zalo_oa_access_token,
            group_name=settings.zalo_notify_group,
            text=text,
        )
    except Exception:
        logger.exception("Failed to send Zalo notification")


@router.post("/reports", response_model=RoomReportResponse, status_code=201)
def create_room_report(data: RoomReportCreate, db=DBSession):
    if not data.image_urls:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 ảnh")
    report = report_service.create_report(db, data)
    _send_zalo_notification(report)
    return report


@router.get("/reports", response_model=list[RoomReportResponse])
def list_room_reports(room_id: str | None = None, db=DBSession):
    return report_service.list_reports(db, room_id=room_id)
