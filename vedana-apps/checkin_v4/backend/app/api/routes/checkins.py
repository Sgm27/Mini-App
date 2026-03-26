import io
import logging
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.api.deps import DBSession
from app.models.checkin import Checkin, Guest
from app.schemas.checkin import (
    CheckinCreate,
    CheckinDetailResponse,
    CheckinResponse,
)
from app.services.zalo_service import notify_checkin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkins")


@router.post("", response_model=CheckinResponse, status_code=201)
def create_checkin(data: CheckinCreate, db: Session = DBSession):
    """Submit a complete check-in record."""
    # Validate dates
    try:
        arrival = datetime.strptime(data.booking.arrival_date, "%d/%m/%Y")
        departure = datetime.strptime(data.booking.departure_date, "%d/%m/%Y")
        if departure < arrival:
            raise HTTPException(
                status_code=400,
                detail="Ngày trả phòng phải sau ngày nhận phòng"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày không hợp lệ. Định dạng: DD/MM/YYYY"
        )

    checkin = Checkin(
        booking_code=data.booking.booking_code.strip(),
        room_type=data.booking.room_type.strip() if data.booking.room_type else None,
        num_guests=data.booking.num_guests,
        arrival_date=data.booking.arrival_date.strip(),
        departure_date=data.booking.departure_date.strip(),
        contact_name=data.contact.name.strip() if data.contact and data.contact.name else None,
        contact_phone=data.contact.phone.strip() if data.contact and data.contact.phone else None,
        status="confirmed",
        created_at=datetime.utcnow(),
    )

    for guest_data in data.guests:
        guest = Guest(
            guest_type=guest_data.guest_type,
            full_name=guest_data.full_name.strip(),
            gender=guest_data.gender.strip() if guest_data.gender else None,
            date_of_birth=guest_data.date_of_birth.strip() if guest_data.date_of_birth else None,
            identification_number=guest_data.identification_number.strip() if guest_data.identification_number else None,
            passport_number=guest_data.passport_number.strip() if guest_data.passport_number else None,
            nationality_code=guest_data.nationality_code.strip() if guest_data.nationality_code else None,
            address=guest_data.address.strip() if guest_data.address else None,
            document_type=guest_data.document_type.strip() if guest_data.document_type else None,
            nationality=guest_data.nationality.strip() if guest_data.nationality else None,
            created_at=datetime.utcnow(),
        )
        checkin.guests.append(guest)

    try:
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving checkin: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu dữ liệu check-in")

    # Send Zalo notification (non-blocking, errors don't affect response)
    try:
        notify_checkin(checkin, checkin.guests)
    except Exception as e:
        logger.error(f"Zalo notification failed: {e}")

    return checkin


