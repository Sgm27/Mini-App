from typing import List

from sqlalchemy.orm import Session

from app.models.nha_hang import Recipe, DishCategory, Dish, Ingredient
from app.schemas.nha_hang import (
    CheckAvailabilityResponse,
    CategoryOut,
    DishAvailability,
    DishOut,
    MissingIngredient,
)


def get_categories(db: Session) -> List[CategoryOut]:
    rows = db.query(DishCategory).order_by(DishCategory.sort_order).all()
    return [CategoryOut.model_validate(r) for r in rows]


def _check_single_dish(db: Session, dish_id: int) -> tuple[bool, List[str]]:
    """Check if 1 serving of a dish can be made given current stock."""
    recipes = (
        db.query(Recipe)
        .filter(Recipe.dish_id == dish_id)
        .all()
    )
    if not recipes:
        return True, []

    missing = []
    for r in recipes:
        ing = db.query(Ingredient).filter(Ingredient.id == r.ingredient_id).first()
        if ing and float(ing.stock_quantity) < float(r.required_quantity):
            missing.append(ing.name)
    return len(missing) == 0, missing


def get_dishes(db: Session, category_id: int | None = None) -> List[DishOut]:
    q = db.query(Dish).filter(Dish.active == True)
    if category_id:
        q = q.filter(Dish.category_id == category_id)
    q = q.join(DishCategory).order_by(DishCategory.sort_order, Dish.id)
    dishes = q.all()

    result = []
    for d in dishes:
        can_serve, missing = _check_single_dish(db, d.id)
        result.append(
            DishOut(
                id=d.id,
                name=d.name,
                price=float(d.price),
                image=d.image,
                description=d.description,
                category_id=d.category_id,
                category_name=d.category.name if d.category else None,
                category_icon=d.category.icon if d.category else None,
                active=d.active,
                can_serve=can_serve,
                missing_ingredients=missing,
            )
        )
    return result


def check_cart_availability(
    db: Session, items: list
) -> CheckAvailabilityResponse:
    """
    Check if ALL items in the cart can be served simultaneously.
    Aggregates ingredient usage across all cart items.
    """
    # Aggregate total ingredient needs
    ingredient_needs: dict[int, float] = {}
    dish_ingredient_map: dict[int, list[int]] = {}

    for item in items:
        d_id = item.dish_id
        qty = item.quantity
        recipes = (
            db.query(Recipe)
            .filter(Recipe.dish_id == d_id)
            .all()
        )
        dish_ingredient_map[d_id] = [r.ingredient_id for r in recipes]
        for r in recipes:
            ingredient_needs[r.ingredient_id] = (
                ingredient_needs.get(r.ingredient_id, 0.0)
                + float(r.required_quantity) * qty
            )

    # Compare against current stock
    insufficient: dict[int, MissingIngredient] = {}
    for ing_id, needed in ingredient_needs.items():
        ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if ing and float(ing.stock_quantity) < needed:
            insufficient[ing_id] = MissingIngredient(
                id=ing.id,
                name=ing.name,
                unit=ing.unit,
                in_stock=float(ing.stock_quantity),
                needed=round(needed - float(ing.stock_quantity), 3),
            )

    # Per-dish status
    dish_results: list[DishAvailability] = []
    for item in items:
        d_id = item.dish_id
        missing_names = [
            insufficient[ing_id].name
            for ing_id in dish_ingredient_map.get(d_id, [])
            if ing_id in insufficient
        ]
        dish_results.append(
            DishAvailability(
                dish_id=d_id,
                can_serve=len(missing_names) == 0,
                missing_ingredients=missing_names,
            )
        )

    return CheckAvailabilityResponse(
        can_serve_all=len(insufficient) == 0,
        missing_ingredients=list(insufficient.values()),
        dishes=dish_results,
    )
