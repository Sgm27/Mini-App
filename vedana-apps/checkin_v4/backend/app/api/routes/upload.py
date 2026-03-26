import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/upload")

UPLOAD_DIR = settings.upload_dir


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to EFS storage."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
    name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    path = os.path.join(UPLOAD_DIR, name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    file_url = f"/api/upload/files/{name}"
    return {"file_url": file_url, "filename": name}


@router.get("/files/{filename}")
async def get_file(filename: str):
    """Serve a file from EFS storage."""
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