@router.get("", response_model=list[CheckinResponse])
def list_checkins(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = DBSession,
):
    """List all check-ins, newest first."""
    checkins = (
        db.query(Checkin)
        .order_by(Checkin.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return checkins


@router.get("/export")
def export_checkins_excel(
    from_date: str = Query(..., description="DD/MM/YYYY"),
    to_date: str = Query(..., description="DD/MM/YYYY"),
    db: Session = DBSession,
):
    """Export all check-ins within a date range as a single Excel file."""
    try:
        dt_from = datetime.strptime(from_date, "%d/%m/%Y")
        dt_to = datetime.strptime(to_date, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày không hợp lệ. Định dạng: DD/MM/YYYY")

    if dt_to < dt_from:
        raise HTTPException(status_code=400, detail="Ngày kết thúc phải sau ngày bắt đầu")

    checkins = (
        db.query(Checkin)
        .filter(Checkin.created_at >= dt_from, Checkin.created_at <= dt_to)
        .order_by(Checkin.created_at.asc())
        .all()
    )

    if not checkins:
        raise HTTPException(status_code=404, detail="Không có check-in nào trong khoảng thời gian này")

    wb = Workbook()
    ws = wb.active
    ws.title = "extracted"
    wb.properties.creator = "Phuong Phan"

    for checkin in checkins:
        for guest in checkin.guests:
            if getattr(guest, 'guest_type', 'vietnamese') in ('vietnamese', None):
                ws.append(_build_guest_row(guest, checkin))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"checkin_{from_date.replace('/', '')}_{to_date.replace('/', '')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export-foreign")
def export_foreign_checkins_xml(
    from_date: str = Query(..., description="DD/MM/YYYY"),
    to_date: str = Query(..., description="DD/MM/YYYY"),
    db: Session = DBSession,
):
    """Export foreign guests within a date range as XML."""
    try:
        dt_from = datetime.strptime(from_date, "%d/%m/%Y")
        dt_to = datetime.strptime(to_date, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày không hợp lệ. Định dạng: DD/MM/YYYY")

    if dt_to < dt_from:
        raise HTTPException(status_code=400, detail="Ngày kết thúc phải sau ngày bắt đầu")

    checkins = (
        db.query(Checkin)
        .filter(Checkin.created_at >= dt_from, Checkin.created_at <= dt_to)
        .order_by(Checkin.created_at.asc())
        .all()
    )

    # Collect foreign guests with room info
    from app.models.room import Room, RoomAssignment
    root = Element("KHAI_BAO_TAM_TRU")
    counter = 0

    for checkin in checkins:
        # Get room number for this checkin
        room_assignment = (
            db.query(RoomAssignment)
            .filter(RoomAssignment.checkin_id == checkin.id, RoomAssignment.released_at.is_(None))
            .order_by(RoomAssignment.assigned_at.asc())
            .first()
        )
        room_number = ""
        if room_assignment:
            room = db.query(Room).filter(Room.id == room_assignment.room_id).first()
            if room:
                room_number = room.room_number or ""

        for guest in checkin.guests:
            if getattr(guest, 'guest_type', 'vietnamese') != 'foreign':
                continue
            counter += 1
            khach = SubElement(root, "THONG_TIN_KHACH")
            SubElement(khach, "so_thu_tu").text = str(counter)
            SubElement(khach, "ho_ten").text = guest.full_name or ""
            SubElement(khach, "ngay_sinh").text = guest.date_of_birth or ""
            SubElement(khach, "ngay_sinh_dung_den").text = "D"
            SubElement(khach, "gioi_tinh").text = guest.gender or ""
            SubElement(khach, "ma_quoc_tich").text = guest.nationality_code or ""
            SubElement(khach, "so_ho_chieu").text = guest.passport_number or ""
            SubElement(khach, "so_phong").text = room_number
            SubElement(khach, "ngay_den").text = checkin.arrival_date or ""
            SubElement(khach, "ngay_di_du_kien").text = checkin.departure_date or ""
            SubElement(khach, "ngay_tra_phong").text = checkin.departure_date or ""

    if counter == 0:
        raise HTTPException(status_code=404, detail="Không có khách nước ngoài trong khoảng thời gian này")

    xml_str = parseString(tostring(root, encoding="unicode")).toprettyxml(indent="  ", encoding=None)
    # Remove extra XML declaration from minidom, add our own
    lines = xml_str.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_output = "\n".join(lines)

    filename = f"foreign_checkin_{from_date.replace('/', '')}_{to_date.replace('/', '')}.xml"
    return StreamingResponse(
        iter([xml_output.encode("utf-8")]),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{checkin_id}", response_model=CheckinDetailResponse)
def get_checkin(checkin_id: int, db: Session = DBSession):
    """Get full check-in detail including guest list."""
    checkin = db.query(Checkin).filter(Checkin.id == checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi check-in")
    return checkin


_ALPHA3_TO_NAME = {
    "GBR": "United Kingdom", "CHN": "China", "DEU": "Germany",
    "KOR": "Korea", "ARG": "Argentina", "FRA": "France",
    "USA": "United States", "JPN": "Japan", "AUS": "Australia",
    "THA": "Thailand", "SGP": "Singapore", "IND": "India",
    "RUS": "Russia", "MYS": "Malaysia", "IDN": "Indonesia",
    "PHL": "Philippines", "MMR": "Myanmar", "TWN": "Taiwan",
    "VNM": "Vietnam", "LAO": "Laos", "KHM": "Cambodia",
    "NZL": "New Zealand", "CAN": "Canada", "ITA": "Italy",
    "ESP": "Spain", "NLD": "Netherlands", "BRA": "Brazil",
}


# --- Gender mapping ---
_GENDER_MAP = {"nam": 2, "nữ": 3, "nu": 3}


def _map_gender_id(gender: str | None) -> int | None:
    if not gender:
        return None
    return _GENDER_MAP.get(gender.strip().lower())


# --- Nationality text → ISO code ---
_NATIONALITY_CODE_MAP = {
    "việt nam": "VN", "viet nam": "VN", "vietnamese": "VN", "vietnam": "VN",
    "lào": "LA", "lao": "LA", "campuchia": "KH", "cambodia": "KH",
    "trung quốc": "CN", "china": "CN", "chinese": "CN",
    "nhật bản": "JP", "japan": "JP", "japanese": "JP",
    "hàn quốc": "KR", "korea": "KR", "korean": "KR",
    "mỹ": "US", "usa": "US", "united states": "US", "american": "US",
    "anh": "GB", "uk": "GB", "united kingdom": "GB", "british": "GB",
    "pháp": "FR", "france": "FR", "french": "FR",
    "đức": "DE", "germany": "DE", "german": "DE",
    "úc": "AU", "australia": "AU", "australian": "AU",
    "thái lan": "TH", "thailand": "TH", "thai": "TH",
    "singapore": "SG", "ấn độ": "IN", "india": "IN",
    "nga": "RU", "russia": "RU", "russian": "RU",
    "malaysia": "MY", "indonesia": "ID", "philippines": "PH",
    "myanmar": "MM", "đài loan": "TW", "taiwan": "TW",
}


def _map_nationality_code(nationality: str | None) -> str:
    if not nationality:
        return "VN"
    code = _NATIONALITY_CODE_MAP.get(nationality.strip().lower())
    if code:
        return code
    # If it's already a 2-letter code, use as-is
    if len(nationality.strip()) == 2 and nationality.strip().isalpha():
        return nationality.strip().upper()
    return "VN"


def _nationality_desc(code: str) -> str:
    _CODE_TO_NAME = {
        "VN": "Viet Nam", "LA": "Lao", "KH": "Cambodia", "CN": "China",
        "JP": "Japan", "KR": "Korea", "US": "United States", "GB": "United Kingdom",
        "FR": "France", "DE": "Germany", "AU": "Australia", "TH": "Thailand",
        "SG": "Singapore", "IN": "India", "RU": "Russia", "MY": "Malaysia",
        "ID": "Indonesia", "PH": "Philippines", "MM": "Myanmar", "TW": "Taiwan",
    }
    return _CODE_TO_NAME.get(code, "")


def _build_guest_row(guest: Guest, checkin: Checkin) -> list:
    """Build a single Excel row for a guest, matching the luutru template."""
    gender_id = _map_gender_id(guest.gender)
    nat_code = _map_nationality_code(guest.nationality)
    nat_desc = _nationality_desc(nat_code)

    # Determine which ID column to use: passport → col F, otherwise → col E
    identifier_number = ""
    passport_no = ""
    doc_type = (guest.document_type or "").lower()
    if doc_type == "passport":
        passport_no = guest.identification_number or ""
    else:
        identifier_number = guest.identification_number or ""

    return [
        guest.full_name or "",                          # A: CITIZENNAME *
        guest.date_of_birth or "",                      # B: DOB *
        gender_id if gender_id else "",                 # C: GENDER_ID *
        "",                                             # D: GENDER_ID_DESC
        identifier_number,                              # E: IDENTIFIER_NUMBER *
        passport_no,                                    # F: PASSPORT_NO *
        "",                                             # G: OTHER_PAPERS * (always empty)
        checkin.contact_phone or "",                    # H: PHONE_NUMBER
        "",                                             # I: OCCUPATION
        "",                                             # J: OCCUPATION_DESC
        "",                                             # K: PLACE_OF_WORK
        "",                                             # L: ETHNIC_ID
        "",                                             # M: ETHNIC_ID_DESC
        nat_code,                                       # N: NATIONALITY *
        nat_desc,                                       # O: NATIONALITY_DESC
        nat_code,                                       # P: COUNTRY *
        nat_desc,                                       # Q: COUNTRY_DESC
        "",                                             # R: RDPROVINCE_ID
        "",                                             # S: RDADDRESS_ID
        guest.address or "",                            # T: RDADDRESS
        guest.address or "",                            # U: FULL_RDADDRESS *
        "0",                                            # V: ADDRESS_TYPE * (0=Thường trú)
        "Thuong tru",                                   # W: ADDRESS_TYPE_DESC
        checkin.arrival_date or "",                     # X: START_DATE *
        checkin.departure_date or "",                   # Y: END_DATE
        "Du lich",                                      # Z: REASON *
    ]
