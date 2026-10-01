"""客户寄售（C2B2C）：客户上传商标 → 自定价 → 后台审核 → 上架销售。

设计要点：
- 复用 trademarks 表（加 source_type='customer' + review_status），审核通过后即为正式在售商品，
  不再复制一份数据，避免两处不一致；前台所有查询都强制 review_status=='approved'。
- 「商标图样」与「商标证」是两类不同材料：分别存在 trademark_images.kind = design / certificate。
  商标证仅后台与提交人可见，前台绝不公开。
- 客户提交时即分配系统「唯一编号」（TM-YYYYMMDD-NNNN），与商标编号互不干扰。
"""
from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import current_admin, current_user
from ..models import (
    Admin, IMAGE_KIND_LABELS, Notification, OperationLog, REVIEW_LABELS, SOURCE_LABELS,
    Trademark, TrademarkImage, User,
)
from ..schemas import SubmissionIn, SubmissionReviewIn
from ..serial import next_serial
from .trademarks import serialize_tm

router = APIRouter(tags=["submissions"])


# --------------------------------------------------------------------------- #
# 客户侧
# --------------------------------------------------------------------------- #
def _validate(p: SubmissionIn) -> None:
    if not p.design_images:
        raise HTTPException(400, "请上传商标图样（logo 图片）")
    if not p.certificates:
        raise HTTPException(400, "请上传商标证（注册证扫描件或照片）")
    if p.price is None or p.price <= 0:
        raise HTTPException(400, "请填写期望售价")
    if p.category is None:
        raise HTTPException(400, "请选择商标类别")
    if not (p.contact_name or "").strip() or not (p.contact_phone or "").strip():
        raise HTTPException(400, "请填写联系人与联系电话")


def _apply_images(db: Session, tm: Trademark, designs: list[str], certificates: list[str]) -> None:
    db.query(TrademarkImage).filter(TrademarkImage.trademark_id == tm.id).delete()
    for i, url in enumerate(designs):
        db.add(TrademarkImage(trademark_id=tm.id, url=url, sort=i, is_primary=(i == 0), kind="design"))
    for i, url in enumerate(certificates):
        db.add(TrademarkImage(trademark_id=tm.id, url=url, sort=100 + i, is_primary=False,
                              kind="certificate"))


@router.post("/api/submissions/upload")
async def upload_for_submission(file: UploadFile = File(...),
                                user: User = Depends(current_user)):
    """客户侧图片上传（商标图样 / 商标证）。文件名随机化，避免被枚举。"""
    import uuid
    from pathlib import Path

    from ..config import MEDIA_URL, UPLOAD_DIR

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        raise HTTPException(400, "仅支持 png / jpg / jpeg / gif / webp 图片")
    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(400, "单张图片不能超过 8MB")
    target_dir = UPLOAD_DIR / "uploads" / "submissions"
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:16]}{ext}"
    (target_dir / name).write_bytes(raw)
    return {"ok": True, "url": f"{MEDIA_URL}/uploads/submissions/{name}", "size": len(raw)}


