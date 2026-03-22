import json
import base64
import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from PIL import Image, ImageOps
from openai import AsyncOpenAI

# ==============================================================================
# CẤU HÌNH NỘI BỘ
# ==============================================================================
MODEL_NAME = "gpt-5.1"
TEMP_ROTATED_FOLDER = "/tmp/agent_rotated_images"
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"]
DEFAULT_INPUT_DIR = "./"
# ==============================================================================

# Initialize AsyncOpenAI client
client = AsyncOpenAI()

def encode_image_to_base64(image_path):
    """Convert image to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

async def check_image_orientation_async(image_path):
    """LLM Call #1: Check orientation (async)"""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image: return {"loai_mat": "unknown", "rotation_angle": 0}

    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"

    prompt = """
Nếu không phải ảnh căn cước hoặc chứng minh thư về luôn:
{
"loai_mat": "mat_truoc"
"rotation_angle": Cần kiểm tra theo nguyên tắc bên dưới
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
OUTPUT FORMAT (JSON ONLY, NO EXPLANATION):
{
  "loai_mat": "mat_truoc" | "mat_sau",
  "rotation_angle": int
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
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0
        )

        response_text = response.choices[0].message.content.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)
        return {
            "loai_mat": result.get("loai_mat", "unknown"),
            "rotation_angle": int(result.get("rotation_angle", 0))
        }
    except Exception:
        return {"loai_mat": "unknown", "rotation_angle": 0}

def rotate_image(image_path, angle, output_folder=None):
    """Rotate image with EXIF handling"""
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

async def extract_mat_truoc_info_async(image_path):
    """LLM Call #2: Extract front side info (async)"""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image: return {"status": "error", "error_message": "Image encode failed"}

    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"

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
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0
        )

        response_text = response.choices[0].message.content.strip()

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
                                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                temperature=0
            )
            response_text = response.choices[0].message.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

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
            "error_message": str(e)
        }

async def extract_mat_sau_info_async(image_path):
    """LLM Call #2: Extract back side info (async)"""
    base64_image = encode_image_to_base64(image_path)
    if not base64_image: return {"status": "error", "error_message": "Image encode failed"}

    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"

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
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0
        )

        response_text = response.choices[0].message.content.strip()

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
                                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                temperature=0
            )
            response_text = response.choices[0].message.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

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
            "error_message": str(e)
        }

def parse_idvnm_code(ma_idvnm):
    """Parse CCCD number from IDVNM code"""
    if not ma_idvnm or ma_idvnm == "Không xác định":
        return "Không xác định"

    try:
        idx = ma_idvnm.find("<")
        if idx == -1:
            return "Không xác định"

        before_bracket = ma_idvnm[:idx]
        digits = ''.join(filter(str.isdigit, before_bracket))

        if len(digits) >= 12:
            return digits[-12:]
        else:
            return "Không xác định"
    except Exception:
        return "Không xác định"

async def process_single_image(image_file):
    """Process a single image (async)"""
    orientation_info = await check_image_orientation_async(str(image_file))
    loai_mat = orientation_info["loai_mat"]
    rotation_angle = orientation_info["rotation_angle"]

    if loai_mat == "unknown":
        return None

    rotated_image_path = rotate_image(str(image_file), rotation_angle, TEMP_ROTATED_FOLDER)

    if loai_mat == "mat_truoc":
        result = await extract_mat_truoc_info_async(rotated_image_path)
    else:
        result = await extract_mat_sau_info_async(rotated_image_path)

    if not result or result.get("status") != "success":
        return None

    if loai_mat == "mat_sau" and "ma" in result:
        ma_idvnm = result.get("ma", "")
        so_cccd = parse_idvnm_code(ma_idvnm)
        result["so_dinh_danh"] = so_cccd

    return result

def map_missing_info(all_results):
    """Map missing 'noi_o' from mat_sau to mat_truoc"""
    mat_truoc_list = [r for r in all_results if r.get("loai_mat") == "mat_truoc"]
    mat_sau_list = [r for r in all_results if r.get("loai_mat") == "mat_sau"]

    mat_sau_map = {}
    for item in mat_sau_list:
        so_cccd = item.get("so_dinh_danh", "")
        noi_o = item.get("noi_o", "")
        if so_cccd and so_cccd != "Không xác định" and noi_o and noi_o != "Không xác định":
            mat_sau_map[so_cccd] = noi_o

    for item in mat_truoc_list:
        noi_o = item.get("noi_o", "")
        so_cccd = item.get("so_dinh_danh", "")

        if (not noi_o or noi_o == "Không xác định") and so_cccd in mat_sau_map:
            item["noi_o"] = mat_sau_map[so_cccd]
            item["noi_o_source"] = "mapped_from_mat_sau"

    return all_results

def get_image_files(folder_path):
    """Get all image files from input folder"""
    image_files = set()
    folder = Path(folder_path)

    if not folder.exists():
        return []

    for ext in SUPPORTED_EXTS:
        image_files.update(folder.rglob(f"*{ext}"))
        image_files.update(folder.rglob(f"*{ext.upper()}"))

    return sorted(list(image_files))

async def process_all_images(input_files=None):
    """
    Main processing logic used by the agent.
    """
    Path(TEMP_ROTATED_FOLDER).mkdir(parents=True, exist_ok=True)

    # Ở đây input_files đã là danh sách các đường dẫn đầy đủ (Full Path)
    if input_files and isinstance(input_files, list) and len(input_files) > 0:
        image_files = [Path(f) for f in input_files if Path(f).exists()]
    else:
        # Fallback (ít khi dùng trong trường hợp này)
        image_files = get_image_files(DEFAULT_INPUT_DIR)

    if not image_files:
        return []

    tasks = []
    for image_file in image_files:
        task = process_single_image(image_file)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    all_results = [r for r in results if r is not None]

    all_results = map_missing_info(all_results)

    final_results = [r for r in all_results if r.get("loai_mat") == "mat_truoc"]
    return final_results

def _extract_filename_from_url(name):
    """Nếu name là URL, chỉ lấy tên file. Ngược lại trả về nguyên bản."""
    if name.startswith("http://") or name.startswith("https://"):
        url_path = urlparse(name).path
        basename = unquote(os.path.basename(url_path))
        return basename if basename else name
    return name

def main(images_path: str):
    """
    Main Entry Point cho Agent.
    Input: "filename1.jpg, filename2.png" (chuỗi tên file do LLM truyền vào)
    """
    if not images_path:
        return [{"role": "assistant", "type": "text", "content": "Vui lòng upload ảnh."}]

    # 1. Lấy các đường dẫn từ Global Variables (Dùng globals().get để tránh lỗi nếu chạy test local)
    # Ưu tiên tìm trong thư mục của cuộc hội thoại hiện tại trước
    conv_path = globals().get('CONVERSATION_PATH', os.getcwd())
    file_storage_path = globals().get('FILE_STORAGE_PATH', '')
    agent_path = globals().get('AGENT_PATH', '')

    # Tập hợp các thư mục tiềm năng chứa file (loại bỏ các thư mục rỗng hoặc không tồn tại)
    search_dirs = [d for d in [conv_path, file_storage_path, agent_path] if d and os.path.exists(d)]

    # 2. Làm sạch input (Agent thường hay sinh thêm [, ], ', ")
    if isinstance(images_path, str):
        cleaned_path = images_path.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
        file_names = [f.strip() for f in cleaned_path.split(',') if f.strip()]
    elif isinstance(images_path, list):
        file_names = [str(f).strip() for f in images_path]
    else:
        file_names = []

    # 2b. Nếu tên file là URL, chỉ lấy phần tên file
    file_names = [_extract_filename_from_url(f) for f in file_names]

    # 3. Truy tìm đường dẫn thực tế của file ảnh
    valid_files_path = []
    for fname in file_names:
        # Nếu LLM đã truyền sẵn đường dẫn tuyệt đối chuẩn xác
        if os.path.isabs(fname) and os.path.exists(fname):
            valid_files_path.append(fname)
            continue

        # Tìm file trong các thư mục mà hệ thống Agent cung cấp
        found = False
        for base_dir in search_dirs:
            full_path = os.path.join(base_dir, fname)
            if os.path.isfile(full_path):
                valid_files_path.append(full_path)
                found = True
                break

        # (Tùy chọn) In log ra console hệ thống để debug nếu file bị thiếu
        if not found:
            print(f"DEBUG: Không tìm thấy file {fname} trong các thư mục: {search_dirs}")

    # Loại bỏ các đường dẫn trùng lặp
    valid_files_path = list(set(valid_files_path))

    # 4. Fallback An Toàn: Nếu vẫn không tìm thấy file theo tên, lấy TẤT CẢ ảnh trong CONVERSATION_PATH
    if not valid_files_path and conv_path:
        print("DEBUG: Kích hoạt fallback, quét toàn bộ ảnh trong CONVERSATION_PATH")
        valid_files_path = [str(p) for p in get_image_files(conv_path)]

    if not valid_files_path:
        error_msg = f"Không tìm thấy file ảnh nào. Đã thử tìm trong: {', '.join(search_dirs)}. Vui lòng kiểm tra lại tiến trình upload."
        return [{"role": "assistant", "type": "text", "content": error_msg}]

    # 5. Chạy logic xử lý (Async)
    extracted_data = asyncio.run(process_all_images(valid_files_path))

    # 6. Format kết quả trả về
    if not extracted_data:
        content_message = "Không tìm thấy thông tin căn cước công dân nào hợp lệ hoặc ảnh bị lỗi."
    else:
        messages = []
        for index, item in enumerate(extracted_data, 1):
            msg = f"--- Hồ sơ {index} ---\n"
            msg += f"Số định danh: {item.get('so_dinh_danh', 'Không xác định')}\n"
            msg += f"Họ tên: {item.get('ho_ten', 'Không xác định')}\n"
            msg += f"Ngày sinh: {item.get('ngay_sinh', 'Không xác định')}\n"
            msg += f"Giới tính: {item.get('gioi_tinh', 'Không xác định')}\n"
            msg += f"Nơi ở: {item.get('noi_o', 'Không xác định')}"
            messages.append(msg)

        content_message = "\n\n".join(messages)

    to_user = [
        {
            "role": "assistant",
            "type": "text",
            "content": content_message
        }
    ]
    return to_user
