"""后台杂项：站点配置、看板统计、操作日志、Banner、图片上传。"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote as urlquote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..config import MEDIA_URL, UPLOAD_DIR
from ..database import get_db
from ..deps import current_admin, require_super_admin
from ..models import (
    Admin, Banner, ImportBatch, Notification, OperationLog, Quote, Trademark, TrademarkColumn,
    TrademarkImage, User, VisitLog,
)
from ..settings_store import get_all, set_values

router = APIRouter(prefix="/api/admin", tags=["admin-misc"])

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


@router.get("/settings")
def read_settings(db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    return {"values": get_all(db)}


@router.put("/settings")
def write_settings(payload: dict, db: Session = Depends(get_db),
                   admin: Admin = Depends(require_super_admin)):
    values = payload.get("values") or payload
    if not isinstance(values, dict):
        raise HTTPException(400, "参数格式不正确")
    set_values(db, values)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="settings_update", target_type="settings",
                        detail=json.dumps({"keys": list(values.keys())}, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "values": get_all(db)}


@router.get("/stats")
def dashboard(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    def count(*conds) -> int:
        stmt = select(func.count(Trademark.id))
        for c in conds:
            stmt = stmt.where(c)
        return db.execute(stmt).scalar() or 0

    status_rows = db.execute(
        select(Trademark.status, func.count(Trademark.id)).group_by(Trademark.status)
    ).all()
    by_status = {s: n for s, n in status_rows}
    today = date.today()
    today_visits = db.execute(
        select(func.count(VisitLog.id)).where(VisitLog.day == today)
    ).scalar() or 0
    week_visits = db.execute(
        select(func.count(VisitLog.id)).where(VisitLog.day >= today - timedelta(days=7))
    ).scalar() or 0
    total_visits = db.execute(select(func.count(VisitLog.id))).scalar() or 0

    cat_rows = db.execute(
        select(Trademark.category, func.count(Trademark.id))
        .where(Trademark.category.is_not(None)).group_by(Trademark.category)
        .order_by(func.count(Trademark.id).desc())
    ).all()

    # 价格区间分布
    buckets = [(0, 2000), (2000, 5000), (5000, 10000), (10000, 30000), (30000, 10 ** 9)]
    labels = ["2000以下", "2000-5000", "5000-1万", "1万-3万", "3万以上"]
    price_dist = []
    for (lo, hi), label in zip(buckets, labels):
        n = db.execute(
            select(func.count(Trademark.id)).where(
                Trademark.price.is_not(None), Trademark.price >= lo, Trademark.price < hi)
        ).scalar() or 0
        price_dist.append({"label": label, "count": n})

    # 近 30 天访问趋势
    trend_rows = db.execute(
        select(VisitLog.day, func.count(VisitLog.id))
        .where(VisitLog.day >= today - timedelta(days=29)).group_by(VisitLog.day)
    ).all()
    trend_map = {d: n for d, n in trend_rows}
    trend = [
        {"day": (today - timedelta(days=29 - i)).isoformat(),
         "count": trend_map.get(today - timedelta(days=29 - i), 0)}
        for i in range(30)
    ]

    expiring_30 = count(Trademark.expiry_date.is_not(None),
                        Trademark.expiry_date <= today + timedelta(days=30),
                        Trademark.expiry_date >= today)
    expiring_90 = count(Trademark.expiry_date.is_not(None),
                        Trademark.expiry_date <= today + timedelta(days=90),
                        Trademark.expiry_date >= today)

    return {
        "trademarks": {
            "total": sum(by_status.values()),
            "on_sale": by_status.get("on_sale", 0),
            "off_shelf": by_status.get("off_shelf", 0),
            "sold": by_status.get("sold", 0),
            "reserved": by_status.get("reserved", 0),
            "unpriced": count(Trademark.price.is_(None)),
            "featured": count(Trademark.is_featured.is_(True)),
        },
        "images": db.execute(select(func.count(TrademarkImage.id))).scalar() or 0,
        "customers": {
            "total": db.execute(select(func.count(User.id))).scalar() or 0,
            "today": db.execute(
                select(func.count(User.id)).where(User.created_at >= datetime.combine(today, datetime.min.time()))
            ).scalar() or 0,
        },
        "quotes": {
            "total": db.execute(select(func.count(Quote.id))).scalar() or 0,
            "today": db.execute(
                select(func.count(Quote.id)).where(Quote.created_at >= datetime.combine(today, datetime.min.time()))
            ).scalar() or 0,
        },
        "visits": {"today": today_visits, "week": week_visits, "total": total_visits, "trend": trend},
        "categories": [{"label": f"{c}类", "value": c, "count": n} for c, n in cat_rows],
        "price_dist": price_dist,
        "expiring": {"within_30": expiring_30, "within_90": expiring_90},
        "import_batches": db.execute(select(func.count(ImportBatch.id))).scalar() or 0,
    }


@router.get("/logs")
def logs(page: int = 1, page_size: int = 50, action: str | None = None,
         db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    stmt = select(OperationLog)
    if action:
        stmt = stmt.where(OperationLog.action.like(f"%{action}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(
        stmt.order_by(desc(OperationLog.created_at))
        .offset(max(page - 1, 0) * page_size).limit(page_size)
    ).scalars().all()
    return {"total": total, "items": [{
        "id": r.id, "admin_name": r.admin_name or "-", "action": r.action,
        "target_type": r.target_type, "target_id": r.target_id, "detail": r.detail,
        "ip": r.ip, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
    } for r in rows]}


@router.get("/expiring")
def expiring(days: int = 90, db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    today = date.today()
    rows = db.execute(
        select(Trademark).where(
            Trademark.expiry_date.is_not(None),
            Trademark.expiry_date <= today + timedelta(days=days),
        ).order_by(Trademark.expiry_date.asc()).limit(300)
    ).scalars().all()
    return {"items": [{
        "id": t.id, "serial_no": t.serial_no, "trademark_no": t.trademark_no, "name": t.name,
        "category": t.category, "expiry_date": t.expiry_date.isoformat()[:10],
        "days_left": (t.expiry_date - today).days, "status": t.status,
    } for t in rows]}


# --------------------------------------------------------------------------- #
# Banner
# --------------------------------------------------------------------------- #
@router.get("/banners")
def list_banners(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    rows = db.execute(select(Banner).order_by(Banner.sort)).scalars().all()
    return {"items": [{
        "id": b.id, "image_url": b.image_url, "link_url": b.link_url, "title": b.title,
        "subtitle": b.subtitle, "sort": b.sort, "status": b.status,
    } for b in rows]}


@router.post("/banners")
def create_banner(payload: dict, db: Session = Depends(get_db),
                  admin: Admin = Depends(require_super_admin)):
    if not payload.get("image_url"):
        raise HTTPException(400, "请上传轮播图")
    n = db.execute(select(func.count(Banner.id))).scalar() or 0
    if n >= 5:
        raise HTTPException(400, "首页轮播图最多 5 张")
    b = Banner(image_url=payload["image_url"], link_url=payload.get("link_url"),
               title=payload.get("title"), subtitle=payload.get("subtitle"),
               sort=int(payload.get("sort", n)), status=1 if payload.get("status", 1) else 0)
    db.add(b)
    db.commit()
    return {"ok": True, "id": b.id}


@router.put("/banners/{banner_id}")
def update_banner(banner_id: int, payload: dict, db: Session = Depends(get_db),
                  admin: Admin = Depends(require_super_admin)):
    b = db.get(Banner, banner_id)
    if not b:
        raise HTTPException(404, "轮播图不存在")
    for f in ("image_url", "link_url", "title", "subtitle"):
        if f in payload:
            setattr(b, f, payload[f])
    if "sort" in payload:
        b.sort = int(payload["sort"])
    if "status" in payload:
        b.status = 1 if payload["status"] else 0
    db.commit()
    return {"ok": True}


@router.delete("/banners/{banner_id}")
def delete_banner(banner_id: int, db: Session = Depends(get_db),
                  admin: Admin = Depends(require_super_admin)):
    b = db.get(Banner, banner_id)
    if not b:
        raise HTTPException(404, "轮播图不存在")
    db.delete(b)
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# 图片上传
# --------------------------------------------------------------------------- #
@router.post("/upload")
async def upload_image(file: UploadFile = File(...), scene: str = "common",
                       db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in IMAGE_EXT:
        raise HTTPException(400, f"仅支持 {'/'.join(sorted(IMAGE_EXT))} 格式")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过 5MB")
    safe_scene = "".join(ch for ch in scene if ch.isalnum() or ch in "-_") or "common"
    target_dir = UPLOAD_DIR / "uploads" / safe_scene
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}{ext}"
    (target_dir / name).write_bytes(raw)
    url = f"{MEDIA_URL}/uploads/{safe_scene}/{name}"
    return {"ok": True, "url": url, "size": len(raw)}


# --------------------------------------------------------------------------- #
# 运营账户管理
# --------------------------------------------------------------------------- #
@router.get("/admins")
def list_admins(db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    rows = db.execute(select(Admin).order_by(Admin.id)).scalars().all()
    return {"items": [{
        "id": a.id, "username": a.username, "name": a.name, "role": a.role, "status": a.status,
        "last_login_at": a.last_login_at.strftime("%Y-%m-%d %H:%M") if a.last_login_at else None,
        "created_at": a.created_at.strftime("%Y-%m-%d") if a.created_at else None,
    } for a in rows]}


@router.post("/admins")
def create_admin(payload: dict, db: Session = Depends(get_db),
                 admin: Admin = Depends(require_super_admin)):
    from ..security import hash_password

    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(400, "用户名至少 3 位，密码至少 6 位")
    if db.execute(select(Admin).where(Admin.username == username)).scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    a = Admin(username=username, password_hash=hash_password(password),
              name=payload.get("name") or username,
              role="admin" if payload.get("role") == "admin" else "operator")
    db.add(a)
    db.commit()
    return {"ok": True, "id": a.id}


@router.put("/admins/{admin_id}")
def update_admin(admin_id: int, payload: dict, db: Session = Depends(get_db),
                 admin: Admin = Depends(require_super_admin)):
    from ..security import hash_password

    a = db.get(Admin, admin_id)
    if not a:
        raise HTTPException(404, "账户不存在")
    if "name" in payload:
        a.name = payload["name"]
    if payload.get("password"):
        if len(payload["password"]) < 6:
            raise HTTPException(400, "密码至少 6 位")
        a.password_hash = hash_password(payload["password"])
    if "role" in payload and a.id != admin.id:
        a.role = "admin" if payload["role"] == "admin" else "operator"
    if "status" in payload and a.id != admin.id:
        a.status = 1 if payload["status"] else 0
    db.commit()
    return {"ok": True}


@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: int, db: Session = Depends(get_db),
                 admin: Admin = Depends(require_super_admin)):
    if admin_id == admin.id:
        raise HTTPException(400, "不能删除当前登录账户")
    a = db.get(Admin, admin_id)
    if not a:
        raise HTTPException(404, "账户不存在")
    db.delete(a)
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# 客户管理
# --------------------------------------------------------------------------- #
@router.get("/customers")
def list_customers(page: int = 1, page_size: int = 50, q: str | None = None,
                   db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    from ..models import Favorite

    stmt = select(User)
    if q:
        stmt = stmt.where(User.phone.like(f"%{q.strip()}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(
        stmt.order_by(desc(User.created_at)).offset(max(page - 1, 0) * page_size).limit(page_size)
    ).scalars().all()
    items = []
    for u in rows:
        items.append({
            "id": u.id, "phone": u.phone, "email": u.email, "nickname": u.nickname,
            "status": u.status,
            "fav_count": db.execute(select(func.count(Favorite.id)).where(Favorite.user_id == u.id)).scalar() or 0,
            "quote_count": db.execute(select(func.count(Quote.id)).where(Quote.user_id == u.id)).scalar() or 0,
            "last_login_at": u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else None,
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else None,
        })
    return {"total": total, "items": items}


@router.put("/customers/{user_id}")
def update_customer(user_id: int, payload: dict, db: Session = Depends(get_db),
                    admin: Admin = Depends(current_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "客户不存在")
    if "status" in payload:
        u.status = 1 if payload["status"] else 0
    if "nickname" in payload:
        u.nickname = payload["nickname"]
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# 报价单管理
# --------------------------------------------------------------------------- #
@router.get("/quotes")
def list_quotes(page: int = 1, page_size: int = 50, q: str | None = None,
                db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    from sqlalchemy.orm import selectinload

    stmt = select(Quote).options(selectinload(Quote.items))
    if q:
        stmt = stmt.where(Quote.quote_no.like(f"%{q.strip()}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(
        stmt.order_by(desc(Quote.created_at)).offset(max(page - 1, 0) * page_size).limit(page_size)
    ).scalars().all()
    from .quotes import _quote_dict

    return {"total": total, "items": [_quote_dict(x) for x in rows]}


@router.post("/quotes/{quote_id}/cancel")
def cancel_quote(quote_id: int, db: Session = Depends(get_db),
                 admin: Admin = Depends(current_admin)):
    q = db.get(Quote, quote_id)
    if not q:
        raise HTTPException(404, "报价单不存在")
    q.status = "cancelled"
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# 动态列管理（供后台「列设置」抽屉使用）
# --------------------------------------------------------------------------- #
@router.get("/columns")
def admin_columns(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    rows = db.execute(select(TrademarkColumn).order_by(TrademarkColumn.sort)).scalars().all()
    return {"items": [{
        "key": c.key, "label": c.label, "kind": c.kind, "data_type": c.data_type,
        "sort": c.sort, "visible": bool(c.visible), "filled_count": c.filled_count,
        "first_seen_file": c.first_seen_file,
    } for c in rows]}


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    rows = db.execute(
        select(Notification).order_by(desc(Notification.created_at)).limit(50)
    ).scalars().all()
    return {"items": [{
        "id": n.id, "type": n.type, "title": n.title, "content": n.content,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else None,
    } for n in rows]}