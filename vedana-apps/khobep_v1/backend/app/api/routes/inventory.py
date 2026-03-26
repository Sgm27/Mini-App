from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.kitchen import InventoryOut
from app.services.inventory_service import get_inventory, recalculate_all_dishes

router = APIRouter(prefix="/inventory")


@router.get("", response_model=list[InventoryOut])
def get_current_inventory(db: Session = Depends(get_db)):
    return get_inventory(db)


@router.post("/recalculate", status_code=200)
def recalculate_dishes(db: Session = Depends(get_db)):
    recalculate_all_dishes(db)
    return {"message": "Đã cập nhật trạng thái món ăn"}
