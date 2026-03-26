import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI
from PIL import Image, ImageOps

from app.core.config import settings

logger = logging.getLogger(__name__)

# ==============================================================================
# CẤU HÌNH NỘI BỘ
# ==============================================================================
MODEL_NAME = "gpt-5.1"
TEMP_ROTATED_FOLDER = "/tmp/agent_rotated_images"
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"]
# ==============================================================================

client = AsyncOpenAI(api_key=settings.openai_api_key)


def encode_image_to_base64(image_path: str) -> str | None:
    """Convert image to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None


def get_mime_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    return f"image/{ext[1:]}"


def _parse_json_response(response_text: str) -> str:
    """Strip markdown code fences from LLM response."""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    return response_text


async def check_image_orientation_async(image_path: str) -> dict:
    """LLM Call #1: Check orientation and detect front/back side."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"loai_mat": "unknown", "rotation_angle": 0, "loai_giay_to": "cccd"}

    mime_type = get_mime_type(image_path)

    prompt = """
Nếu không phải ảnh căn cước hoặc chứng minh thư về luôn:
{
"loai_mat": "mat_truoc"
"rotation_angle": Cần kiểm tra theo nguyên tắc bên dưới
"loai_giay_to": Cần xác định theo nguyên tắc bên dưới
}
Đóng vai trò là chuyên gia nhận định hình ảnh. Hãy phân tích hình ảnh và trả về JSON theo yêu cầu nghiêm ngặt:

NHIỆM VỤ 1: XÁC ĐỊNH MẶT (loai_mat)
- "mat_truoc": Nếu thấy ảnh chân dung, Quốc huy, hoặc họ tên/số định danh.
- "mat_sau": Nếu thấy đặc điểm nhận dạng, mã có dạng IDVNM hoặc hình ảnh con chip.

NHIỆM VỤ 2: XÁC ĐỊNH GÓC CẦN XOAY THEO THUẬN CHIỀU KIM ĐỒNG HỒ THEO NGUYÊN TẮC SAU (rotation_angle)
- Thẻ nằm NGANG. Chiều chữ đã đúng, đã dễ đọc. -> Trả về 0.
- Thẻ nằm NGANG. Chữ bị lộn ngược. -> Trả về 180.

- Thẻ nằm DỌC. Chữ đang quay về bên trái so với chiều đúng. -> Trả về 90.
- Thẻ nằm DỌC. Chữ đang quay về bên phải so với chiều đúng. -> Trả về 270.

NHIỆM VỤ 3: PHÂN LOẠI GIẤY TỜ (loai_giay_to)
- "cccd": Căn cước công dân (thẻ nhựa, có chip, số 12 chữ số, ghi "CĂN CƯỚC CÔNG DÂN" hoặc "CĂN CƯỚC")
- "cmnd": Chứng minh nhân dân (thẻ cũ 9 chữ số, ghi "CHỨNG MINH NHÂN DÂN")
- "passport": Hộ chiếu (ghi "PASSPORT" hoặc "HỘ CHIẾU")
- "birth_certificate": Giấy khai sinh (ghi "GIẤY KHAI SINH")
- "vneid": Ảnh chụp màn hình ứng dụng VNeID

OUTPUT FORMAT (JSON ONLY, NO EXPLANATION):
{
  "loai_mat": "mat_truoc" | "mat_sau",
  "rotation_angle": int,
  "loai_giay_to": "cccd" | "cmnd" | "passport" | "birth_certificate" | "vneid"
"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = _parse_json_response(
            response.choices[0].message.content.strip()
        )
        result = json.loads(response_text)
        return {
            "loai_mat": result.get("loai_mat", "unknown"),
            "rotation_angle": int(result.get("rotation_angle", 0)),
            "loai_giay_to": result.get("loai_giay_to", "cccd"),
        }
    except Exception:
        return {"loai_mat": "unknown", "rotation_angle": 0, "loai_giay_to": "cccd"}


def rotate_image(image_path: str, angle: int, output_folder: str | None = None) -> str:
    """Rotate image with EXIF handling."""
    if angle == 0:
        return image_path

    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        rotated = img.rotate(-angle, expand=True)

        path = Path(image_path)
        target_folder = Path(output_folder) if output_folder else Path(TEMP_ROTATED_FOLDER)
        target_folder.mkdir(parents=True, exist_ok=True)

        rotated_path = target_folder / f"{path.stem}_rotated_{angle}deg{path.suffix}"
        rotated.save(str(rotated_path))
        return str(rotated_path)
    except Exception:
        return image_path


async def extract_mat_truoc_info_async(image_path: str) -> dict:
    """LLM Call #2: Extract front side info."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"status": "error", "error_message": "Image encode failed"}

    mime_type = get_mime_type(image_path)

    prompt = """
    Nếu nhận thấy ảnh bị ngược chữ trả về luôn số 0 (chỉ trả ra số 0).
    Trích xuất thông tin từ MẶT TRƯỚC của ảnh.

Chủ sở hữu ở đây là người có thông tin chính trong ảnh, không phải thông tin của người thân.
Trích xuất các thông tin sau:
- Số định danh cá nhân của chủ sở hữu (Thông tin này luôn có trong ảnh thường là số định danh cá nhân hoặc số hộ chiếu)
- Họ và tên lấy giống hệt theo thông tin trong ảnh (Tên của chủ sở hữu) (lưu ý: chữ TÍNH và TĨNH, hoặc BỐ và BỖ, hoặc những chữ tương tự như vậy)
- Ngày sinh theo tên chủ sở hữu (DD/MM/YYYY)
- Giới tính theo tên chủ sở hữu (Nam/Nữ)
- Nơi ở (lấy từ trường "Nơi thường trú" hoặc "Quê quán") lấy theo chủ sở hữu, nếu là hộ chiếu chỉ cần ghi tên tỉnh (nếu có), và ghi tên nước trên hộ chiếu đó.

Trả về JSON tương tự như ví dụ bên dưới (KHÔNG giải thích):
{
  "so_dinh_danh": "001202009143",
  "ho_ten": "NGUYỄN VĂN TĨNH",
  "ngay_sinh": "01/01/1990",
  "gioi_tinh": "Nam",
  "noi_o": "Xã Hải Minh, Huyện Hải Hậu, Tỉnh Nam Định" (nếu có trong mặt trước)
}

Nếu không tìm thấy thông tin nào, ghi "Không xác định"."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = response.choices[0].message.content.strip()

        # Self-correction: if text is upside down, rotate 180° and retry
        if response_text == "0":
            rotated_path = rotate_image(image_path, 180, TEMP_ROTATED_FOLDER)
            base64_image = encode_image_to_base64(rotated_path)

            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
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
        result["source_image"] = str(Path(image_path).name)
        result["loai_mat"] = "mat_truoc"
        result["status"] = "success"
        return result

    except Exception as e:
        return {
            "so_dinh_danh": "Không xác định",
            "ho_ten": "Không xác định",
            "ngay_sinh": "Không xác định",
            "gioi_tinh": "Không xác định",
            "noi_o": "Không xác định",
            "source_image": str(Path(image_path).name),
            "loai_mat": "mat_truoc",
            "status": "error",
            "error_message": str(e),
        }


async def extract_mat_sau_info_async(image_path: str) -> dict:
    """LLM Call #2: Extract back side info."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"status": "error", "error_message": "Image encode failed"}

    mime_type = get_mime_type(image_path)

    prompt = """
    Nếu nhận thấy ảnh bị ngược chữ trả về luôn số 0 (chỉ trả ra số 0).
    Trích xuất thông tin từ MẶT SAU của ảnh.

Trích xuất các thông tin sau:
- Mã IDVNM (chuỗi bắt đầu bằng IDVNM, copy CHÍNH XÁC toàn bộ)
- "noi_o" phải viết có dấu tiếng Việt (lấy từ trường "Nơi cư trú"))

Trả về JSON tương tự như ví dụ bên dưới (KHÔNG giải thích):
{
  "ma": "IDVNM2020091437001202009143<<80211093M2711092VNM<<<<<<<<<<<8LE<<HOANG<NAM<<<<<<<<<<<<<<<<<",
  "noi_o": "Xã Hải Minh, Huyện Hải Hậu, Tỉnh Nam Định" (nếu có trong mặt sau)
}

Nếu không tìm thấy thông tin, ghi "Không xác định"."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = response.choices[0].message.content.strip()

        # Self-correction: if text is upside down, rotate 180° and retry
        if response_text == "0":
            rotated_path = rotate_image(image_path, 180, TEMP_ROTATED_FOLDER)
            base64_image = encode_image_to_base64(rotated_path)

            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
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
        result["source_image"] = str(Path(image_path).name)
        result["loai_mat"] = "mat_sau"
        result["status"] = "success"
        return result

    except Exception as e:
        return {
            "ma": "Không xác định",
            "noi_o": "Không xác định",
            "source_image": str(Path(image_path).name),
            "loai_mat": "mat_sau",
            "status": "error",
            "error_message": str(e),
        }


def parse_idvnm_code(ma_idvnm: str) -> str:
    """Parse identification number from IDVNM code."""
    if not ma_idvnm or ma_idvnm == "Không xác định":
        return "Không xác định"

    try:
        idx = ma_idvnm.find("<")
        if idx == -1:
            return "Không xác định"

        before_bracket = ma_idvnm[:idx]
        digits = "".join(filter(str.isdigit, before_bracket))

        if len(digits) >= 12:
            return digits[-12:]
        else:
            return "Không xác định"
    except Exception:
        return "Không xác định"


async def process_single_image(image_path: str) -> dict | None:
    """Process a single image: orientation check → rotate → extract.
    Auto-detects document type and routes passport vs VN ID accordingly."""
    orientation_info = await check_image_orientation_async(image_path)
    loai_mat = orientation_info["loai_mat"]
    rotation_angle = orientation_info["rotation_angle"]
    loai_giay_to = orientation_info["loai_giay_to"]

    if loai_mat == "unknown":
        return None

    rotated_image_path = rotate_image(image_path, rotation_angle, TEMP_ROTATED_FOLDER)

    # Route passport to dedicated extraction pipeline
    if loai_giay_to == "passport":
        result = await extract_passport_info_async(rotated_image_path)
        if not result or result.get("status") != "success":
            return None
        result["loai_giay_to"] = "passport"
        return result

    # Vietnamese ID extraction (CCCD, CMND, VNeID, birth certificate)
    if loai_mat == "mat_truoc":
        result = await extract_mat_truoc_info_async(rotated_image_path)
    else:
        result = await extract_mat_sau_info_async(rotated_image_path)

    if not result or result.get("status") != "success":
        return None

    if loai_mat == "mat_sau" and "ma" in result:
        ma_idvnm = result.get("ma", "")
        so_dinh_danh = parse_idvnm_code(ma_idvnm)
        result["so_dinh_danh"] = so_dinh_danh

    result["loai_giay_to"] = loai_giay_to
    return result


def map_missing_info(all_results: list[dict]) -> list[dict]:
    """Map missing 'noi_o' from mat_sau to mat_truoc by identification number."""
    mat_sau_map = {}
    for item in all_results:
        if item.get("loai_mat") != "mat_sau":
            continue
        so_dinh_danh = item.get("so_dinh_danh", "")
        noi_o = item.get("noi_o", "")
        if (
            so_dinh_danh
            and so_dinh_danh != "Không xác định"
            and noi_o
            and noi_o != "Không xác định"
        ):
            mat_sau_map[so_dinh_danh] = noi_o

    for item in all_results:
        if item.get("loai_mat") != "mat_truoc":
            continue
        noi_o = item.get("noi_o", "")
        so_dinh_danh = item.get("so_dinh_danh", "")
        if (not noi_o or noi_o == "Không xác định") and so_dinh_danh in mat_sau_map:
            item["noi_o"] = mat_sau_map[so_dinh_danh]
            item["noi_o_source"] = "mapped_from_mat_sau"

    return all_results


async def extract_booking_info_async(image_path: str) -> dict:
    """Extract booking information from a confirmation image."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"error": "encode_failed", "message": "Không thể đọc ảnh"}

    mime_type = get_mime_type(image_path)

    prompt = """Trích xuất thông tin đặt phòng khách sạn từ ảnh. Ảnh có thể là ảnh chụp màn hình từ app đặt phòng, email xác nhận, hoặc giấy xác nhận.

Trích xuất các thông tin sau:
- booking_code: Mã đặt phòng / Mã xác nhận / Confirmation number
- room_type: Loại phòng
- num_guests: Số người ở (số nguyên)
- arrival_date: Ngày nhận phòng (DD/MM/YYYY)
- departure_date: Ngày trả phòng (DD/MM/YYYY)

Trả về JSON (KHÔNG giải thích):
{
  "booking_code": "ABC123",
  "room_type": "Deluxe King",
  "num_guests": 2,
  "arrival_date": "25/03/2026",
  "departure_date": "28/03/2026"
}

Nếu không tìm thấy thông tin nào, ghi null cho trường đó.
Nếu ảnh không phải xác nhận đặt phòng, trả về: {"error": "not_booking"}"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        response_text = _parse_json_response(
            response.choices[0].message.content.strip()
        )
        result = json.loads(response_text)

        if result.get("error") == "not_booking":
            return {"error": "not_booking", "message": "Ảnh không phải xác nhận đặt phòng"}

        return {
            "booking_code": result.get("booking_code"),
            "room_type": result.get("room_type"),
            "num_guests": result.get("num_guests"),
            "arrival_date": result.get("arrival_date"),
            "departure_date": result.get("departure_date"),
        }
    except Exception as e:
        logger.error(f"Booking OCR error: {e}")
        return {"error": "ocr_error", "message": "Không thể trích xuất thông tin đặt phòng"}


async def batch_extract_info_async(image_paths: list[str]) -> dict:
    """Process multiple document images (CCCD, CMND, passport, etc).
    Auto-detects document type, routes accordingly, and merges profiles."""
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    # Process all images concurrently
    tasks = [process_single_image(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    if not all_results:
        return {"guests": [], "total_profiles": 0}

    # Separate passport results from VN ID results
    # Vietnamese passports (VNM) are treated as Vietnamese guests, not foreign
    vn_results = [
        r for r in all_results
        if r.get("loai_giay_to") != "passport"
        or r.get("ma_quoc_tich", "").upper() == "VNM"
    ]
    passport_results = [
        r for r in all_results
        if r.get("loai_giay_to") == "passport"
        and r.get("ma_quoc_tich", "").upper() != "VNM"
    ]

    guest_list = []

    # --- Process VN results: map front/back, merge by identification_number ---
    if vn_results:
        vn_results = map_missing_info(vn_results)
        vn_profiles: dict[str, dict] = {}

        for result in vn_results:
            is_vn_passport = result.get("loai_giay_to") == "passport"

            # Vietnamese passport uses so_ho_chieu as ID
            if is_vn_passport:
                id_number = result.get("so_ho_chieu", "")
                if not id_number or id_number == "Unknown":
                    id_number = f"temp_{uuid.uuid4().hex[:8]}"
            else:
                id_number = result.get("so_dinh_danh", "")
                if not id_number or id_number == "Không xác định":
                    id_number = f"temp_{uuid.uuid4().hex[:8]}"

            if id_number in vn_profiles:
                existing = vn_profiles[id_number]
                for field, vn_field in [
                    ("full_name", "ho_ten"),
                    ("gender", "gioi_tinh"),
                    ("date_of_birth", "ngay_sinh"),
                    ("address", "noi_o"),
                ]:
                    if not existing.get(field) or existing[field] == "Không xác định":
                        new_val = result.get(vn_field, "")
                        if new_val and new_val != "Không xác định":
                            existing[field] = new_val
            else:
                vn_profiles[id_number] = {
                    "guest_type": "vietnamese",
                    "full_name": result.get("ho_ten", ""),
                    "gender": result.get("gioi_tinh", ""),
                    "date_of_birth": result.get("ngay_sinh", ""),
                    "identification_number": id_number if not id_number.startswith("temp_") else "",
                    "address": result.get("noi_o", "") if not is_vn_passport else None,
                    "document_type": result.get("loai_giay_to", "cccd"),
                    "nationality": None,
                }

        for profile in vn_profiles.values():
            cleaned = {k: (None if v == "Không xác định" else v) for k, v in profile.items()}
            guest_list.append(cleaned)

    # --- Process passport results: merge by passport_number ---
    if passport_results:
        foreign_profiles: dict[str, dict] = {}

        for result in passport_results:
            passport_num = result.get("so_ho_chieu", "")
            if not passport_num or passport_num == "Unknown":
                passport_num = f"temp_{uuid.uuid4().hex[:8]}"

            if passport_num in foreign_profiles:
                existing = foreign_profiles[passport_num]
                for field, vn_field in [
                    ("full_name", "ho_ten"),
                    ("gender", "gioi_tinh"),
                    ("date_of_birth", "ngay_sinh"),
                    ("nationality_code", "ma_quoc_tich"),
                ]:
                    if not existing.get(field) or existing[field] == "Unknown":
                        new_val = result.get(vn_field, "")
                        if new_val and new_val != "Unknown":
                            existing[field] = new_val
            else:
                foreign_profiles[passport_num] = {
                    "guest_type": "foreign",
                    "full_name": result.get("ho_ten", ""),
                    "gender": result.get("gioi_tinh", ""),
                    "date_of_birth": result.get("ngay_sinh", ""),
                    "passport_number": passport_num if not passport_num.startswith("temp_") else "",
                    "nationality_code": result.get("ma_quoc_tich", ""),
                    "document_type": "passport",
                }

        for profile in foreign_profiles.values():
            cleaned = {k: (None if v == "Unknown" else v) for k, v in profile.items()}
            guest_list.append(cleaned)

    return {"guests": guest_list, "total_profiles": len(guest_list)}


def _to_frontend_format(result: dict) -> dict:
    """Map internal Vietnamese fields to frontend expected format with confidence."""
    return {
        "document_type": result.get("loai_giay_to", "cccd"),
        "full_name": {"value": result.get("ho_ten", ""), "confidence": 1.0},
        "gender": {"value": result.get("gioi_tinh", ""), "confidence": 1.0},
        "date_of_birth": {"value": result.get("ngay_sinh", ""), "confidence": 1.0},
        "identification_number": {"value": result.get("so_dinh_danh", ""), "confidence": 1.0},
        "address": {"value": result.get("noi_o", ""), "confidence": 1.0},
    }


async def process_document(file_path: str) -> dict:
    """
    Process a single document image.
    Full pipeline: orientation check → rotate → extract (front/back).
    """
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    result = await process_single_image(file_path)
    if not result:
        return {"error": "ocr_error", "message": "Không trích xuất được thông tin từ ảnh"}

    return _to_frontend_format(result)


async def process_all_images(input_files: list[str]) -> list[dict]:
    """
    Process multiple images concurrently.
    Maps missing info between front and back sides.
    """
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    image_files = [f for f in input_files if Path(f).exists()]
    if not image_files:
        return []

    tasks = [process_single_image(str(f)) for f in image_files]
    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    all_results = map_missing_info(all_results)

    # Return only front-side results
    final_results = [r for r in all_results if r.get("loai_mat") == "mat_truoc"]
    return final_results


async def extract_passport_info_async(image_path: str) -> dict:
    """Extract info from a passport image."""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return {"status": "error", "error_message": "Image encode failed"}

    mime_type = get_mime_type(image_path)

    prompt = """
    Extract information from this PASSPORT image.

