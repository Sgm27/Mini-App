"""OCR and voice transcript extraction using Claude API."""

import base64
import json
import re
from typing import Any

from app.core.config import settings
from app.schemas.kitchen import ExtractedItem

UNITS_VI = [
    "kg", "g", "lít", "lit", "l", "ml", "cái", "hộp", "bao", "bó",
    "quả", "trái", "túi", "lon", "chai", "thùng", "gói", "tờ", "miếng",
]

EXTRACT_PROMPT = """Bạn là trợ lý nhận diện hóa đơn cho kho bếp nhà hàng.

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


def _parse_claude_json(text: str) -> list[dict[str, Any]]:
    """Extract JSON array from Claude response."""
    text = text.strip()
    # Find JSON array in response
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def _normalize_items(raw: list[dict]) -> list[ExtractedItem]:
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


async def extract_from_image(image_base64: str) -> list[ExtractedItem]:
    """Use Claude Vision to extract materials from invoice image."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY chưa được cấu hình")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Detect image type from base64 header or default to jpeg
        media_type = "image/jpeg"
        if image_base64.startswith("data:"):
            header, image_base64 = image_base64.split(",", 1)
            if "png" in header:
                media_type = "image/png"
            elif "webp" in header:
                media_type = "image/webp"
            elif "gif" in header:
                media_type = "image/gif"

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACT_PROMPT + "\n\nHãy phân tích hình ảnh hóa đơn/phiếu giao hàng này và trích xuất danh sách nguyên vật liệu.",
                        },
                    ],
                }
            ],
        )
        raw_text = message.content[0].text
        raw_items = _parse_claude_json(raw_text)
        return _normalize_items(raw_items)

    except Exception as e:
        raise RuntimeError(f"Lỗi nhận diện ảnh: {str(e)}")


async def extract_from_voice(transcript: str) -> list[ExtractedItem]:
    """Parse voice transcript to extract materials. Uses Claude if available, else regex fallback."""
    if settings.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACT_PROMPT + f"\n\nNội dung ghi âm:\n{transcript}",
                    }
                ],
            )
            raw_text = message.content[0].text
            raw_items = _parse_claude_json(raw_text)
            items = _normalize_items(raw_items)
            if items:
                return items
        except Exception:
            pass  # Fall through to regex

    # Regex fallback: parse patterns like "5 kg thịt bò", "3 lít nước mắm"
    return _regex_extract(transcript)


def _regex_extract(text: str) -> list[ExtractedItem]:
    """Fallback regex parser for voice input."""
    units_pattern = "|".join(re.escape(u) for u in UNITS_VI)
    # Pattern: [number] [unit] [name] or [number] [name] [unit]
    pattern = rf'(\d+(?:[.,]\d+)?)\s*({units_pattern})\s+([^\d,;.]+?)(?=\d|,|;|\.|$)'
    results = []
    for match in re.finditer(pattern, text.lower(), re.IGNORECASE):
        qty_str, unit, name = match.groups()
        qty = float(qty_str.replace(",", "."))
        name = name.strip().rstrip(",; ")
        if name:
            results.append(ExtractedItem(name=name, quantity=qty, unit=unit))
    return results
