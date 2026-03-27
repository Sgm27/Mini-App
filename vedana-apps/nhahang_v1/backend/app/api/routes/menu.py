from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.nha_hang import (
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    CategoryOut,
    DishOut,
)
from app.services import menu_service

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return menu_service.get_categories(db)


@router.get("/dishes", response_model=List[DishOut])
def list_dishes(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return menu_service.get_dishes(db, category_id)


@router.post("/check-availability", response_model=CheckAvailabilityResponse)
def check_availability(
    payload: CheckAvailabilityRequest,
    db: Session = Depends(get_db),
):
    return menu_service.check_cart_availability(db, payload.items)
