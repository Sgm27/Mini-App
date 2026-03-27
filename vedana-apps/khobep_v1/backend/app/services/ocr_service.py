"""OCR extraction using OpenAI GPT-5.1 and voice transcript parsing."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from PIL import Image, ImageOps

from app.core.config import settings
from app.schemas.kitchen import ExtractedItem

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-5.1"
TEMP_ROTATED_FOLDER = "/tmp/khobep_rotated_images"

UNITS_VI = [
    "kg", "g", "lít", "lit", "l", "ml", "cái", "hộp", "bao", "bó",
    "quả", "trái", "túi", "lon", "chai", "thùng", "gói", "tờ", "miếng",
]

VOICE_EXTRACT_PROMPT = """Bạn là trợ lý nhận diện cho kho bếp nhà hàng.

Nhiệm vụ: Trích xuất danh sách nguyên vật liệu từ nội dung sau.

Trả về JSON array với format chính xác sau (KHÔNG thêm text khác):
[
  {"name": "Tên nguyên vật liệu", "quantity": 5.0, "unit": "kg"},
  ...
]

Quy tắc:
- name: tên nguyên vật liệu bằng tiếng Việt, viết thường, không có số
- quantity: số lượng (float)
- unit: đơn vị (kg, g, lít, ml, cái, hộp, bao, bó, quả, túi, lon, chai, thùng)
- Nếu không đọc được số lượng, dùng 1.0
- Nếu không đọc được đơn vị, đoán dựa trên loại nguyên liệu (thịt/cá→kg, nước→lít)
- Bỏ qua thông tin không phải nguyên vật liệu (tên cửa hàng, ngày tháng, tổng tiền...)
"""

RECEIPT_EXTRACT_PROMPT = """Bạn là chuyên gia nhận diện phiếu nhập kho cho nhà hàng/resort.
Nếu nhận thấy ảnh bị ngược chữ trả về luôn số 0 (chỉ trả ra số 0).

Nhiệm vụ: Trích xuất TOÀN BỘ thông tin từ phiếu nhập kho / receiving note trong ảnh.

Trả về JSON với format chính xác sau (KHÔNG giải thích):
{
  "header": {
    "receipt_date": "DD/MM/YYYY",
    "description": "Nội dung phiếu nhập",
    "vendor_name": "Tên nhà cung cấp",
    "period": "Kỳ KT (ví dụ: 202602)",
    "voucher_no": "Số phiếu (ví dụ: NK0072)",
    "invoice_serial": "Seri HĐ (ví dụ: 1C26TDK)",
    "invoice_no": "Số HĐ (ví dụ: 39)"
  },
  "items": [
    {
      "item_code": "Mã số hàng",
      "name": "Tên nguyên vật liệu",
      "unit": "Đơn vị tính",
      "quantity": 5.60,
      "unit_price": 604914,
      "amount": 3387520,
      "location": "Mã kho",
      "acc_no": "Mã tài khoản"
    }
  ],
  "summary": {
    "sub_amount": 3387520,
    "discount": 0,
    "vat": 0,
    "total_amount": 3387520
  }
}

Quy tắc:
- Trích xuất CHÍNH XÁC số liệu từ phiếu, không làm tròn
- quantity là số lượng (Số lượng/Qty), unit_price là đơn giá (Đơn giá/Price), amount là thành tiền (Thành tiền/Amount)
- Nếu không tìm thấy trường nào, ghi null
- Nếu có nhiều dòng hàng, trích xuất TẤT CẢ
- Tên nguyên vật liệu phải viết có dấu tiếng Việt nếu trong ảnh có dấu
"""


def _parse_json_response(response_text: str) -> str:
    """Strip markdown code fences from LLM response."""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    return response_text


def _get_openai_client() -> AsyncOpenAI:
    """Get async OpenAI client."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY chưa được cấu hình")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _detect_mime_and_strip(image_base64: str) -> tuple[str, str]:
    """Detect MIME type and strip data URI prefix if present."""
    mime_type = "image/jpeg"
    data = image_base64

    if data.startswith("data:"):
        header, data = data.split(",", 1)
        if "png" in header:
            mime_type = "image/png"
        elif "webp" in header:
            mime_type = "image/webp"
        elif "gif" in header:
            mime_type = "image/gif"

    return mime_type, data


