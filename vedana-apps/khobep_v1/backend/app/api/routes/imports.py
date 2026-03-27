from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import ImportReceipt
from app.schemas.kitchen import ImportRecordCreate, ImportRecordOut
from app.services.inventory_service import build_import_out, create_import, get_imports

router = APIRouter(prefix="/imports")


@router.post("", response_model=ImportRecordOut, status_code=201)
def create_import_record(data: ImportRecordCreate, db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 nguyên vật liệu")
    record = create_import(db, data)
    return build_import_out(record)


@router.get("", response_model=list[ImportRecordOut])
def list_imports(limit: int = 50, import_date: date | None = None, db: Session = Depends(get_db)):
    records = get_imports(db, limit=limit, import_date=import_date)
    return [build_import_out(r) for r in records]


@router.get("/{import_id}", response_model=ImportRecordOut)
def get_import(import_id: int, db: Session = Depends(get_db)):
    record = db.query(ImportReceipt).filter(ImportReceipt.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập")
    return build_import_out(record)
