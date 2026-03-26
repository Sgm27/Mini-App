import json
import logging
import urllib.parse
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)

DOC_TYPE_LABELS = {
    "cccd": "CCCD",
    "cmnd": "CMND",
    "passport": "Hộ chiếu",
    "birth_certificate": "Giấy khai sinh",
    "vneid": "VNeID",
}

ALPHA3_TO_NAME = {
    "GBR": "United Kingdom", "CHN": "China", "DEU": "Germany",
    "KOR": "Korea", "ARG": "Argentina", "FRA": "France",
    "USA": "United States", "JPN": "Japan", "AUS": "Australia",
    "THA": "Thailand", "SGP": "Singapore", "IND": "India",
    "RUS": "Russia", "MYS": "Malaysia", "IDN": "Indonesia",
}


def _api_get(url: str, access_token: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={"access_token": access_token},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        parsed = json.loads(resp.read().decode("utf-8"))
        if parsed.get("error") == 0:
            return parsed
        logger.warning(f"Zalo API error: {parsed}")
        return None


def _api_post(url: str, access_token: str, payload: dict) -> dict | None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "access_token": access_token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        parsed = json.loads(resp.read().decode("utf-8"))
        if parsed.get("error") == 0:
            return parsed
        logger.warning(f"Zalo API error: {parsed}")
        return None


def _find_group_id(access_token: str, group_name: str) -> str | None:
    url = "https://openapi.zalo.me/v3.0/oa/group/getgroupsofoa"
    params = {"count": 50}
    url = f"{url}?{urllib.parse.urlencode(params)}"

    res = _api_get(url, access_token)
    if not res:
        return None

    target = group_name.strip().lower()
    for g in (res.get("data") or {}).get("groups") or []:
        if (g.get("name") or "").strip().lower() == target:
            return str(g.get("group_id"))
    return None


def _send_message(access_token: str, group_id: str, text: str) -> bool:
    url = "https://openapi.zalo.me/v3.0/oa/group/message"
    payload = {
        "recipient": {"group_id": group_id},
        "message": {"text": text},
    }
    res = _api_post(url, access_token, payload)
    return res is not None


def _build_checkin_message(checkin, guests: list) -> str:
    lines = [
        "📋 CHECK-IN MỚI",
        f"Mã booking: {checkin.booking_code}",
    ]
    if checkin.room_type:
        lines.append(f"Loại phòng: {checkin.room_type}")
    lines.append(f"Ngày: {checkin.arrival_date} → {checkin.departure_date}")
    lines.append(f"Số khách: {checkin.num_guests}")
    if checkin.contact_name:
        lines.append(f"Liên hệ: {checkin.contact_name}")
    if checkin.contact_phone:
        lines.append(f"SĐT: {checkin.contact_phone}")

    if guests:
        lines.append("")
        lines.append(f"👥 Danh sách khách ({len(guests)}):")
        for i, g in enumerate(guests, 1):
            guest_type = getattr(g, 'guest_type', 'vietnamese') or 'vietnamese'
            if guest_type == 'foreign':
                nat_code = getattr(g, 'nationality_code', '') or ''
                nat_name = ALPHA3_TO_NAME.get(nat_code, nat_code)
                passport = getattr(g, 'passport_number', '') or ''
                parts = [f"[NN] {g.full_name}"]
                if passport:
                    parts.append(passport)
                if nat_code:
                    parts.append(f"({nat_name})")
                lines.append(f"  {i}. {' - '.join(parts)}")
            else:
                doc_label = DOC_TYPE_LABELS.get(g.document_type, g.document_type or "")
                parts = [f"[VN] {g.full_name}"]
                if g.identification_number:
                    parts.append(g.identification_number)
                if doc_label:
                    parts.append(f"({doc_label})")
                lines.append(f"  {i}. {' - '.join(parts)}")

    return "\n".join(lines)


def notify_checkin(checkin, guests: list) -> None:
    access_token = settings.zalo_access_token
    group_name = settings.zalo_group_name

    if not access_token:
        logger.info("Zalo access token not configured, skipping notification")
        return

    try:
        group_id = _find_group_id(access_token, group_name)
        if not group_id:
            logger.warning(f"Zalo group '{group_name}' not found")
            return

        message = _build_checkin_message(checkin, guests)
        if _send_message(access_token, group_id, message):
            logger.info(f"Zalo notification sent for checkin {checkin.id}")
        else:
            logger.warning(f"Failed to send Zalo notification for checkin {checkin.id}")
    except Exception as e:
        logger.error(f"Zalo notification error: {e}")