@router.post("/api/submissions")
def create_submission(payload: SubmissionIn, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    _validate(payload)
    trademark_no = (payload.trademark_no or "").strip() or None
    if trademark_no:
        dup = db.execute(select(Trademark).where(Trademark.trademark_no == trademark_no)).scalar_one_or_none()
        if dup:
            hint = "该商标已在你的提交中" if dup.user_id == user.id else "该商标已在本平台收录"
            raise HTTPException(
                400,
                f"商标编号 {trademark_no} 已存在（{hint}，唯一编号 {dup.serial_no}）。"
                "如果这是你的商标，请联系客服核对，无需重复提交。",
            )

    tm = Trademark(
        serial_no=next_serial(db),
        source_file="客户寄售",
        source_type="customer",
        review_status="pending",
        status="off_shelf",              # 待审核期间不可见
        user_id=user.id,
        name=payload.name.strip(),
        trademark_no=trademark_no,
        category=payload.category,
        price=round(float(payload.price), 2),
        products=payload.products,
        groups=payload.groups,
        registration_date=date.fromisoformat(payload.registration_date) if payload.registration_date else None,
        legal_status=payload.legal_status,
        ai_description=payload.ai_description,
        remark=payload.remark or "客户寄售提交",
        contact_name=(payload.contact_name or "").strip(),
        contact_phone=(payload.contact_phone or "").strip(),
    )
    if tm.registration_date and payload.expiry_date:
        tm.expiry_date = date.fromisoformat(payload.expiry_date)
    db.add(tm)
    db.flush()
    _apply_images(db, tm, payload.design_images or [], payload.certificates or [])
    db.add(Notification(
        type="submission", title=f"新的商标寄售申请：{tm.name}",
        content=(f"提交人 {user.nickname or user.phone}（{user.phone}）\n"
                 f"唯一编号 {tm.serial_no}｜商标编号 {tm.trademark_no or '—'}｜"
                 f"类别 {tm.category}类｜期望售价 ¥{tm.price:,.0f}"),
        receiver_type="admin",
    ))
    db.commit()
    return {
        "ok": True,
        "submission": serialize_tm(tm, with_detail=True),
        "message": "提交成功，平台将在 1 个工作日内完成审核",
    }


@router.get("/api/submissions/mine")
def my_submissions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Trademark).where(Trademark.user_id == user.id)
        .options(selectinload(Trademark.images)).order_by(Trademark.created_at.desc())
    ).scalars().all()
    return {
        "items": [serialize_tm(t, with_detail=True) for t in rows],
        "counts": {
            "total": len(rows),
            "pending": sum(1 for t in rows if t.review_status == "pending"),
            "approved": sum(1 for t in rows if t.review_status == "approved"),
            "rejected": sum(1 for t in rows if t.review_status == "rejected"),
        },
    }


def _own_pending(db: Session, tm_id: int, user: User) -> Trademark:
    tm = db.get(Trademark, tm_id)
    if not tm or tm.user_id != user.id:
        raise HTTPException(404, "提交记录不存在")
    return tm


