from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import Ingredient
from app.schemas.kitchen import MaterialCreate, MaterialOut, MaterialUpdate, MaterialWithStock
from app.services.inventory_service import create_material, get_all_materials_with_stock

router = APIRouter(prefix="/materials")


@router.get("", response_model=list[MaterialWithStock])
def list_materials(db: Session = Depends(get_db)):
    return get_all_materials_with_stock(db)


@router.post("", response_model=MaterialOut, status_code=201)
def add_material(data: MaterialCreate, db: Session = Depends(get_db)):
    mat = create_material(db, name=data.name, unit=data.unit, min_stock=data.min_stock)
    return MaterialOut(
        id=mat.id,
        name=mat.name,
        unit=mat.unit,
        min_stock=float(mat.warning_threshold),
        created_at=mat.created_at,
    )


@router.put("/{material_id}", response_model=MaterialOut)
def update_material(material_id: int, data: MaterialUpdate, db: Session = Depends(get_db)):
    mat = db.query(Ingredient).filter(Ingredient.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên vật liệu")
    if data.name is not None:
        mat.name = data.name
    if data.unit is not None:
        mat.unit = data.unit
    if data.min_stock is not None:
        mat.warning_threshold = data.min_stock
    db.commit()
    db.refresh(mat)
    return MaterialOut(
        id=mat.id,
        name=mat.name,
        unit=mat.unit,
        min_stock=float(mat.warning_threshold),
        created_at=mat.created_at,
    )


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: int, db: Session = Depends(get_db)):
    mat = db.query(Ingredient).filter(Ingredient.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên vật liệu")
    db.delete(mat)
    db.commit()
