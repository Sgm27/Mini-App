import uuid

import boto3
from botocore.config import Config
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/upload")

REGION = settings.s3_region or "ap-southeast-1"
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)
BUCKET = settings.s3_bucket_name


class PresignedUrlRequest(BaseModel):
    filename: str


@router.post("/presigned-url")
async def get_presigned_url(body: PresignedUrlRequest):
    filename = body.filename
    if not BUCKET:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME is not configured")

    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    key = f"uploads/{uuid.uuid4().hex}.{ext}" if ext else f"uploads/{uuid.uuid4().hex}"

    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=3600,
    )

    file_url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
    return {"upload_url": upload_url, "file_url": file_url, "key": key}