Extract the following:
- Full name of the passport holder
- Date of birth (DD/MM/YYYY)
- Gender (Nam or Nữ)
- Nationality code (ISO 3166-1 alpha-3, e.g., GBR, CHN, DEU, KOR, USA, FRA, JPN, AUS)
- Passport number

Return JSON (NO explanation):
{
  "ho_ten": "GARY LEWIS",
  "ngay_sinh": "25/06/1968",
  "gioi_tinh": "Nam",
  "ma_quoc_tich": "GBR",
  "so_ho_chieu": "549588610"
}

If any field cannot be found, write "Unknown"."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
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
        result["source_image"] = str(Path(image_path).name)
        result["status"] = "success"
        return result

    except Exception as e:
        return {
            "ho_ten": "Unknown",
            "ngay_sinh": "Unknown",
            "gioi_tinh": "Unknown",
            "ma_quoc_tich": "Unknown",
            "so_ho_chieu": "Unknown",
            "source_image": str(Path(image_path).name),
            "status": "error",
            "error_message": str(e),
        }


async def process_single_passport(image_path: str) -> dict | None:
    """Process a single passport image: orientation check -> rotate -> extract."""
    orientation_info = await check_image_orientation_async(image_path)
    if orientation_info["loai_mat"] == "unknown":
        return None
    rotation_angle = orientation_info["rotation_angle"]

    rotated_image_path = rotate_image(image_path, rotation_angle, TEMP_ROTATED_FOLDER)
    result = await extract_passport_info_async(rotated_image_path)

    if not result or result.get("status") != "success":
        return None

    result["loai_giay_to"] = "passport"
    return result


