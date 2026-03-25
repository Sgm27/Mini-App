from typing import List

from sqlalchemy.orm import Session

from app.models.nha_hang import CongThucMon, DanhMucMon, MonAn, NguyenLieu
from app.schemas.nha_hang import (
    CheckAvailabilityResponse,
    DanhMucMonOut,
    MonAnAvailability,
    MonAnOut,
    ThieuNguyenLieu,
)


def get_categories(db: Session) -> List[DanhMucMonOut]:
    rows = db.query(DanhMucMon).order_by(DanhMucMon.thu_tu).all()
    return [DanhMucMonOut.model_validate(r) for r in rows]


def _check_single_dish(db: Session, mon_an_id: int) -> tuple[bool, List[str]]:
    """Check if 1 serving of a dish can be made given current stock."""
    recipes = (
        db.query(CongThucMon)
        .filter(CongThucMon.mon_an_id == mon_an_id)
        .all()
    )
    if not recipes:
        return True, []

    missing = []
    for r in recipes:
        ng = db.query(NguyenLieu).filter(NguyenLieu.id == r.nguyen_lieu_id).first()
        if ng and float(ng.so_luong_ton) < float(r.so_luong_can):
            missing.append(ng.ten_nguyen_lieu)
    return len(missing) == 0, missing


def get_dishes(db: Session, danh_muc_id: int | None = None) -> List[MonAnOut]:
    q = db.query(MonAn).filter(MonAn.active == True)
    if danh_muc_id:
        q = q.filter(MonAn.danh_muc_id == danh_muc_id)
    q = q.join(DanhMucMon).order_by(DanhMucMon.thu_tu, MonAn.id)
    dishes = q.all()

    result = []
    for d in dishes:
        co_the, missing = _check_single_dish(db, d.id)
        result.append(
            MonAnOut(
                id=d.id,
                ten_mon=d.ten_mon,
                gia=float(d.gia),
                hinh_anh=d.hinh_anh,
                mo_ta=d.mo_ta,
                danh_muc_id=d.danh_muc_id,
                danh_muc_ten=d.danh_muc.ten_danh_muc if d.danh_muc else None,
                danh_muc_icon=d.danh_muc.icon if d.danh_muc else None,
                active=d.active,
                co_the_phuc_vu=co_the,
                thieu_nguyen_lieu=missing,
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
        dish_id = item.mon_an_id
        qty = item.so_luong
        recipes = (
            db.query(CongThucMon)
            .filter(CongThucMon.mon_an_id == dish_id)
            .all()
        )
        dish_ingredient_map[dish_id] = [r.nguyen_lieu_id for r in recipes]
        for r in recipes:
            ingredient_needs[r.nguyen_lieu_id] = (
                ingredient_needs.get(r.nguyen_lieu_id, 0.0)
                + float(r.so_luong_can) * qty
            )

    # Compare against current stock
    insufficient: dict[int, ThieuNguyenLieu] = {}
    for ng_id, needed in ingredient_needs.items():
        ng = db.query(NguyenLieu).filter(NguyenLieu.id == ng_id).first()
        if ng and float(ng.so_luong_ton) < needed:
            insufficient[ng_id] = ThieuNguyenLieu(
                id=ng.id,
                ten=ng.ten_nguyen_lieu,
                don_vi=ng.don_vi,
                ton_kho=float(ng.so_luong_ton),
                can_them=round(needed - float(ng.so_luong_ton), 3),
            )

    # Per-dish status
    mon_an_results: list[MonAnAvailability] = []
    for item in items:
        dish_id = item.mon_an_id
        missing_names = [
            insufficient[ng_id].ten
            for ng_id in dish_ingredient_map.get(dish_id, [])
            if ng_id in insufficient
        ]
        mon_an_results.append(
            MonAnAvailability(
                mon_an_id=dish_id,
                co_the_phuc_vu=len(missing_names) == 0,
                thieu_nguyen_lieu=missing_names,
            )
        )

    return CheckAvailabilityResponse(
        co_the_phuc_vu_tat_ca=len(insufficient) == 0,
        thieu_nguyen_lieu=list(insufficient.values()),
        mon_an=mon_an_results,
    )
