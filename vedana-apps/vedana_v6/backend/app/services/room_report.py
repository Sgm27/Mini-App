from sqlalchemy.orm import Session

from app.models.room_report import RoomReport
from app.schemas.room_report import RoomReportCreate


def create_report(db: Session, data: RoomReportCreate) -> RoomReport:
    report = RoomReport(
        room_id=data.room_id,
        note_text=data.note_text,
        voice_url=data.voice_url,
        image_urls=data.image_urls,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, room_id: str | None = None, limit: int = 50) -> list[RoomReport]:
    query = db.query(RoomReport)
    if room_id:
        query = query.filter(RoomReport.room_id == room_id.upper())
    return query.order_by(RoomReport.created_at.desc()).limit(limit).all()
