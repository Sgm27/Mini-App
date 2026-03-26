import os
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.services.ocr_service import process_document, extract_booking_info_async, batch_extract_info_async, batch_extract_foreign_info_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    """Upload document image and extract info via OCR."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Định dạng file không hợp lệ. Chỉ chấp nhận JPG, PNG, WEBP"
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File quá lớn. Kích thước tối đa 10MB"
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File rỗng")

    # Save temp file for processing
    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        # Process with OCR
        result = await process_document(temp_path)

        if "error" in result:
            if result["error"] == "not_a_document":
                raise HTTPException(status_code=422, detail=result["message"])
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    finally:
        # Always clean up temp file - don't store original image
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/booking")
async def extract_booking(file: UploadFile = File(...)):
    """Extract booking confirmation info via OCR."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Định dạng file không hợp lệ. Chỉ chấp nhận JPG, PNG, WEBP"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File quá lớn. Kích thước tối đa 10MB")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File rỗng")

    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        result = await extract_booking_info_async(temp_path)

        if result.get("error") == "not_booking":
            raise HTTPException(status_code=422, detail=result["message"])
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/batch-extract")
async def batch_extract_documents(files: list[UploadFile] = File(...)):
    """Extract info from multiple ID document images, merge by identification number."""
    if not files:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_paths = []

    try:
        for file in files:
            if not file.filename:
                continue
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            content = await file.read()
            if len(content) == 0 or len(content) > MAX_FILE_SIZE:
                continue

            temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_paths.append(temp_path)

        if not temp_paths:
            raise HTTPException(status_code=400, detail="Không có file hợp lệ")

        result = await batch_extract_info_async(temp_paths)

        if not result["guests"]:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được thông tin từ các ảnh"
            )

        return result
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)


@router.post("/batch-extract-foreign")
async def batch_extract_foreign_documents(files: list[UploadFile] = File(...)):
    """Extract info from multiple passport images for foreign guests."""
    if not files:
        raise HTTPException(status_code=400, detail="Không có file được tải lên")

    temp_dir = "/tmp/ocr_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_paths = []

    try:
        for file in files:
            if not file.filename:
                continue
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            content = await file.read()
            if len(content) == 0 or len(content) > MAX_FILE_SIZE:
                continue

            temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_paths.append(temp_path)

        if not temp_paths:
            raise HTTPException(status_code=400, detail="Không có file hợp lệ")

        result = await batch_extract_foreign_info_async(temp_paths)

        if not result["guests"]:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được thông tin từ các ảnh hộ chiếu"
            )

        return result
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