@router.put("/api/submissions/{tm_id}")
def update_submission(tm_id: int, payload: SubmissionIn, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    """修改并重新提交：仅在「待审核 / 已驳回」状态可改，改完回到待审核。"""
    tm = _own_pending(db, tm_id, user)
    if tm.review_status == "approved":
        raise HTTPException(400, "已审核通过的商标不能自行修改，请联系客服")
    _validate(payload)
    tm.name = payload.name.strip()
    tm.trademark_no = (payload.trademark_no or "").strip() or None
    tm.category = payload.category
    tm.price = round(float(payload.price), 2)
    tm.products = payload.products
    tm.groups = payload.groups
    tm.registration_date = date.fromisoformat(payload.registration_date) if payload.registration_date else None
    tm.expiry_date = date.fromisoformat(payload.expiry_date) if payload.expiry_date else None
    tm.legal_status = payload.legal_status
    tm.ai_description = payload.ai_description
    tm.remark = payload.remark
    tm.contact_name = (payload.contact_name or "").strip()
    tm.contact_phone = (payload.contact_phone or "").strip()
    _apply_images(db, tm, payload.design_images or [], payload.certificates or [])
    tm.review_status = "pending"
    tm.review_remark = None
    tm.reviewed_at = None
    db.commit()
    return {"ok": True, "submission": serialize_tm(tm, with_detail=True)}


@router.delete("/api/submissions/{tm_id}")
def withdraw_submission(tm_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    tm = _own_pending(db, tm_id, user)
    if tm.review_status == "approved" and tm.status == "sold":
        raise HTTPException(400, "该商标已成交，无法撤回，请联系客服")
    db.delete(tm)
    db.commit()
    return {"ok": True, "message": "已撤回提交"}


# --------------------------------------------------------------------------- #
# 后台侧
# --------------------------------------------------------------------------- #
@router.get("/api/admin/submissions/summary")
def submissions_summary(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    rows = db.execute(
        select(Trademark.review_status, func.count(Trademark.id))
        .where(Trademark.source_type == "customer").group_by(Trademark.review_status)
    ).all()
    by_status = {s: n for s, n in rows}
    return {
        "pending": by_status.get("pending", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "total": sum(by_status.values()),
        "labels": REVIEW_LABELS,
    }


@router.get("/api/admin/submissions")
def list_submissions(
    status_filter: str | None = Query(default="pending", alias="status"),
    q: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_admin),
):
    stmt = select(Trademark).where(Trademark.source_type == "customer")
    if status_filter and status_filter != "all":
        stmt = stmt.where(Trademark.review_status == status_filter)
    if q:
        term = q.strip()
        stmt = stmt.where(Trademark.name.like(f"%{term}%")
                          | Trademark.trademark_no.like(f"%{term}%")
                          | Trademark.serial_no.like(f"%{term}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(
        stmt.options(selectinload(Trademark.images))
        .order_by(Trademark.created_at.desc())
        .offset(max(page - 1, 0) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [serialize_tm(t, with_detail=True) for t in rows],
    }


def _review_one(db: Session, tm: Trademark, action: str, remark: str | None,
                price: float | None, status: str | None, admin: Admin) -> None:
    if action == "approve":
        tm.review_status = "approved"
        tm.review_remark = remark
        if price is not None and price >= 0:
            tm.price = round(float(price), 2)
        tm.status = status or "on_sale"
        tm.reviewer_id = admin.id
        tm.reviewed_at = datetime.now()
    else:
        tm.review_status = "rejected"
        tm.review_remark = remark or "资料不符合平台要求"
        tm.status = "off_shelf"
        tm.reviewer_id = admin.id
        tm.reviewed_at = datetime.now()
    if tm.user_id:
        db.add(Notification(
            type="submission_review",
            title=("寄售审核通过：" if action == "approve" else "寄售审核未通过：") + tm.name,
            content=(tm.review_remark or ""),
            receiver_type="customer", receiver_id=tm.user_id,
        ))


@router.post("/api/admin/submissions/{tm_id}/review")
def review_submission(tm_id: int, payload: SubmissionReviewIn,
                      db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    tm = db.get(Trademark, tm_id)
    if not tm or tm.source_type != "customer":
        raise HTTPException(404, "寄售申请不存在")
    if payload.action == "reject" and not (payload.remark or "").strip():
        raise HTTPException(400, "请填写驳回原因，客户会看到这段说明")
    _review_one(db, tm, payload.action, payload.remark, payload.price, payload.status, admin)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action=f"submission_{payload.action}", target_type="trademark",
                        target_id=tm.id,
                        detail=json.dumps({"serial_no": tm.serial_no, "name": tm.name,
                                           "remark": payload.remark}, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "submission": serialize_tm(tm, with_detail=True)}


@router.post("/api/admin/submissions/batch_review")
def batch_review(payload: dict, db: Session = Depends(get_db),
                 admin: Admin = Depends(current_admin)):
    ids = payload.get("ids") or []
    action = payload.get("action")
    if not ids or action not in ("approve", "reject"):
        raise HTTPException(400, "请选择申请并指定审核动作")
    if action == "reject" and not (payload.get("remark") or "").strip():
        raise HTTPException(400, "批量驳回需要填写驳回原因")
    rows = db.execute(select(Trademark).where(Trademark.id.in_(ids),
                                              Trademark.source_type == "customer")).scalars().all()
    for tm in rows:
        _review_one(db, tm, action, payload.get("remark"), payload.get("price"),
                    payload.get("status"), admin)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action=f"submission_batch_{action}", target_type="trademark",
                        detail=json.dumps({"count": len(rows), "ids": ids[:200]}, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "affected": len(rows)}


@router.get("/api/admin/submissions/meta")
def submissions_meta(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    """审核页用的枚举字典，避免前端硬编码中文。"""
    return {
        "review_labels": REVIEW_LABELS,
        "source_labels": SOURCE_LABELS,
        "image_kind_labels": IMAGE_KIND_LABELS,
    }