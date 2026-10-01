"""内容包：把「内容」打包成一个 ZIP，与「镜像」解耦 —— 镜像升级与内容迁移互不影响。

包含内容
  data.json         全部业务数据（按表分区，含主键，可直接还原外键关系）
  meta.json         版本、导出时间、各表行数、文件数、数据库类型
  uploads/…         图样、商标证、Logo/Banner 等全部上传文件（保留相对路径）

不包含（属基础设施，迁移时各自独立处理）
  admins            运营登录凭据（导入端沿用自身账户，避免把人锁在门外）
  operation_logs     审计日志（外键指向 admins）
  uploads/imports/   导入解析中间产物（未完成的导入批次不随内容包迁移）
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import Boolean, Date, DateTime, Float, Numeric, func, inspect as sa_inspect, select
from sqlalchemy.orm import Session

from ..config import MEDIA_URL, UPLOAD_DIR
from ..database import get_db
from ..deps import current_admin, require_super_admin
from ..models import (
    Admin, Banner, Favorite, ImportBatch, Notification, OperationLog, Quote, QuoteItem,
    SiteSetting, Trademark, TrademarkColumn, TrademarkImage, User, VisitLog,
)
from ..settings_store import ensure_defaults, get_all

router = APIRouter(prefix="/api/admin/content", tags=["admin-content"])

FORMAT_VERSION = 1

# 导入顺序即外键依赖顺序：父表在前
CONTENT_TABLES = [
    SiteSetting, Banner, TrademarkColumn, ImportBatch, User, Trademark,
    TrademarkImage, Favorite, Quote, QuoteItem, Notification, VisitLog,
]
# 清空顺序：子表在前
DELETE_ORDER = list(reversed(CONTENT_TABLES))

# 引用了未导出表（admins）的外键，导入时置空，避免悬挂引用
DROP_ON_IMPORT = {
    "trademarks": {"reviewer_id"},
    "import_batches": {"created_by"},
}


# --------------------------------------------------------------------------- #
# 序列化
# --------------------------------------------------------------------------- #
def _encode(value, col_type):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _decode(value, col_type):
    if value is None:
        return None
    try:
        if isinstance(col_type, DateTime) and isinstance(value, str):
            return datetime.fromisoformat(value)
        if isinstance(col_type, Date) and isinstance(value, str):
            return date.fromisoformat(value)
        if isinstance(col_type, Numeric):
            return Decimal(str(value))
        if isinstance(col_type, Float) and value is not None:
            return float(value)
        if isinstance(col_type, Boolean):
            return bool(value)
    except (ValueError, TypeError):
        return value
    return value


def _dump_table(db: Session, model) -> list[dict]:
    cols = list(model.__table__.columns)
    rows = []
    for obj in db.execute(select(model)).scalars():
        item = {}
        for c in cols:
            item[c.name] = _encode(getattr(obj, c.name), c.type)
        rows.append(item)
    return rows


def _iter_upload_files() -> list[Path]:
    """收录品牌素材与商品附件；跳过导入中间产物。"""
    files: list[Path] = []
    for p in UPLOAD_DIR.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(UPLOAD_DIR).as_posix()
        if rel.startswith("imports/"):
            continue
        files.append(p)
    return files


# --------------------------------------------------------------------------- #
# 概览
# --------------------------------------------------------------------------- #
@router.get("/summary")
def content_summary(db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    counts = {m.__tablename__: db.execute(select(func.count()).select_from(m)).scalar() or 0
              for m in CONTENT_TABLES}
    files = _iter_upload_files()
    total_bytes = sum(f.stat().st_size for f in files)
    return {
        "counts": counts,
        "uploads": {"files": len(files), "bytes": total_bytes,
                    "megabytes": round(total_bytes / 1024 / 1024, 1)},
        "format_version": FORMAT_VERSION,
        "excluded": {"tables": ["admins", "operation_logs"], "paths": ["uploads/imports/"]},
    }


# --------------------------------------------------------------------------- #
# 导出
# --------------------------------------------------------------------------- #
@router.get("/export")
def export_content(db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    buf = io.BytesIO()
    counts: dict[str, int] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        data = {}
        for model in CONTENT_TABLES:
            rows = _dump_table(db, model)
            data[model.__tablename__] = rows
            counts[model.__tablename__] = len(rows)
        zf.writestr("data.json", json.dumps(data, ensure_ascii=False))

        files = _iter_upload_files()
        for p in files:
            zf.write(p, f"uploads/{p.relative_to(UPLOAD_DIR).as_posix()}")

        meta = {
            "format_version": FORMAT_VERSION,
            "site": get_all(db).get("site_name"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": admin.username,
            "tables": counts,
            "upload_files": len(files),
            "note": "内容包：不含运营账户与操作日志；镜像升级与内容迁移相互独立",
        }
        zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))

    buf.seek(0)
    filename = f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="content_export", target_type="content",
                        detail=json.dumps({"tables": counts, "files": len(files)}, ensure_ascii=False)))
    db.commit()
    from urllib.parse import quote
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# --------------------------------------------------------------------------- #
# 导入
# --------------------------------------------------------------------------- #
@router.post("/import")
async def import_content(file: UploadFile = File(...), mode: str = "replace",
                         include_uploads: bool = True,
                         db: Session = Depends(get_db),
                         admin: Admin = Depends(require_super_admin)):
    if mode != "replace":
        raise HTTPException(400, "当前仅支持 replace（清空并整体恢复）模式")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "文件为空")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "不是有效的 ZIP 文件") from exc

    names = set(zf.namelist())
    if "data.json" not in names:
        raise HTTPException(400, "内容包缺少 data.json，请使用「导出内容包」生成的文件")
    meta = json.loads(zf.read("meta.json")) if "meta.json" in names else {}
    if int(meta.get("format_version", 0)) > FORMAT_VERSION:
        raise HTTPException(400, "内容包版本高于当前系统，请先升级镜像")

    data = json.loads(zf.read("data.json"))
    restored: dict[str, int] = {}

    try:
        # 1) 清空业务数据（子表在前），保留运营账户
        for model in DELETE_ORDER:
            db.query(model).delete(synchronize_session=False)
        db.flush()

        # 2) 按外键依赖顺序写入（显式带主键，外键关系原样保留）
        for model in CONTENT_TABLES:
            rows = data.get(model.__tablename__) or []
            if not rows:
                restored[model.__tablename__] = 0
                continue
            drop = DROP_ON_IMPORT.get(model.__tablename__, set())
            objects = []
            for row in rows:
                payload = {k: v for k, v in row.items() if k not in drop}
                for col in model.__table__.columns:
                    if col.name in payload:
                        payload[col.name] = _decode(payload[col.name], col.type)
                objects.append(model(**payload))
            db.bulk_save_objects(objects)
            restored[model.__tablename__] = len(objects)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(500, f"内容恢复失败，已回滚（数据未变更）：{exc}") from exc

    # 3) 还原上传文件
    written = 0
    if include_uploads:
        for name in names:
            if not name.startswith("uploads/") or name.endswith("/"):
                continue
            rel = name[len("uploads/"):]
            target = UPLOAD_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
            written += 1

    # 4) 修复列统计与配置默认值（导入后站点配置可能来自旧版本）
    from ..importer import refresh_column_stats

    ensure_defaults(db)
    refresh_column_stats(db)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="content_import", target_type="content",
                        detail=json.dumps({"tables": restored, "files": written,
                                           "meta": meta.get("exported_at")}, ensure_ascii=False)))
    db.commit()

    return {
        "ok": True,
        "tables": restored,
        "upload_files": written,
        "source": {"site": meta.get("site"), "exported_at": meta.get("exported_at")},
        "message": "内容已恢复。若浏览器仍显示旧内容，请强制刷新一次（Ctrl+F5）。",
    }


@router.get("/browse")
def browse_uploads(page: int = 1, page_size: int = 200,
                   db: Session = Depends(get_db), admin: Admin = Depends(current_admin)):
    """列出内容包会收录的文件，便于迁移前核对。"""
    files = _iter_upload_files()
    files.sort(key=lambda p: p.stat().st_size, reverse=True)
    start = max(page - 1, 0) * page_size
    page_items = files[start:start + page_size]
    return {
        "total": len(files),
        "items": [{
            "path": f"{MEDIA_URL}/{p.relative_to(UPLOAD_DIR).as_posix()}",
            "size": p.stat().st_size,
        } for p in page_items],
    }