async def batch_extract_foreign_info_async(image_paths: list[str]) -> dict:
    """Process multiple passport images and merge profiles by passport number."""
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    tasks = [process_single_passport(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    if not all_results:
        return {"guests": [], "total_profiles": 0}

    profiles: dict[str, dict] = {}

    for result in all_results:
        passport_num = result.get("so_ho_chieu", "")
        if not passport_num or passport_num == "Unknown":
            passport_num = f"temp_{uuid.uuid4().hex[:8]}"

        if passport_num in profiles:
            existing = profiles[passport_num]
            for field, vn_field in [
                ("full_name", "ho_ten"),
                ("gender", "gioi_tinh"),
                ("date_of_birth", "ngay_sinh"),
                ("nationality_code", "ma_quoc_tich"),
            ]:
                if not existing.get(field) or existing[field] == "Unknown":
                    new_val = result.get(vn_field, "")
                    if new_val and new_val != "Unknown":
                        existing[field] = new_val
        else:
            profiles[passport_num] = {
                "guest_type": "foreign",
                "full_name": result.get("ho_ten", ""),
                "gender": result.get("gioi_tinh", ""),
                "date_of_birth": result.get("ngay_sinh", ""),
                "passport_number": passport_num if not passport_num.startswith("temp_") else "",
                "nationality_code": result.get("ma_quoc_tich", ""),
                "document_type": "passport",
            }

    guest_list = []
    for profile in profiles.values():
        cleaned = {}
        for k, v in profile.items():
            cleaned[k] = None if v == "Unknown" else v
        guest_list.append(cleaned)

    return {"guests": guest_list, "total_profiles": len(guest_list)}
