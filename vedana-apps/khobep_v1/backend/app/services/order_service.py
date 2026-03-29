"""Order business logic — kitchen confirms, completes (with stock deduction), or rejects."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.kitchen import Order, OrderItem, Recipe, Ingredient, Dish
from app.schemas.kitchen import OrderOut, OrderItemOut
from app.services.inventory_service import recalculate_all_dishes


def _build_order_out(order: Order) -> OrderOut:
    items = []
    for oi in order.items:
        dish_name = oi.dish.name if oi.dish else f"Món #{oi.dish_id}"
        items.append(OrderItemOut(
            dish_id=oi.dish_id,
            dish_name=dish_name,
            quantity=oi.quantity,
            unit_price=float(oi.unit_price),
            subtotal=float(oi.unit_price) * oi.quantity,
        ))
    return OrderOut(
        id=order.id,
        table_number=order.table_number,
        status=order.status,
        total_amount=float(order.total_amount),
        notes=order.notes,
        reject_reason=order.reject_reason,
        items=items,
        created_at=order.created_at,
        confirmed_at=order.confirmed_at,
        completed_at=order.completed_at,
    )


def get_orders(db: Session, status_filter: str | None = None, limit: int = 50) -> list[OrderOut]:
    q = db.query(Order).order_by(Order.created_at.desc())
    if status_filter:
        q = q.filter(Order.status == status_filter)
    orders = q.limit(limit).all()
    return [_build_order_out(o) for o in orders]


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn #{order_id}")
    return order


def confirm_order(db: Session, order_id: int) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'pending' mới xác nhận được (hiện tại: {order.status})")
    order.status = "confirmed"
    order.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _build_order_out(order)


def complete_order(db: Session, order_id: int) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "confirmed":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'confirmed' mới hoàn thành được (hiện tại: {order.status})")

    # Deduct ingredients based on recipes
    ingredient_needs: dict[int, Decimal] = {}
    for oi in order.items:
        recipes = db.query(Recipe).filter(Recipe.dish_id == oi.dish_id).all()
        for r in recipes:
            ingredient_needs[r.ingredient_id] = (
                ingredient_needs.get(r.ingredient_id, Decimal("0"))
                + r.required_quantity * oi.quantity
            )

    for ing_id, needed in ingredient_needs.items():
        ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if ing:
            new_qty = max(Decimal("0"), ing.stock_quantity - needed)
            ing.stock_quantity = new_qty

    order.status = "completed"
    order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    recalculate_all_dishes(db)

    return _build_order_out(order)


def reject_order(db: Session, order_id: int, reason: str) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'pending' mới từ chối được (hiện tại: {order.status})")
    order.status = "rejected"
    order.reject_reason = reason
    db.commit()
    db.refresh(order)
    return _build_order_out(order)
