"""商标管理 API（后台）。

动态列：列表接口返回 columns 定义，前端据此渲染表头 —— 导入什么 Excel，就出现哪些列。
双编号：serial_no（唯一编号，系统生成）与 trademark_no（商标编号，来自 Excel）分列返回。
金额：price 可为 null，前端渲染为「未定价」。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import current_admin
from ..models import Admin, OperationLog, Trademark, TrademarkColumn, TrademarkImage
from ..schemas import BatchActionIn, TrademarkIn
from ..serial import next_serial

router = APIRouter(prefix="/api/admin/trademarks", tags=["admin-trademarks"])

SORTABLE = {
    "serial_no": Trademark.serial_no,
    "trademark_no": Trademark.trademark_no,
    "name": Trademark.name,
    "category": Trademark.category,
    "price": Trademark.price,
    "registration_date": Trademark.registration_date,
    "application_count": Trademark.application_count,
    "created_at": Trademark.created_at,
    "updated_at": Trademark.updated_at,
    "view_count": Trademark.view_count,
}


def _fmt_date(v) -> str | None:
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return None


def serialize_tm(tm: Trademark, with_detail: bool = False) -> dict:
    data = {
        "id": tm.id,
        # 双编号：语义不同，同时返回但字段名不同，前端分列展示
        "serial_no": tm.serial_no,
        "trademark_no": tm.trademark_no,
        "name": tm.name,
        "category": tm.category,
        "price": float(tm.price) if tm.price is not None else None,
        "has_price": tm.price is not None,
        "status": tm.status,
        "is_featured": bool(tm.is_featured),
        "registration_date": _fmt_date(tm.registration_date),
        "expiry_date": _fmt_date(tm.expiry_date),
        "legal_status": tm.legal_status,
        "application_count": tm.application_count,
        "groups": tm.groups,
        "products": tm.products,
        "ai_description": tm.ai_description,
        "remark": tm.remark,
        "view_count": tm.view_count,
        "quote_count": tm.quote_count,
        "source_file": tm.source_file,
        "source_row": tm.source_row,
        "extra": tm.extra or {},
        "created_at": tm.created_at.strftime("%Y-%m-%d %H:%M") if tm.created_at else None,
        "images": [{"url": im.url, "is_primary": im.is_primary} for im in (tm.images or [])],
    }
    if not with_detail:
        data.pop("ai_description", None)
        data.pop("products", None)
        data.pop("groups", None)
    return data


def build_columns(db: Session) -> list[dict]:
    """动态列定义：核心列全给，动态列只给「有数据」的，避免空列干扰。"""
    cols = db.execute(select(TrademarkColumn).order_by(TrademarkColumn.sort)).scalars().all()
    out = []
    for c in cols:
        if not c.visible:
            continue
        if c.kind == "extra" and c.filled_count <= 0:
            continue
        out.append({
            "key": c.key,
            "label": c.label,
            "kind": c.kind,
            "data_type": c.data_type,
            "sort": c.sort,
            "filled_count": c.filled_count,
        })
    return out


def _apply_filters(stmt, db: Session, q: str | None, category: int | None, status: str | None,
                   price_min: float | None, price_max: float | None, price_state: str | None,
                   date_from: str | None, date_to: str | None, featured: bool | None,
                   batch_id: int | None) -> tuple:
    hints: list[str] = []
    if q:
        term = q.strip()
        cond = or_(
            Trademark.name.like(f"%{term}%"),
            Trademark.trademark_no.like(f"%{term}%"),
            Trademark.serial_no.like(f"%{term}%"),
        )
        stmt = stmt.where(cond)
        if term.upper().startswith("TM-"):
            hints.append("已按「唯一编号」前缀检索")
        else:
            hints.append("同时检索了商标名 / 商标编号 / 唯一编号")
    if category:
        stmt = stmt.where(Trademark.category == category)
    if status:
        stmt = stmt.where(Trademark.status == status)
    if price_state == "set":
        stmt = stmt.where(Trademark.price.is_not(None))
    elif price_state == "unset":
        stmt = stmt.where(Trademark.price.is_(None))
    if price_min is not None:
        stmt = stmt.where(Trademark.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Trademark.price <= price_max)
    if date_from:
        stmt = stmt.where(Trademark.registration_date >= date.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Trademark.registration_date <= date.fromisoformat(date_to))
    if featured is not None:
        stmt = stmt.where(Trademark.is_featured.is_(featured))
    if batch_id:
        stmt = stmt.where(Trademark.import_batch_id == batch_id)
    return stmt, hints


@router.get("")
def list_trademarks(
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_admin),
    q: str | None = None,
    category: int | None = None,
    status: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    price_state: str | None = Query(default=None, description="set=有价 / unset=未定价"),
    date_from: str | None = None,
    date_to: str | None = None,
    featured: bool | None = None,
    batch_id: int | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = Query(default=50, le=200),
):
    stmt = select(Trademark)
    stmt, hints = _apply_filters(stmt, db, q, category, status, price_min, price_max,
                                 price_state, date_from, date_to, featured, batch_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    col = SORTABLE.get(sort_by, Trademark.created_at)
    stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
    stmt = stmt.options(selectinload(Trademark.images))
    stmt = stmt.offset(max(page - 1, 0) * page_size).limit(page_size)

    rows = db.execute(stmt).scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "columns": build_columns(db),
        "items": [serialize_tm(t) for t in rows],
        "hints": hints,
    }


@router.get("/columns")
def list_columns(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    cols = db.execute(select(TrademarkColumn).order_by(TrademarkColumn.sort)).scalars().all()
    return {
        "items": [
            {"key": c.key, "label": c.label, "kind": c.kind, "data_type": c.data_type,
             "sort": c.sort, "visible": bool(c.visible), "filled_count": c.filled_count,
             "first_seen_file": c.first_seen_file}
            for c in cols
        ]
    }


@router.put("/columns/{key}")
def update_column(key: str, payload: dict = Body(...), db: Session = Depends(get_db),
                  admin: Admin = Depends(current_admin)):
    col = db.execute(select(TrademarkColumn).where(TrademarkColumn.key == key)).scalar_one_or_none()
    if not col:
        raise HTTPException(404, "列不存在")
    if payload.get("visible") is not None:
        col.visible = bool(payload["visible"])
    if payload.get("label"):
        col.label = str(payload["label"])[:80]
    if payload.get("sort") is not None:
        col.sort = int(payload["sort"])
    db.commit()
    return {"ok": True, "key": key, "visible": bool(col.visible), "label": col.label}


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    cats = db.execute(
        select(Trademark.category, func.count(Trademark.id))
        .where(Trademark.category.is_not(None)).group_by(Trademark.category).order_by(Trademark.category)
    ).all()
    statuses = db.execute(
        select(Trademark.status, func.count(Trademark.id)).group_by(Trademark.status)
    ).all()
    price_range = db.execute(
        select(func.min(Trademark.price), func.max(Trademark.price))
        .where(Trademark.price.is_not(None))
    ).one()
    return {
        "categories": [{"value": c, "count": n} for c, n in cats],
        "statuses": [{"value": s, "count": n} for s, n in statuses],
        "price_min": float(price_range[0]) if price_range[0] is not None else None,
        "price_max": float(price_range[1]) if price_range[1] is not None else None,
        "unpriced": db.execute(
            select(func.count(Trademark.id)).where(Trademark.price.is_(None))
        ).scalar() or 0,
    }


@router.get("/{tm_id}")
def get_trademark(tm_id: int, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    tm = db.get(Trademark, tm_id)
    if not tm:
        raise HTTPException(404, "商标不存在")
    return serialize_tm(tm, with_detail=True)


@router.post("")
def create_trademark(payload: TrademarkIn, db: Session = Depends(get_db),
                     admin: Admin = Depends(current_admin)):
    if payload.trademark_no:
        dup = db.execute(
            select(Trademark).where(Trademark.trademark_no == payload.trademark_no.strip())
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(400, f"商标编号 {payload.trademark_no} 已存在（唯一编号 {dup.serial_no}）")
    tm = Trademark(serial_no=next_serial(db), source_file="手工新增")
    _assign_payload(tm, payload)
    db.add(tm)
    db.flush()
    _sync_images(db, tm, payload.images)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="trademark_create", target_type="trademark", target_id=tm.id,
                        detail=json.dumps({"serial_no": tm.serial_no, "name": tm.name}, ensure_ascii=False)))
    db.commit()
    return serialize_tm(tm, with_detail=True)


@router.put("/{tm_id}")
def update_trademark(tm_id: int, payload: TrademarkIn, db: Session = Depends(get_db),
                     admin: Admin = Depends(current_admin)):
    tm = db.get(Trademark, tm_id)
    if not tm:
        raise HTTPException(404, "商标不存在")
    if payload.trademark_no and payload.trademark_no.strip() != (tm.trademark_no or ""):
        dup = db.execute(
            select(Trademark).where(Trademark.trademark_no == payload.trademark_no.strip(),
                                    Trademark.id != tm_id)
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(400, f"商标编号 {payload.trademark_no} 已被其他记录占用")
    _assign_payload(tm, payload)
    if payload.images is not None:
        _sync_images(db, tm, payload.images)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="trademark_update", target_type="trademark", target_id=tm.id,
                        detail=json.dumps({"serial_no": tm.serial_no}, ensure_ascii=False)))
    db.commit()
    return serialize_tm(tm, with_detail=True)


def _assign_payload(tm: Trademark, p: TrademarkIn) -> None:
    tm.name = p.name.strip()
    tm.trademark_no = p.trademark_no.strip() if p.trademark_no else None
    tm.category = p.category
    tm.products = p.products
    tm.groups = p.groups
    tm.registration_date = date.fromisoformat(p.registration_date) if p.registration_date else None
    if p.expiry_date:
        tm.expiry_date = date.fromisoformat(p.expiry_date)
    elif tm.registration_date:
        d = tm.registration_date
        tm.expiry_date = date(d.year + 10, d.month, d.day)
    tm.legal_status = p.legal_status
    tm.application_count = p.application_count
    tm.price = p.price          # 允许为 None（未定价）
    tm.ai_description = p.ai_description
    tm.remark = p.remark
    if p.status:
        tm.status = p.status
    if p.is_featured is not None:
        tm.is_featured = p.is_featured
    if p.extra is not None:
        tm.extra = p.extra


def _sync_images(db: Session, tm: Trademark, urls: list[str] | None) -> None:
    if urls is None:
        return
    db.query(TrademarkImage).filter(TrademarkImage.trademark_id == tm.id).delete()
    for i, url in enumerate(urls):
        db.add(TrademarkImage(trademark_id=tm.id, url=url, sort=i, is_primary=(i == 0)))


@router.delete("/{tm_id}")
def delete_trademark(tm_id: int, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    tm = db.get(Trademark, tm_id)
    if not tm:
        raise HTTPException(404, "商标不存在")
    serial = tm.serial_no
    db.delete(tm)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="trademark_delete", target_type="trademark", target_id=tm_id,
                        detail=json.dumps({"serial_no": serial}, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "deleted": 1}


# --------------------------------------------------------------------------- #
# 批量操作：上架 / 下架 / 删除 / 改价 / 改状态 / 设精选 / 改类别
# --------------------------------------------------------------------------- #
@router.post("/batch")
def batch_action(payload: BatchActionIn, db: Session = Depends(get_db),
                 admin: Admin = Depends(current_admin)):
    if not payload.ids:
        raise HTTPException(400, "请先勾选需要操作的商标")

    rows = db.execute(select(Trademark).where(Trademark.id.in_(payload.ids))).scalars().all()
    if not rows:
        raise HTTPException(404, "勾选的商标不存在")
    affected = len(rows)
    detail: dict = {"ids": payload.ids[:200], "count": affected}

    if payload.action == "on_shelf":
        for tm in rows:
            tm.status = "on_sale"
    elif payload.action == "off_shelf":
        for tm in rows:
            tm.status = "off_shelf"
    elif payload.action == "delete":
        db.query(TrademarkImage).filter(TrademarkImage.trademark_id.in_(payload.ids)).delete(
            synchronize_session=False)
        db.query(Trademark).filter(Trademark.id.in_(payload.ids)).delete(synchronize_session=False)
    elif payload.action == "set_status":
        if payload.status not in ("on_sale", "off_shelf", "sold", "reserved"):
            raise HTTPException(400, "状态不合法")
        for tm in rows:
            tm.status = payload.status
        detail["status"] = payload.status
    elif payload.action == "set_price":
        if payload.price is None:
            raise HTTPException(400, "请填写金额")
        if payload.price < 0:
            raise HTTPException(400, "金额不能为负")
        for tm in rows:
            tm.price = round(float(payload.price), 2)
        detail["price"] = payload.price
    elif payload.action == "adjust_price":
        if payload.adjust_mode not in ("percent", "fixed", "set"):
            raise HTTPException(400, "调价方式不合法")
        if payload.adjust_value is None:
            raise HTTPException(400, "请填写调价值")
        v = float(payload.adjust_value)
        skipped = 0
        for tm in rows:
            if payload.adjust_mode == "percent":
                if tm.price is None:
                    skipped += 1
                    continue
                tm.price = round(float(tm.price) * (1 + v / 100), 2)
            elif payload.adjust_mode == "fixed":
                if tm.price is None:
                    skipped += 1
                    continue
                tm.price = round(float(tm.price) + v, 2)
            else:
                tm.price = round(v, 2)
            if tm.price is not None and tm.price < 0:
                tm.price = 0
        detail.update({"adjust_mode": payload.adjust_mode, "adjust_value": v, "skipped_unpriced": skipped})
    elif payload.action == "set_featured":
        for tm in rows:
            tm.is_featured = bool(payload.featured)
        detail["featured"] = payload.featured
    elif payload.action == "set_category":
        if payload.category is None:
            raise HTTPException(400, "请选择类别")
        for tm in rows:
            tm.category = payload.category
        detail["category"] = payload.category
    else:
        raise HTTPException(400, "不支持的操作")

    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action=f"batch_{payload.action}", target_type="trademark",
                        detail=json.dumps(detail, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "action": payload.action, "affected": affected, "detail": detail}


# --------------------------------------------------------------------------- #
# 导出
# --------------------------------------------------------------------------- #
@router.post("/export")
def export_trademarks(payload: dict = Body(default={}), db: Session = Depends(get_db),
                      admin: Admin = Depends(current_admin)):
    from ..exporter import build_export

    ids = payload.get("ids") or []
    include_images = payload.get("include_images", "url")   # url | embed | none
    columns = payload.get("columns") or None                # None = 全部可见列
    if ids:
        rows = db.execute(
            select(Trademark).where(Trademark.id.in_(ids)).options(selectinload(Trademark.images))
        ).scalars().all()
    else:
        stmt = select(Trademark).options(selectinload(Trademark.images))
        stmt, _ = _apply_filters(
            stmt, db, payload.get("q"), payload.get("category"), payload.get("status"),
            payload.get("price_min"), payload.get("price_max"), payload.get("price_state"),
            payload.get("date_from"), payload.get("date_to"), payload.get("featured"),
            payload.get("batch_id"),
        )
        stmt = stmt.order_by(Trademark.created_at.desc()).limit(int(payload.get("limit", 5000)))
        rows = db.execute(stmt).scalars().all()

    buf = build_export(rows, columns=columns, include_images=include_images)
    filename = f"trademarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="trademark_export", target_type="trademark",
                        detail=json.dumps({"count": len(rows), "images": include_images}, ensure_ascii=False)))
    db.commit()
    from urllib.parse import quote
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )