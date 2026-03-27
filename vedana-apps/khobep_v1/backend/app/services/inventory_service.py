"""Inventory and import business logic — using shared nhahang_v1 DB."""

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.kitchen import (
    ImportReceiptItem, Recipe, Dish, Ingredient, ImportReceipt,
)
from app.schemas.kitchen import (
    ImportRecordCreate, ImportRecordOut, ImportItemOut,
    InventoryOut, MaterialWithStock,
)


def _stock_status(quantity: float, min_stock: float) -> str:
    if quantity <= 0:
        return "out"
    if min_stock > 0 and quantity < min_stock:
        return "low"
    return "ok"


# ─── Materials ───────────────────────────────────────────────

def get_all_materials_with_stock(db: Session) -> list[MaterialWithStock]:
    materials = db.query(Ingredient).all()
    result = []
    for mat in materials:
        qty = float(mat.stock_quantity)
        min_s = float(mat.warning_threshold)
        result.append(MaterialWithStock(
            id=mat.id,
            name=mat.name,
            unit=mat.unit,
            min_stock=min_s,
            created_at=mat.created_at,
            quantity=qty,
            stock_status=_stock_status(qty, min_s),
        ))
    return result


def create_material(db: Session, name: str, unit: str, min_stock: float = 0.0) -> Ingredient:
    mat = Ingredient(
        name=name,
        unit=unit,
        warning_threshold=Decimal(str(min_stock)),
        stock_quantity=Decimal("0"),
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


# ─── Inventory ───────────────────────────────────────────────

def get_inventory(db: Session) -> list[InventoryOut]:
    materials = db.query(Ingredient).all()
    result = []
    for mat in materials:
        qty = float(mat.stock_quantity)
        min_s = float(mat.warning_threshold)
        result.append(InventoryOut(
            material_id=mat.id,
            material_name=mat.name,
            unit=mat.unit,
            quantity=qty,
            min_stock=min_s,
            stock_status=_stock_status(qty, min_s),
            last_updated=mat.updated_at,
        ))
    return result


# ─── Imports ─────────────────────────────────────────────────

def create_import(db: Session, data: ImportRecordCreate) -> ImportReceipt:
    # Parse receipt_date if provided (DD/MM/YYYY format)
    parsed_date = None
    if data.receipt_date:
        try:
            from datetime import datetime as dt
            parsed_date = dt.strptime(data.receipt_date, "%d/%m/%Y")
        except ValueError:
            pass

    record = ImportReceipt(
        supplier=data.supplier_name or data.vendor_name,
        notes=data.notes,
        image_url=data.image_url,
        received_by=data.created_by,
        receipt_date=parsed_date,
        description=data.description,
        vendor_name=data.vendor_name,
        period=data.period,
        voucher_no=data.voucher_no,
        invoice_serial=data.invoice_serial,
        invoice_no=data.invoice_no,
    )
    db.add(record)
    db.flush()

    for item_in in data.items:
        # Skip items without material_id
        if not item_in.material_id:
            continue

        mat = db.query(Ingredient).filter(Ingredient.id == item_in.material_id).first()
        if not mat:
            continue

        # Add import line item with new fields
        import_item = ImportReceiptItem(
            import_receipt_id=record.id,
            ingredient_id=item_in.material_id,
            quantity=Decimal(str(item_in.quantity)),
            unit=item_in.unit,
            item_code=item_in.item_code,
            item_name=item_in.item_name,
            unit_price=Decimal(str(item_in.unit_price)) if item_in.unit_price is not None else None,
            amount=Decimal(str(item_in.amount)) if item_in.amount is not None else None,
            location=item_in.location,
            acc_no=item_in.acc_no,
        )
        db.add(import_item)

        # Unit conversion: g→kg, ml→lít
        qty = Decimal(str(item_in.quantity))
        unit_lower = item_in.unit.lower().strip()
        mat_unit_lower = mat.unit.lower().strip()
        if unit_lower == "g" and mat_unit_lower == "kg":
            qty = qty / 1000
        elif unit_lower == "ml" and mat_unit_lower in ("lít", "lit", "l"):
            qty = qty / 1000

        # Atomic stock update
        db.execute(
            update(Ingredient)
            .where(Ingredient.id == item_in.material_id)
            .values(stock_quantity=Ingredient.stock_quantity + qty)
        )

    db.commit()
    db.refresh(record)

    recalculate_all_dishes(db)

    return record


def get_imports(db: Session, limit: int = 50, import_date: date | None = None) -> list[ImportReceipt]:
    q = db.query(ImportReceipt).order_by(ImportReceipt.created_at.desc())
    if import_date:
        q = q.filter(
            ImportReceipt.created_at >= datetime.combine(import_date, datetime.min.time()),
            ImportReceipt.created_at < datetime.combine(import_date, datetime.max.time()),
        )
    return q.limit(limit).all()


def build_import_out(record: ImportReceipt) -> ImportRecordOut:
    items_out = []
    for it in record.items:
        items_out.append(ImportItemOut(
            id=it.id,
            material_id=it.ingredient_id,
            material_name=it.ingredient.name if it.ingredient else "?",
            quantity=float(it.quantity),
            unit=it.unit,
            item_code=it.item_code,
            item_name=it.item_name,
            unit_price=float(it.unit_price) if it.unit_price is not None else None,
            amount=float(it.amount) if it.amount is not None else None,
            location=it.location,
            acc_no=it.acc_no,
        ))

    receipt_date_str = None
    if record.receipt_date:
        receipt_date_str = record.receipt_date.strftime("%d/%m/%Y")

    return ImportRecordOut(
        id=record.id,
        supplier_name=record.supplier,
        notes=record.notes,
        image_url=record.image_url,
        created_by=record.received_by,
        created_at=record.created_at,
        receipt_date=receipt_date_str,
        description=record.description,
        vendor_name=record.vendor_name,
        period=record.period,
        voucher_no=record.voucher_no,
        invoice_serial=record.invoice_serial,
        invoice_no=record.invoice_no,
        items=items_out,
    )


# ─── Dish Availability ───────────────────────────────────────

def recalculate_all_dishes(db: Session) -> None:
    dishes = db.query(Dish).all()
    for dish in dishes:
        _recalc_dish(db, dish)
    db.commit()


def _recalc_dish(db: Session, dish: Dish) -> None:
    """Check if all recipe ingredients are available in stock."""
    for ri in dish.recipes:
        current_qty = float(ri.ingredient.stock_quantity) if ri.ingredient else 0.0
        required = float(ri.required_quantity)
        if current_qty < required:
            dish.active = False
            return
    dish.active = True


def get_dishes_with_status(db: Session) -> list[dict]:
    dishes = db.query(Dish).all()
    result = []
    for dish in dishes:
        missing = []
        for ri in dish.recipes:
            qty = float(ri.ingredient.stock_quantity) if ri.ingredient else 0.0
            if qty < float(ri.required_quantity):
                mat_name = ri.ingredient.name if ri.ingredient else "?"
                missing.append(mat_name)
        category = dish.category.name if dish.category else None
        result.append({
            "id": dish.id,
            "name": dish.name,
            "category": category,
            "is_available": dish.active,
            "missing_ingredients": missing,
        })
    return result
