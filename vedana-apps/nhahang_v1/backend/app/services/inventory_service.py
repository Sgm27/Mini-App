from typing import List

from sqlalchemy.orm import Session

from app.models.nha_hang import NguyenLieu
from app.schemas.nha_hang import NguyenLieuCreate, NguyenLieuOut, NguyenLieuUpdate


def get_all_ingredients(db: Session) -> List[NguyenLieuOut]:
    rows = db.query(NguyenLieu).order_by(NguyenLieu.id).all()
    result = []
    for r in rows:
        ton = float(r.so_luong_ton)
        bao = float(r.nguong_canh_bao)
        result.append(
            NguyenLieuOut(
                id=r.id,
                ten_nguyen_lieu=r.ten_nguyen_lieu,
                don_vi=r.don_vi,
                so_luong_ton=ton,
                nguong_canh_bao=bao,
                canh_bao_thap=(bao > 0 and ton <= bao),
            )
        )
    return result


def update_ingredient(db: Session, ingredient_id: int, data: NguyenLieuUpdate) -> NguyenLieuOut:
    ng = db.query(NguyenLieu).filter(NguyenLieu.id == ingredient_id).first()
    if not ng:
        return None
    ng.so_luong_ton = data.so_luong_ton
    if data.nguong_canh_bao is not None:
        ng.nguong_canh_bao = data.nguong_canh_bao
    db.commit()
    db.refresh(ng)
    ton = float(ng.so_luong_ton)
    bao = float(ng.nguong_canh_bao)
    return NguyenLieuOut(
        id=ng.id,
        ten_nguyen_lieu=ng.ten_nguyen_lieu,
        don_vi=ng.don_vi,
        so_luong_ton=ton,
        nguong_canh_bao=bao,
        canh_bao_thap=(bao > 0 and ton <= bao),
    )


def create_ingredient(db: Session, data: NguyenLieuCreate) -> NguyenLieuOut:
    ng = NguyenLieu(
        ten_nguyen_lieu=data.ten_nguyen_lieu,
        don_vi=data.don_vi,
        so_luong_ton=data.so_luong_ton,
        nguong_canh_bao=data.nguong_canh_bao,
    )
    db.add(ng)
    db.commit()
    db.refresh(ng)
    ton = float(ng.so_luong_ton)
    bao = float(ng.nguong_canh_bao)
    return NguyenLieuOut(
        id=ng.id,
        ten_nguyen_lieu=ng.ten_nguyen_lieu,
        don_vi=ng.don_vi,
        so_luong_ton=ton,
        nguong_canh_bao=bao,
        canh_bao_thap=(bao > 0 and ton <= bao),
    )
