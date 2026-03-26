from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.kitchen import DishStatusOut
from app.services.inventory_service import get_dishes_with_status, recalculate_all_dishes

router = APIRouter(prefix="/dishes")


@router.get("", response_model=list[DishStatusOut])
def list_dishes(db: Session = Depends(get_db)):
    return get_dishes_with_status(db)


@router.post("/recalculate", status_code=200)
def recalculate(db: Session = Depends(get_db)):
    recalculate_all_dishes(db)
    dishes = get_dishes_with_status(db)
    return {"dishes": dishes}
