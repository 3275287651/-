"""前台公开 API：首页数据、商标浏览、详情、收藏。

注意：前台只暴露「商标编号」（官方注册号），不暴露系统内部「唯一编号」，
避免两个编号在对外场景被混用。
"""
from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import current_user, current_user_optional
from ..models import Favorite, Trademark, TrademarkImage, User, VisitLog
from ..settings_store import get_public

router = APIRouter(prefix="/api", tags=["public"])


def _status_of(tm: Trademark) -> dict:
    return {"code": tm.status, "label": {
        "on_sale": "在售", "off_shelf": "已下架", "sold": "已售出", "reserved": "预留中",
    }.get(tm.status, tm.status)}


def _design_images(tm: Trademark) -> list:
    """对外只展示商标图样；商标证属于内部/提交人材料，不在前台公开。"""
    return [im for im in (tm.images or []) if (im.kind or "design") == "design"]


def public_card(tm: Trademark) -> dict:
    """列表卡片：不含内部唯一编号"""
    designs = _design_images(tm)
    primary = next((im.url for im in designs if im.is_primary), None)
    if not primary and designs:
        primary = designs[0].url
    return {
        "id": tm.id,
        "name": tm.name,
        "category": tm.category,
        "trademark_no": tm.trademark_no,
        "price": float(tm.price) if tm.price is not None else None,
        "price_text": f"¥{float(tm.price):,.0f}" if tm.price is not None else "面议",
        "status": _status_of(tm),
        "is_featured": bool(tm.is_featured),
        "registration_date": tm.registration_date.isoformat()[:10] if tm.registration_date else None,
        "image": primary,
        "view_count": tm.view_count,
    }


def _detail(tm: Trademark, display: dict) -> dict:
    data = public_card(tm)
    designs = _design_images(tm)
    data.update({
        "products": tm.products,
        "groups": tm.groups,
        "expiry_date": tm.expiry_date.isoformat()[:10] if tm.expiry_date else None,
        "legal_status": tm.legal_status,
        "application_count": tm.application_count,
        "ai_description": tm.ai_description,
        "remark": tm.remark,
        "images": [{"url": im.url, "is_primary": im.is_primary} for im in designs],
        "extra": tm.extra or {},
    })
    # 详情页字段开关（超级管理员可配）：关掉的字段不下发
    for field, visible in (display or {}).items():
        if not visible and field in data:
            data[field] = None
    return data


@router.get("/site/config")
def site_config(response: Response, db: Session = Depends(get_db)):
    # 站点配置随时可能在后台被改动，禁止任何缓存，避免「改了标题/图标前台不变」
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return get_public(db)


