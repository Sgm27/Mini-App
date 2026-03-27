from typing import List

from sqlalchemy.orm import Session

from app.models.nha_hang import Ingredient
from app.schemas.nha_hang import IngredientCreate, IngredientOut, IngredientUpdate


def get_all_ingredients(db: Session) -> List[IngredientOut]:
    rows = db.query(Ingredient).order_by(Ingredient.id).all()
    result = []
    for r in rows:
        stock = float(r.stock_quantity)
        threshold = float(r.warning_threshold)
        result.append(
            IngredientOut(
                id=r.id,
                name=r.name,
                unit=r.unit,
                stock_quantity=stock,
                warning_threshold=threshold,
                low_stock_warning=(threshold > 0 and stock <= threshold),
            )
        )
    return result


def update_ingredient(db: Session, ingredient_id: int, data: IngredientUpdate) -> IngredientOut:
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        return None
    ing.stock_quantity = data.stock_quantity
    if data.warning_threshold is not None:
        ing.warning_threshold = data.warning_threshold
    db.commit()
    db.refresh(ing)
    stock = float(ing.stock_quantity)
    threshold = float(ing.warning_threshold)
    return IngredientOut(
        id=ing.id,
        name=ing.name,
        unit=ing.unit,
        stock_quantity=stock,
        warning_threshold=threshold,
        low_stock_warning=(threshold > 0 and stock <= threshold),
    )


def create_ingredient(db: Session, data: IngredientCreate) -> IngredientOut:
    ing = Ingredient(
        name=data.name,
        unit=data.unit,
        stock_quantity=data.stock_quantity,
        warning_threshold=data.warning_threshold,
    )
    db.add(ing)
    db.commit()
    db.refresh(ing)
    stock = float(ing.stock_quantity)
    threshold = float(ing.warning_threshold)
    return IngredientOut(
        id=ing.id,
        name=ing.name,
        unit=ing.unit,
        stock_quantity=stock,
        warning_threshold=threshold,
        low_stock_warning=(threshold > 0 and stock <= threshold),
    )
