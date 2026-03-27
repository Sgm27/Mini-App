from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.nha_hang import IngredientCreate, IngredientOut, IngredientUpdate
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/ingredients", response_model=List[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return inventory_service.get_all_ingredients(db)


@router.put("/ingredients/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    db: Session = Depends(get_db),
):
    result = inventory_service.update_ingredient(db, ingredient_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên liệu")
    return result


@router.post("/ingredients", response_model=IngredientOut)
def create_ingredient(
    data: IngredientCreate,
    db: Session = Depends(get_db),
):
    return inventory_service.create_ingredient(db, data)
