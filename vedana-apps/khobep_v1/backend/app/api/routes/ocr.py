from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import Ingredient
from app.schemas.kitchen import (
    ExtractResponse,
    OcrExtractRequest,
    OcrReceiptResponse,
    ReceiptHeader,
    ReceiptItem,
    ReceiptSummary,
    VoiceExtractRequest,
)
from app.services.ocr_service import extract_from_voice, extract_receipt_from_image

router = APIRouter(prefix="/ocr")


def _match_and_create_materials(items: list[dict], db: Session) -> list[ReceiptItem]:
    """Match extracted items to ingredients. Auto-create if not found."""
    all_mats = db.query(Ingredient).all()
    mat_map = {m.name.lower(): m for m in all_mats}

    result = []
    for raw_item in items:
        name = raw_item.get("name", "")
        name_lower = name.lower().strip()
        material_id = None
        is_new = False
        matched_unit = raw_item.get("unit", "kg")

        # Exact match
        if name_lower in mat_map:
            material_id = mat_map[name_lower].id
            matched_unit = mat_map[name_lower].unit
        else:
            # Partial match
            for mat_name, mat in mat_map.items():
                if name_lower in mat_name or mat_name in name_lower:
                    material_id = mat.id
                    matched_unit = mat.unit
                    break

        # Auto-create if not found
        if material_id is None and name.strip():
            unit = raw_item.get("unit", "kg")
            new_mat = Ingredient(name=name.strip(), unit=unit)
            db.add(new_mat)
            db.flush()
            material_id = new_mat.id
            is_new = True
            # Update map for subsequent items
            mat_map[name_lower] = new_mat

        result.append(ReceiptItem(
            item_code=raw_item.get("item_code"),
            name=name,
            unit=matched_unit,
            quantity=float(raw_item.get("quantity", 0)),
            unit_price=raw_item.get("unit_price"),
            amount=raw_item.get("amount"),
            location=raw_item.get("location"),
            acc_no=raw_item.get("acc_no"),
            material_id=material_id,
            is_new=is_new,
        ))

    db.commit()
    return result


@router.post("/image", response_model=OcrReceiptResponse)
async def extract_from_invoice_image(data: OcrExtractRequest, db: Session = Depends(get_db)):
    try:
        raw_result = await extract_receipt_from_image(data.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Match items to ingredients (auto-create if needed)
    matched_items = _match_and_create_materials(raw_result.get("items", []), db)

    header_data = raw_result.get("header", {})
    summary_data = raw_result.get("summary")

    return OcrReceiptResponse(
        header=ReceiptHeader(**header_data) if header_data else ReceiptHeader(),
        items=matched_items,
        summary=ReceiptSummary(**summary_data) if summary_data else None,
    )


def _match_voice_materials(items, db: Session):
    """Match voice-extracted items to known ingredients (no auto-create)."""
    all_mats = db.query(Ingredient).all()
    mat_map = {m.name.lower(): m for m in all_mats}

    for item in items:
        name_lower = item.name.lower()
        if name_lower in mat_map:
            item.material_id = mat_map[name_lower].id
            item.unit = mat_map[name_lower].unit
            continue
        for mat_name, mat in mat_map.items():
            if name_lower in mat_name or mat_name in name_lower:
                item.material_id = mat.id
                item.unit = mat.unit
                break
    return items


@router.post("/voice", response_model=ExtractResponse)
async def extract_from_voice_transcript(data: VoiceExtractRequest, db: Session = Depends(get_db)):
    if not data.transcript.strip():
        raise HTTPException(status_code=400, detail="Nội dung giọng nói trống")

    items = await extract_from_voice(data.transcript)
    items = _match_voice_materials(items, db)
    return ExtractResponse(items=items, raw_text=data.transcript)
