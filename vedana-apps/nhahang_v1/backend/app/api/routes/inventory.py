from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.nha_hang import NguyenLieuCreate, NguyenLieuOut, NguyenLieuUpdate
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/ingredients", response_model=List[NguyenLieuOut])
def list_ingredients(db: Session = Depends(get_db)):
    return inventory_service.get_all_ingredients(db)


@router.put("/ingredients/{ingredient_id}", response_model=NguyenLieuOut)
def update_ingredient(
    ingredient_id: int,
    data: NguyenLieuUpdate,
    db: Session = Depends(get_db),
):
    result = inventory_service.update_ingredient(db, ingredient_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên liệu")
    return result


@router.post("/ingredients", response_model=NguyenLieuOut)
def create_ingredient(
    data: NguyenLieuCreate,
    db: Session = Depends(get_db),
):
    return inventory_service.create_ingredient(db, data)
