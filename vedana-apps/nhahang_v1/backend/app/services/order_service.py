from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.nha_hang import OrderItem, Order, Dish
from app.schemas.nha_hang import CreateOrderRequest, OrderOut, OrderItemOut
from app.services.menu_service import check_cart_availability


def create_order(db: Session, data: CreateOrderRequest) -> OrderOut:
    # 1. Availability check
    availability = check_cart_availability(db, data.items)
    if not availability.can_serve_all:
        missing = ", ".join(i.name for i in availability.missing_ingredients)
        raise HTTPException(
            status_code=400,
            detail=f"Không đủ nguyên liệu: {missing}",
        )

    # 2. Build order items + calculate total
    order_items = []
    total = 0.0
    for item in data.items:
        dish = db.query(Dish).filter(Dish.id == item.dish_id).first()
        if not dish:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item.dish_id}")
        price = float(dish.price)
        subtotal = price * item.quantity
        total += subtotal
        order_items.append(
            {
                "dish_id": dish.id,
                "name": dish.name,
                "quantity": item.quantity,
                "unit_price": price,
                "subtotal": subtotal,
            }
        )

    # 3. Persist order with status=pending (kitchen will confirm)
    order = Order(
        table_number=data.table_number,
        status="pending",
        total_amount=total,
        notes=data.notes,
    )
    db.add(order)
    db.flush()

    for oi in order_items:
        db.add(
            OrderItem(
                order_id=order.id,
                dish_id=oi["dish_id"],
                quantity=oi["quantity"],
                unit_price=oi["unit_price"],
            )
        )

    # NOTE: No inventory deduction here — khobep deducts on completion

    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        table_number=order.table_number,
        status=order.status,
        total_amount=float(order.total_amount),
        notes=order.notes,
        reject_reason=order.reject_reason,
        confirmed_at=order.confirmed_at.isoformat() if order.confirmed_at else None,
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
        items=[
            OrderItemOut(**{k: v for k, v in oi.items()}) for oi in order_items
        ],
        created_at=order.created_at.isoformat(),
    )


def get_orders(db: Session, limit: int = 20) -> list[OrderOut]:
    orders = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for o in orders:
        items = []
        for oi in o.items:
            dish_name = oi.dish.name if oi.dish else f"Món #{oi.dish_id}"
            items.append(
                OrderItemOut(
                    dish_id=oi.dish_id,
                    name=dish_name,
                    quantity=oi.quantity,
                    unit_price=float(oi.unit_price),
                    subtotal=float(oi.unit_price) * oi.quantity,
                )
            )
        result.append(
            OrderOut(
                id=o.id,
                table_number=o.table_number,
                status=o.status,
                total_amount=float(o.total_amount),
                notes=o.notes,
                reject_reason=o.reject_reason,
                confirmed_at=o.confirmed_at.isoformat() if o.confirmed_at else None,
                completed_at=o.completed_at.isoformat() if o.completed_at else None,
                items=items,
                created_at=o.created_at.isoformat(),
            )
        )
    return result
