"""
Gửi thông báo tới nhóm Zalo OA.

Sử dụng Zalo OA API v3.0:
  - GET  /v3.0/oa/group/getgroupsofoa  — lấy danh sách group
  - POST /v3.0/oa/group/message         — gửi tin nhắn vào group
"""

import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

BASE_URL = "https://openapi.zalo.me/v3.0/oa/group"


def _get_groups(access_token: str, offset: int = 0, count: int = 50) -> list[dict]:
    """Lấy danh sách group của OA."""
    params = {"count": count}
    if offset:
        params["offset"] = offset
    url = f"{BASE_URL}/getgroupsofoa?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={"access_token": access_token},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if body.get("error") != 0:
        logger.warning("Zalo get_groups error: %s", body)
        return []

    data = body.get("data") or {}
    groups = data.get("groups") or []
    return groups if isinstance(groups, list) else []


def _send_message(access_token: str, group_id: str, text: str) -> bool:
    """Gửi tin nhắn văn bản tới group."""
    url = f"{BASE_URL}/message"
    payload = {
        "recipient": {"group_id": group_id},
        "message": {"text": text},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "access_token": access_token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if body.get("error") != 0:
        logger.warning("Zalo send_message error: %s", body)
        return False
    return True


def notify_group(access_token: str, group_name: str, text: str) -> bool:
    """
    Tìm group theo tên và gửi tin nhắn.

    Returns:
        True nếu gửi thành công, False nếu không tìm thấy group hoặc gửi lỗi.
    """
    if not access_token:
        logger.warning("Zalo access_token is empty, skip notification")
        return False

    groups = _get_groups(access_token)
    target = group_name.strip().lower()

    group_id = None
    for g in groups:
        if (g.get("name") or "").strip().lower() == target:
            group_id = g.get("group_id")
            break

    if not group_id:
        logger.warning("Zalo group not found: %s", group_name)
        return False

    return _send_message(access_token, str(group_id), text)
