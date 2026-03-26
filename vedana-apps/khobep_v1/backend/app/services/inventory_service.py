"""Inventory and import business logic — using shared nhahang_v1 DB."""

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.kitchen import (
    ChiTietNhapKho, CongThucMon, MonAn, NguyenLieu, PhieuNhapKho,
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
    materials = db.query(NguyenLieu).all()
    result = []
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        result.append(MaterialWithStock(
            id=mat.id,
            name=mat.ten_nguyen_lieu,
            unit=mat.don_vi,
            min_stock=min_s,
            created_at=mat.created_at,
            quantity=qty,
            stock_status=_stock_status(qty, min_s),
        ))
    return result


def create_material(db: Session, name: str, unit: str, min_stock: float = 0.0) -> NguyenLieu:
    mat = NguyenLieu(
        ten_nguyen_lieu=name,
        don_vi=unit,
        nguong_canh_bao=Decimal(str(min_stock)),
        so_luong_ton=Decimal("0"),
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


# ─── Inventory ───────────────────────────────────────────────

def get_inventory(db: Session) -> list[InventoryOut]:
    materials = db.query(NguyenLieu).all()
    result = []
    for mat in materials:
        qty = float(mat.so_luong_ton)
        min_s = float(mat.nguong_canh_bao)
        result.append(InventoryOut(
            material_id=mat.id,
            material_name=mat.ten_nguyen_lieu,
            unit=mat.don_vi,
            quantity=qty,
            min_stock=min_s,
            stock_status=_stock_status(qty, min_s),
            last_updated=mat.updated_at,
        ))
    return result


# ─── Imports ─────────────────────────────────────────────────

def create_import(db: Session, data: ImportRecordCreate) -> PhieuNhapKho:
    record = PhieuNhapKho(
        nha_cung_cap=data.supplier_name,
        ghi_chu=data.notes,
        hinh_anh_url=data.image_url,
        nguoi_nhap=data.created_by,
    )
    db.add(record)
    db.flush()

    for item_in in data.items:
        mat = db.query(NguyenLieu).filter(NguyenLieu.id == item_in.material_id).first()
        if not mat:
            continue

        # Add import line item
        import_item = ChiTietNhapKho(
            phieu_nhap_id=record.id,
            nguyen_lieu_id=item_in.material_id,
            so_luong=Decimal(str(item_in.quantity)),
            don_vi=item_in.unit,
        )
        db.add(import_item)

        # Unit conversion: g→kg, ml→lít
        qty = Decimal(str(item_in.quantity))
        unit_lower = item_in.unit.lower().strip()
        mat_unit_lower = mat.don_vi.lower().strip()
        if unit_lower == "g" and mat_unit_lower == "kg":
            qty = qty / 1000
        elif unit_lower == "ml" and mat_unit_lower in ("lít", "lit", "l"):
            qty = qty / 1000

        # Atomic stock update — avoids TOCTOU race
        db.execute(
            update(NguyenLieu)
            .where(NguyenLieu.id == item_in.material_id)
            .values(so_luong_ton=NguyenLieu.so_luong_ton + qty)
        )

    db.commit()
    db.refresh(record)

    # Recalculate dish availability
    recalculate_all_dishes(db)

    return record


def get_imports(db: Session, limit: int = 50, import_date: date | None = None) -> list[PhieuNhapKho]:
    q = db.query(PhieuNhapKho).order_by(PhieuNhapKho.created_at.desc())
    if import_date:
        q = q.filter(
            PhieuNhapKho.created_at >= datetime.combine(import_date, datetime.min.time()),
            PhieuNhapKho.created_at < datetime.combine(import_date, datetime.max.time()),
        )
    return q.limit(limit).all()


def build_import_out(record: PhieuNhapKho) -> ImportRecordOut:
    items_out = []
    for it in record.items:
        items_out.append(ImportItemOut(
            id=it.id,
            material_id=it.nguyen_lieu_id,
            material_name=it.nguyen_lieu.ten_nguyen_lieu if it.nguyen_lieu else "?",
            quantity=float(it.so_luong),
            unit=it.don_vi,
        ))
    return ImportRecordOut(
        id=record.id,
        supplier_name=record.nha_cung_cap,
        notes=record.ghi_chu,
        image_url=record.hinh_anh_url,
        created_by=record.nguoi_nhap,
        created_at=record.created_at,
        items=items_out,
    )


# ─── Dish Availability ───────────────────────────────────────

def recalculate_all_dishes(db: Session) -> None:
    dishes = db.query(MonAn).all()
    for dish in dishes:
        _recalc_dish(db, dish)
    db.commit()


def _recalc_dish(db: Session, dish: MonAn) -> None:
    """Check if all recipe ingredients are available in stock."""
    for ri in dish.cong_thuc:
        current_qty = float(ri.nguyen_lieu.so_luong_ton) if ri.nguyen_lieu else 0.0
        required = float(ri.so_luong_can)
        if current_qty < required:
            dish.active = False
            return
    dish.active = True


def get_dishes_with_status(db: Session) -> list[dict]:
    dishes = db.query(MonAn).all()
    result = []
    for dish in dishes:
        missing = []
        for ri in dish.cong_thuc:
            qty = float(ri.nguyen_lieu.so_luong_ton) if ri.nguyen_lieu else 0.0
            if qty < float(ri.so_luong_can):
                mat_name = ri.nguyen_lieu.ten_nguyen_lieu if ri.nguyen_lieu else "?"
                missing.append(mat_name)
        # Resolve category from danh_muc_mon relationship
        category = dish.danh_muc.ten_danh_muc if dish.danh_muc else None
        result.append({
            "id": dish.id,
            "name": dish.ten_mon,
            "category": category,
            "is_available": dish.active,
            "missing_ingredients": missing,
        })
    return result
