from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.nha_hang import (
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    DanhMucMonOut,
    MonAnOut,
)
from app.services import menu_service

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/categories", response_model=List[DanhMucMonOut])
def list_categories(db: Session = Depends(get_db)):
    return menu_service.get_categories(db)


@router.get("/dishes", response_model=List[MonAnOut])
def list_dishes(
    danh_muc_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return menu_service.get_dishes(db, danh_muc_id)


@router.post("/check-availability", response_model=CheckAvailabilityResponse)
def check_availability(
    payload: CheckAvailabilityRequest,
    db: Session = Depends(get_db),
):
    return menu_service.check_cart_availability(db, payload.items)