@router.get("/site/home")
def site_home(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    cfg = get_public(db)
    featured = db.execute(
        select(Trademark).where(Trademark.is_featured.is_(True), Trademark.status == "on_sale",
                                Trademark.review_status == "approved")
        .options(selectinload(Trademark.images)).order_by(Trademark.updated_at.desc()).limit(8)
    ).scalars().all()
    latest = db.execute(
        select(Trademark).where(Trademark.status == "on_sale", Trademark.review_status == "approved")
        .options(selectinload(Trademark.images)).order_by(Trademark.created_at.desc()).limit(8)
    ).scalars().all()
    cats = db.execute(
        select(Trademark.category, func.count(Trademark.id))
        .where(Trademark.status == "on_sale", Trademark.review_status == "approved",
               Trademark.category.is_not(None))
        .group_by(Trademark.category).order_by(func.count(Trademark.id).desc())
    ).all()
    return {
        "config": cfg,
        "banners": cfg.get("banner") or [],
        "featured": [public_card(t) for t in featured],
        "latest": [public_card(t) for t in latest],
        "categories": [{"value": c, "count": n} for c, n in cats],
        "stats": {
            "on_sale": db.execute(
                select(func.count(Trademark.id)).where(Trademark.status == "on_sale",
                                                       Trademark.review_status == "approved")
            ).scalar() or 0,
            "total": db.execute(select(func.count(Trademark.id))).scalar() or 0,
            "categories": len(cats),
        },
    }


@router.get("/trademarks")
def public_list(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    category: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    featured: bool | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = Query(default=24, le=96),
):
    stmt = select(Trademark).where(Trademark.status == "on_sale",
                                   Trademark.review_status == "approved")
    if q:
        term = q.strip()
        stmt = stmt.where(or_(
            Trademark.name.like(f"%{term}%"),
            Trademark.trademark_no.like(f"%{term}%"),
        ))
    if category:
        stmt = stmt.where(Trademark.category == category)
    if price_min is not None:
        stmt = stmt.where(Trademark.price.is_not(None), Trademark.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Trademark.price.is_not(None), Trademark.price <= price_max)
    if date_from:
        stmt = stmt.where(Trademark.registration_date >= date.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Trademark.registration_date <= date.fromisoformat(date_to))
    if featured:
        stmt = stmt.where(Trademark.is_featured.is_(True))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    sort_map = {
        "price": Trademark.price, "registration_date": Trademark.registration_date,
        "created_at": Trademark.created_at, "view_count": Trademark.view_count,
        "application_count": Trademark.application_count,
    }
    col = sort_map.get(sort_by, Trademark.created_at)
    stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc().nullslast())
    rows = db.execute(
        stmt.options(selectinload(Trademark.images))
        .offset(max(page - 1, 0) * page_size).limit(page_size)
    ).scalars().all()

    # 访问统计（按天聚合）
    try:
        day = date.today()
        db.add(VisitLog(day=day, path="/trademarks",
                        ip=request.client.host if request.client else None))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    cats = db.execute(
        select(Trademark.category, func.count(Trademark.id))
        .where(Trademark.status == "on_sale", Trademark.review_status == "approved",
               Trademark.category.is_not(None))
        .group_by(Trademark.category).order_by(Trademark.category)
    ).all()
    pr = db.execute(
        select(func.min(Trademark.price), func.max(Trademark.price))
        .where(Trademark.status == "on_sale", Trademark.price.is_not(None))
    ).one()
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [public_card(t) for t in rows],
        "facets": {
            "categories": [{"value": c, "count": n} for c, n in cats],
            "price_min": float(pr[0]) if pr[0] is not None else None,
            "price_max": float(pr[1]) if pr[1] is not None else None,
        },
    }


@router.get("/trademarks/{tm_id}")
def public_detail(tm_id: int, db: Session = Depends(get_db)):
    tm = db.get(Trademark, tm_id)
    # 未过审的客户寄售商品一律不可见
    if not tm or tm.status not in ("on_sale", "reserved") or tm.review_status != "approved":
        raise HTTPException(404, "商标不存在或已下架")
    tm.view_count = (tm.view_count or 0) + 1
    db.commit()
    cfg = get_public(db)
    display = cfg.get("display_fields") or {}
    recs = db.execute(
        select(Trademark).where(Trademark.status == "on_sale", Trademark.id != tm_id,
                                Trademark.review_status == "approved",
                                Trademark.category == tm.category)
        .options(selectinload(Trademark.images)).limit(4)
    ).scalars().all()
    return {
        "trademark": _detail(tm, display),
        "config": cfg,
        "recommend": [public_card(t) for t in recs],
    }


# --------------------------------------------------------------------------- #
# 收藏
# --------------------------------------------------------------------------- #
@router.get("/favorites")
def my_favorites(user: User = Depends(current_user), db: Session = Depends(get_db)):
    favs = db.execute(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    ).scalars().all()
    ids = [f.trademark_id for f in favs]
    if not ids:
        return {"items": []}
    rows = db.execute(
        select(Trademark).where(Trademark.id.in_(ids)).options(selectinload(Trademark.images))
    ).scalars().all()
    order = {tid: i for i, tid in enumerate(ids)}
    rows.sort(key=lambda t: order.get(t.id, 999))
    return {"items": [public_card(t) for t in rows]}


@router.post("/favorites/{tm_id}")
def add_favorite(tm_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Trademark, tm_id):
        raise HTTPException(404, "商标不存在")
    exists = db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.trademark_id == tm_id)
    ).scalar_one_or_none()
    if not exists:
        db.add(Favorite(user_id=user.id, trademark_id=tm_id))
        db.commit()
    return {"ok": True, "favorited": True}


@router.delete("/favorites/{tm_id}")
def remove_favorite(tm_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.trademark_id == tm_id).delete()
    db.commit()
    return {"ok": True, "favorited": False}


@router.get("/favorites/ids")
def favorite_ids(user: User | None = Depends(current_user_optional), db: Session = Depends(get_db)):
    if not user:
        return {"ids": []}
    ids = db.execute(select(Favorite.trademark_id).where(Favorite.user_id == user.id)).scalars().all()
    return {"ids": list(ids)}