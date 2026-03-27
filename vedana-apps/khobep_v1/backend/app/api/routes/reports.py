from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.kitchen import Dish, Ingredient, ImportReceipt
from app.schemas.kitchen import LowStockItem, ReportOverview
from app.services.inventory_service import build_import_out, get_imports

router = APIRouter(prefix="/reports")


@router.get("/overview", response_model=ReportOverview)
def get_overview(db: Session = Depends(get_db)):
    total_materials = db.query(Ingredient).count()
    total_available = db.query(Dish).filter(Dish.active == True).count()  # noqa: E712
    total_unavailable = db.query(Dish).filter(Dish.active == False).count()  # noqa: E712

    low_stock = 0
    out_of_stock = 0
    materials = db.query(Ingredient).all()
    for mat in materials:
        qty = float(mat.stock_quantity)
        min_s = float(mat.warning_threshold)
        if qty <= 0:
            out_of_stock += 1
        elif min_s > 0 and qty < min_s:
            low_stock += 1

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    today_records = db.query(ImportReceipt).filter(
        ImportReceipt.created_at >= today_start,
        ImportReceipt.created_at <= today_end,
    ).all()
    today_items = sum(len(r.items) for r in today_records)

    return ReportOverview(
        total_materials=total_materials,
        total_available_dishes=total_available,
        total_unavailable_dishes=total_unavailable,
        low_stock_count=low_stock,
        out_of_stock_count=out_of_stock,
        today_import_count=len(today_records),
        today_import_items=today_items,
    )


@router.get("/history")
def get_history(limit: int = 20, import_date: date | None = None, db: Session = Depends(get_db)):
    records = get_imports(db, limit=limit, import_date=import_date)
    return [build_import_out(r) for r in records]


@router.get("/low-stock", response_model=list[LowStockItem])
def get_low_stock(db: Session = Depends(get_db)):
    materials = db.query(Ingredient).all()
    result = []
    for mat in materials:
        qty = float(mat.stock_quantity)
        min_s = float(mat.warning_threshold)
        if qty <= 0:
            status = "out"
        elif min_s > 0 and qty < min_s:
            status = "low"
        else:
            continue
        result.append(LowStockItem(
            material_id=mat.id,
            material_name=mat.name,
            unit=mat.unit,
            quantity=qty,
            min_stock=min_s,
            status=status,
        ))
    return result