def _rotate_image_base64(image_base64: str, mime_type: str, angle: int) -> str:
    """Rotate a base64 image by the given angle and return new base64."""
    if angle == 0:
        return image_base64

    try:
        import io
        image_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        rotated = img.rotate(-angle, expand=True)

        buffer = io.BytesIO()
        fmt = "PNG" if "png" in mime_type else "JPEG"
        rotated.save(buffer, format=fmt)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error rotating image: {e}")
        return image_base64


async def extract_receipt_from_image(image_base64: str) -> dict:
    """Extract full receiving note (header + items + summary) from image using GPT-5.1.

    Returns dict with keys: header, items, summary.
    Uses self-correction: if LLM detects upside-down text, rotates 180 and retries.
    """
    client = _get_openai_client()
    mime_type, b64_data = _detect_mime_and_strip(image_base64)

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": RECEIPT_EXTRACT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_data}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = response.choices[0].message.content.strip()

        # Self-correction: if text is upside down, rotate 180 and retry
        if response_text == "0":
            b64_data = _rotate_image_base64(b64_data, mime_type, 180)

            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": RECEIPT_EXTRACT_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0,
            )
            response_text = response.choices[0].message.content.strip()

        response_text = _parse_json_response(response_text)
        result = json.loads(response_text)

        return {
            "header": result.get("header", {}),
            "items": result.get("items", []),
            "summary": result.get("summary"),
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raise RuntimeError(f"Không thể parse kết quả OCR: {e}")
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise RuntimeError(f"Lỗi nhận diện ảnh: {e}")


async def extract_from_voice(transcript: str) -> list[ExtractedItem]:
    """Parse voice transcript to extract materials. Uses GPT-5.1 if available, else regex fallback."""
    if settings.openai_api_key:
        try:
            client = _get_openai_client()
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": VOICE_EXTRACT_PROMPT + f"\n\nNội dung ghi âm:\n{transcript}",
                    }
                ],
                temperature=0,
            )
            response_text = response.choices[0].message.content.strip()
            response_text = _parse_json_response(response_text)
            raw_items = json.loads(response_text)
            items = _normalize_items(raw_items)
            if items:
                return items
        except Exception:
            pass  # Fall through to regex

    # Regex fallback
    return _regex_extract(transcript)


def _normalize_items(raw: list[dict]) -> list[ExtractedItem]:
    """Convert raw JSON dicts to ExtractedItem list."""
    result = []
    for item in raw:
        try:
            name = str(item.get("name", "")).strip()
            quantity = float(item.get("quantity", 1.0))
            unit = str(item.get("unit", "kg")).strip().lower()
            if not name:
                continue
            result.append(ExtractedItem(name=name, quantity=quantity, unit=unit))
        except (ValueError, TypeError):
            continue
    return result


def _regex_extract(text: str) -> list[ExtractedItem]:
    """Fallback regex parser for voice input."""
    units_pattern = "|".join(re.escape(u) for u in UNITS_VI)
    pattern = rf'(\d+(?:[.,]\d+)?)\s*({units_pattern})\s+([^\d,;.]+?)(?=\d|,|;|\.|$)'
    results = []
    for match in re.finditer(pattern, text.lower(), re.IGNORECASE):
        qty_str, unit, name = match.groups()
        qty = float(qty_str.replace(",", "."))
        name = name.strip().rstrip(",; ")
        if name:
            results.append(ExtractedItem(name=name, quantity=qty, unit=unit))
    return results
