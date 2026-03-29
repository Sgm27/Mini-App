"""Order endpoints for kitchen workflow."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.kitchen import OrderOut, RejectOrderRequest
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return order_service.get_orders(db, status_filter=status, limit=limit)


@router.put("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.confirm_order(db, order_id)


@router.put("/{order_id}/complete", response_model=OrderOut)
def complete_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.complete_order(db, order_id)


@router.put("/{order_id}/reject", response_model=OrderOut)
def reject_order(
    order_id: int,
    payload: RejectOrderRequest,
    db: Session = Depends(get_db),
):
    return order_service.reject_order(db, order_id, payload.reject_reason)
