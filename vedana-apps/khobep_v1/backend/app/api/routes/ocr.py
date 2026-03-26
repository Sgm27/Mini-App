from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import NguyenLieu
from app.schemas.kitchen import ExtractResponse, OcrExtractRequest, VoiceExtractRequest
from app.services.ocr_service import extract_from_image, extract_from_voice

router = APIRouter(prefix="/ocr")


def _match_materials(items, db: Session):
    """Try to match extracted item names to known ingredients."""
    all_mats = db.query(NguyenLieu).all()
    mat_map = {m.ten_nguyen_lieu.lower(): m for m in all_mats}

    for item in items:
        name_lower = item.name.lower()
        # Exact match
        if name_lower in mat_map:
            item.material_id = mat_map[name_lower].id
            item.unit = mat_map[name_lower].don_vi
            continue
        # Partial match
        for mat_name, mat in mat_map.items():
            if name_lower in mat_name or mat_name in name_lower:
                item.material_id = mat.id
                item.unit = mat.don_vi
                break
    return items


@router.post("/image", response_model=ExtractResponse)
async def extract_from_invoice_image(data: OcrExtractRequest, db: Session = Depends(get_db)):
    try:
        items = await extract_from_image(data.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = _match_materials(items, db)
    return ExtractResponse(items=items)


@router.post("/voice", response_model=ExtractResponse)
async def extract_from_voice_transcript(data: VoiceExtractRequest, db: Session = Depends(get_db)):
    if not data.transcript.strip():
        raise HTTPException(status_code=400, detail="Nội dung giọng nói trống")

    items = await extract_from_voice(data.transcript)
    items = _match_materials(items, db)
    return ExtractResponse(items=items, raw_text=data.transcript)
