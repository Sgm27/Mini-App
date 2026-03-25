from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.nha_hang import CreateOrderRequest, DonHangOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=DonHangOut)
def create_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
):
    return order_service.create_order(db, payload)


@router.get("", response_model=List[DonHangOut])
def list_orders(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    return order_service.get_orders(db, limit)
