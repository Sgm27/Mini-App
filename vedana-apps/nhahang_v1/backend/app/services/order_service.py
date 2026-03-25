from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.nha_hang import ChiTietDonHang, CongThucMon, DonHang, MonAn, NguyenLieu
from app.schemas.nha_hang import CreateOrderRequest, DonHangOut, ChiTietDonHangOut
from app.services.menu_service import check_cart_availability


def create_order(db: Session, data: CreateOrderRequest) -> DonHangOut:
    # 1. Availability check
    availability = check_cart_availability(db, data.items)
    if not availability.co_the_phuc_vu_tat_ca:
        missing = ", ".join(i.ten for i in availability.thieu_nguyen_lieu)
        raise HTTPException(
            status_code=400,
            detail=f"Không đủ nguyên liệu: {missing}",
        )

    # 2. Build order items + calculate total
    order_items = []
    total = 0.0
    for item in data.items:
        dish = db.query(MonAn).filter(MonAn.id == item.mon_an_id).first()
        if not dish:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item.mon_an_id}")
        don_gia = float(dish.gia)
        thanh_tien = don_gia * item.so_luong
        total += thanh_tien
        order_items.append(
            {
                "mon_an_id": dish.id,
                "ten_mon": dish.ten_mon,
                "so_luong": item.so_luong,
                "don_gia": don_gia,
                "thanh_tien": thanh_tien,
            }
        )

    # 3. Persist order
    order = DonHang(
        ma_ban=data.ma_ban,
        trang_thai="da_xac_nhan",
        tong_tien=total,
        ghi_chu=data.ghi_chu,
    )
    db.add(order)
    db.flush()

    for oi in order_items:
        db.add(
            ChiTietDonHang(
                don_hang_id=order.id,
                mon_an_id=oi["mon_an_id"],
                so_luong=oi["so_luong"],
                don_gia=oi["don_gia"],
            )
        )

    # 4. Deduct inventory
    ingredient_needs: dict[int, float] = {}
    for item in data.items:
        recipes = (
            db.query(CongThucMon)
            .filter(CongThucMon.mon_an_id == item.mon_an_id)
            .all()
        )
        for r in recipes:
            ingredient_needs[r.nguyen_lieu_id] = (
                ingredient_needs.get(r.nguyen_lieu_id, 0.0)
                + float(r.so_luong_can) * item.so_luong
            )

    for ng_id, needed in ingredient_needs.items():
        ng = db.query(NguyenLieu).filter(NguyenLieu.id == ng_id).first()
        if ng:
            ng.so_luong_ton = max(0.0, float(ng.so_luong_ton) - needed)

    db.commit()
    db.refresh(order)

    return DonHangOut(
        id=order.id,
        ma_ban=order.ma_ban,
        trang_thai=order.trang_thai,
        tong_tien=float(order.tong_tien),
        ghi_chu=order.ghi_chu,
        chi_tiet=[
            ChiTietDonHangOut(**{k: v for k, v in oi.items()}) for oi in order_items
        ],
        created_at=order.created_at.isoformat(),
    )


def get_orders(db: Session, limit: int = 20) -> list[DonHangOut]:
    orders = (
        db.query(DonHang)
        .order_by(DonHang.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for o in orders:
        chi_tiet = []
        for ct in o.chi_tiet:
            ten_mon = ct.mon_an.ten_mon if ct.mon_an else f"Món #{ct.mon_an_id}"
            chi_tiet.append(
                ChiTietDonHangOut(
                    mon_an_id=ct.mon_an_id,
                    ten_mon=ten_mon,
                    so_luong=ct.so_luong,
                    don_gia=float(ct.don_gia),
                    thanh_tien=float(ct.don_gia) * ct.so_luong,
                )
            )
        result.append(
            DonHangOut(
                id=o.id,
                ma_ban=o.ma_ban,
                trang_thai=o.trang_thai,
                tong_tien=float(o.tong_tien),
                ghi_chu=o.ghi_chu,
                chi_tiet=chi_tiet,
                created_at=o.created_at.isoformat(),
            )
        )
    return result
