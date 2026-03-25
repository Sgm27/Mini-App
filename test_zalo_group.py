"""
Script gửi test message kèm file đến nhóm Zalo "MAXFLOW - Lễ tân".
"""

import csv
import json
import os
import tempfile
import urllib.parse
import urllib.request

import openpyxl
import requests


def get_groups(access_token: str, offset: int = 0):
    url = "https://openapi.zalo.me/v3.0/oa/group/getgroupsofoa"
    params = {"count": 50}
    if offset != 0:
        params["offset"] = offset
    url = f"{url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={"access_token": access_token},
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if parsed.get("error") == 0:
            return parsed
        print(f"[get_groups] API error: {parsed}")
        return None


def xlsx_to_csv(xlsx_path: str) -> str:
    """Convert file .xlsx sang .csv, trả về đường dẫn file csv tạm."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active
    base_name = os.path.splitext(os.path.basename(xlsx_path))[0]
    csv_path = os.path.join(tempfile.gettempdir(), f"{base_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            writer.writerow(row)
    wb.close()
    print(f"[xlsx_to_csv] Đã convert sang: {csv_path}")
    return csv_path


def upload_file(access_token: str, file_path: str):
    """Upload file lên Zalo OA và trả về token."""
    url = "https://openapi.zalo.me/v2.0/oa/upload/file"
    with open(file_path, "rb") as f:
        resp = requests.post(
            url,
            headers={"access_token": access_token},
            files={"file": (os.path.basename(file_path), f, "application/octet-stream")},
        )
    parsed = resp.json()
    if parsed.get("error") == 0:
        token = (parsed.get("data") or {}).get("token")
        print(f"[upload_file] Upload thành công, token: {token}")
        return token
    print(f"[upload_file] API error: {parsed}")
    return None


def send_message_to_group(access_token: str, group_id: str, text: str):
    url = "https://openapi.zalo.me/v3.0/oa/group/message"
    payload = {
        "recipient": {"group_id": group_id},
        "message": {"text": text},
    }
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
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if parsed.get("error") == 0:
            return parsed
        print(f"[send_message] API error: {parsed}")
        return None


def send_file_to_group(access_token: str, group_id: str, file_token: str):
    url = "https://openapi.zalo.me/v3.0/oa/group/message"
    payload = {
        "recipient": {"group_id": group_id},
        "message": {
            "attachment": {
                "type": "file",
                "payload": {
                    "token": file_token,
                },
            }
        },
    }
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
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if parsed.get("error") == 0:
            return parsed
        print(f"[send_file] API error: {parsed}")
        return None


def main():
    access_token = (
        "X7OV3vSk1Lg2Tn4AaIq5Le5q402KCsman3GHB88DQYtFLoyEk5Ot9j5rIJAaH0XX-"
        "KnkL8v31dJ_GMvmgcyfTkXFTqErOmb2-cOSIkz7NcUvIZD7tN0jLyXhELtNTMzlc"
        "aigMuHiGtJcDZmbW11fSSO35cwkCWrYrZHZJS0-A4QH8N8EZZeM3_1bSb_aP2XpZt"
        "irHTv8IqQm4bHhnm41RR09TKhj2nzbW2u2IV4GNnoTDKiEwZWYEg4xM2piAneudm"
        "TRSFnR8aUiTaDwlbW6JDKSN4Ax8KWHmmu81f0XNLgF7Zv-wauWNe1g8MEMUbmss5"
        "GTOR1sOKd2VdLggrepVyb5JMscVJj9-MH4LRyx0Lxx445qlKWAVFbaOcocQIPU-J0"
        "-JRmVTNosGnzsmsHIGDHIIssVSrPF9saiPPSn0bm"
    )
    name_group = "MAXFLOW - Lễ tân"
    text = "Đây là tin nhắn test từ hệ thống. Vui lòng bỏ qua."
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_import_template_luutru_test.xlsx")

    # 1. Lấy danh sách group
    print("Đang lấy danh sách group...")
    res = get_groups(access_token=access_token)
    if not res:
        print("Không lấy được danh sách group.")
        return

    # 2. Tìm group theo tên
    groups = (res.get("data") or {}).get("groups") or []
    print(f"Tìm thấy {len(groups)} group(s):")
    for i, g in enumerate(groups, 1):
        print(f"  {i}. {g.get('name')} (id: {g.get('group_id')})")

    target = name_group.strip().lower()
    group_id = None
    for g in groups:
        name = (g.get("name") or "").strip().lower()
        if name == target:
            group_id = g.get("group_id")

    if not group_id:
        print(f"Không tìm thấy group: '{name_group}'")
        return

    print(f"Tìm thấy group_id: {group_id}")

    # 3. Gửi tin nhắn text
    print(f"Đang gửi tin nhắn: '{text}'")
    sent = send_message_to_group(access_token=access_token, group_id=str(group_id), text=text)
    if sent:
        print("Gửi tin nhắn thành công!")
    else:
        print("Gửi tin nhắn thất bại.")

    # 4. Convert xlsx -> csv, upload và gửi kèm
    csv_path = xlsx_to_csv(file_path)
    print(f"Đang upload file: {csv_path}")
    file_token = upload_file(access_token=access_token, file_path=csv_path)
    if not file_token:
        print("Upload file thất bại.")
        return

    print("Đang gửi file đến group...")
    sent_file = send_file_to_group(access_token=access_token, group_id=str(group_id), file_token=file_token)
    if sent_file:
        print("Gửi file thành công!")
    else:
        print("Gửi file thất bại.")


if __name__ == "__main__":
    main()
