from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.nha_hang import OrderItem, Recipe, Order, Dish, Ingredient
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

    # 3. Persist order
    order = Order(
        table_number=data.table_number,
        status="confirmed",
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

    # 4. Deduct inventory
    ingredient_needs: dict[int, float] = {}
    for item in data.items:
        recipes = (
            db.query(Recipe)
            .filter(Recipe.dish_id == item.dish_id)
            .all()
        )
        for r in recipes:
            ingredient_needs[r.ingredient_id] = (
                ingredient_needs.get(r.ingredient_id, 0.0)
                + float(r.required_quantity) * item.quantity
            )

    for ing_id, needed in ingredient_needs.items():
        ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if ing:
            ing.stock_quantity = max(0.0, float(ing.stock_quantity) - needed)

    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        table_number=order.table_number,
        status=order.status,
        total_amount=float(order.total_amount),
        notes=order.notes,
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
                items=items,
                created_at=o.created_at.isoformat(),
            )
        )
    return result
