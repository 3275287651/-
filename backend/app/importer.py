"""导入服务：分析（不落库）→ 落库（后台任务，带进度）。

关键约定：
- 「唯一编号」在此生成（TM-YYYYMMDD-NNNN），与 Excel 的「商标编号」各自独立。
- 「金额」三态：from_file（跟随源表）/ fixed（统一价）/ none（留空）。
- 未映射到核心字段的列 → 原样写入 trademark.extra，并在动态列注册表登记。
"""
from __future__ import annotations

import json
import shutil
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import MEDIA_URL, UPLOAD_DIR
from .excel_reader import (
    CORE_LABELS, ColumnInfo, ParsedSheet, parse_csv, parse_xlsx, parsed_from_json, parsed_to_json,
)
from .models import ImportBatch, OperationLog, Trademark, TrademarkColumn, TrademarkImage
from .serial import SerialAllocator

IMPORT_ROOT = UPLOAD_DIR / "imports"
TRADEMARK_MEDIA = UPLOAD_DIR / "trademarks"

CORE_FIELDS = {
    "serial_no", "trademark_no", "name", "category", "products", "groups",
    "registration_date", "expiry_date", "legal_status", "application_count",
    "price", "ai_description", "remark",
}

CORE_COLUMN_META = [
    # (key, label, data_type, sort, 默认可见)
    ("serial_no", "唯一编号", "text", 10, True),
    ("trademark_no", "商标编号", "text", 20, True),
    ("name", "商标名", "text", 30, True),
    ("category", "类别", "number", 40, True),
    ("price", "金额", "price", 50, True),
    ("status", "状态", "text", 60, True),
    ("registration_date", "注册日期", "date", 70, True),
    ("application_count", "申请量", "number", 80, False),
    ("groups", "群组", "text", 90, False),
    ("products", "产品/服务", "text", 100, False),
    ("legal_status", "法律状态", "text", 110, False),
    ("expiry_date", "有效期至", "date", 120, False),
    ("ai_description", "AI释义", "text", 130, False),
    ("remark", "备注", "text", 140, False),
    ("images", "图样", "image", 15, True),
    ("source_file", "来源文件", "text", 900, False),
    ("source_row", "源表行号", "number", 910, False),
    ("created_at", "入库时间", "date", 920, False),
]


# --------------------------------------------------------------------------- #
# 分析阶段
# --------------------------------------------------------------------------- #
def _snapshot_path(batch_id: int) -> Path:
    return IMPORT_ROOT / str(batch_id) / "snapshot.json"


def _images_dir(batch_id: int) -> Path:
    d = TRADEMARK_MEDIA / f"batch_{batch_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _images_url_prefix(batch_id: int) -> str:
    return f"{MEDIA_URL}/trademarks/batch_{batch_id}"


def analyze_file(db: Session, stored_path: Path, batch_id: int, admin_id: int | None) -> ImportBatch:
    """解析文件 → 落盘快照 + 图片 → 生成批次记录（此时不写商标数据）。"""
    suffix = stored_path.suffix.lower()
    images_dir = _images_dir(batch_id)
    url_prefix = _images_url_prefix(batch_id)

    if suffix == ".csv":
        parsed = parse_csv(stored_path)
    elif suffix in (".xlsx", ".xlsm"):
        parsed = parse_xlsx(stored_path, images_dir, url_prefix)
    else:
        raise ValueError("暂不支持 .xls 旧格式，请在 Excel 中另存为 .xlsx 或 CSV 后重试")

    work_dir = IMPORT_ROOT / str(batch_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    _snapshot_path(batch_id).write_text(
        json.dumps(parsed_to_json(parsed), ensure_ascii=False), encoding="utf-8"
    )

    batch = db.get(ImportBatch, batch_id)
    batch.sheet_name = parsed.sheet_name
    batch.total_rows = len(parsed.rows)
    batch.image_count = sum(len(v) for v in parsed.images.values())
    batch.columns_json = [
        {
            "key": c.key,
            "header": c.header,
            "label": c.label,
            "mapped_field": c.mapped_field,
            "data_type": c.data_type,
            "samples": c.samples,
            "non_empty": c.non_empty,
        }
        for c in parsed.columns
    ]
    batch.status = "pending"
    batch.message = "；".join(parsed.warnings) if parsed.warnings else None
    db.commit()
    return batch


def analyze_upload(db: Session, stored_path: Path, original_name: str, admin_id: int | None) -> ImportBatch:
    batch = ImportBatch(
        filename=original_name,
        stored_path=str(stored_path),
        status="analyzing",
        created_by=admin_id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    try:
        return analyze_file(db, stored_path, batch.id, admin_id)
    except Exception as exc:  # noqa: BLE001
        batch.status = "failed"
        batch.message = f"解析失败：{exc}"
        db.commit()
        raise


def build_preview(db: Session, batch_id: int, limit: int = 20) -> dict:
    """给导入向导用的数据预览：列结构 + 前 N 行 + 图片缩略图。"""
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise ValueError("导入批次不存在")
    snap = _snapshot_path(batch_id)
    if not snap.exists():
        raise ValueError("解析快照已丢失，请重新上传文件")
    parsed = parsed_from_json(json.loads(snap.read_text(encoding="utf-8")))

    preview_rows: list[dict] = []
    for row in parsed.rows[:limit]:
        excel_row = row["_excel_row"]
        preview_rows.append({
            "excel_row": excel_row,
            "cells": {k: _jsonable(v) for k, v in row["_cells"].items()},
            "images": [i.rel_url for i in parsed.images.get(excel_row, [])],
        })

    return {
        "batch_id": batch.id,
        "filename": batch.filename,
        "sheet_name": parsed.sheet_name,
        "total_rows": len(parsed.rows),
        "image_count": sum(len(v) for v in parsed.images.values()),
        "columns": json.loads(json.dumps(batch.columns_json, ensure_ascii=False)),
        "warnings": parsed.warnings,
        "preview_rows": preview_rows,
    }


def _jsonable(v: Any) -> Any:
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return v


def _expected_ratio(parsed: ParsedSheet) -> dict[str, float]:
    total = max(len(parsed.rows), 1)
    ratio: dict[str, float] = {}
    for col in parsed.columns:
        cnt = 0
        for row in parsed.rows:
            v = row["_cells"].get(col.key)
            if v not in (None, ""):
                cnt += 1
        ratio[col.key] = round(cnt / total, 3)
    return ratio


def auto_mapping(parsed: ParsedSheet) -> dict[str, str]:
    """默认映射：命中的核心字段 → 字段名；其余非忽略列 → extra；图样列 → images。"""
    mapping: dict[str, str] = {}
    for col in parsed.columns:
        if col.mapped_field == "image":
            mapping[col.key] = "images"
        elif col.mapped_field:
            mapping[col.key] = col.mapped_field
        elif col.header.lower() in ("序号", "no", "id"):
            mapping[col.key] = "ignore"
        else:
            mapping[col.key] = "extra"
    return mapping


# --------------------------------------------------------------------------- #
# 落库阶段
# --------------------------------------------------------------------------- #
def run_import(batch_id: int, mapping: dict[str, str], options: dict, db_factory) -> None:
    """后台任务入口。逐行写入，实时更新进度。"""
    db: Session = db_factory()
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        db.close()
        return
    try:
        batch.status = "running"
        batch.progress = 0
        batch.mapping_json = mapping
        batch.options_json = options
        db.commit()

        snap = _snapshot_path(batch_id)
        parsed = parsed_from_json(json.loads(snap.read_text(encoding="utf-8")))

        price_mode = options.get("price_mode", "from_file")     # from_file | fixed | none
        fixed_price = options.get("fixed_price")
        default_status = options.get("status", "off_shelf")
        import_mode = options.get("import_mode", "insert_only")  # insert_only | upsert
        overwrite_images = bool(options.get("overwrite_images", True))
        is_featured = bool(options.get("is_featured", False))
        default_category = options.get("default_category")

        # 反查：核心字段 ← 源列 key（同一字段多列时以第一个为准）
        field_source: dict[str, str] = {}
        extra_keys: list[str] = []
        for key, target in mapping.items():
            if target in CORE_FIELDS and target not in field_source:
                field_source[target] = key
            elif target == "extra":
                extra_keys.append(key)

        col_by_key = {c.key: c for c in parsed.columns}
        allocator = SerialAllocator(db)
        errors: list[dict] = []
        success = updated = skipped = failed = 0
        total = len(parsed.rows)
        label_by_key = {c.key: c.label for c in parsed.columns}

        # 去重键预载：商标编号 → id；无编号行用「名称+类别」
        existing: dict[str, Trademark] = {}
        existing_by_name: dict[str, Trademark] = {}
        for tm in db.execute(select(Trademark)).scalars():
            if tm.trademark_no:
                existing[tm.trademark_no] = tm
            existing_by_name[f"{tm.name}|{tm.category or ''}"] = tm

        for idx, row in enumerate(parsed.rows, start=1):
            excel_row = row["_excel_row"]
            cells = row["_cells"]
            try:
                values: dict[str, Any] = {}
                for field_name, src_key in field_source.items():
                    if field_name == "images":
                        continue
                    values[field_name] = cells.get(src_key)

                name = (values.get("name") or "").strip() if values.get("name") else None
                trademark_no = values.get("trademark_no")
                category = values.get("category") if values.get("category") is not None else default_category

                if not name:
                    failed += 1
                    errors.append({"row": excel_row, "reason": "缺少商标名，已跳过"})
                    continue

                # 金额三态
                if price_mode == "from_file":
                    price = values.get("price")
                elif price_mode == "fixed":
                    price = fixed_price
                else:
                    price = None

                extra = {}
                for k in extra_keys:
                    v = cells.get(k)
                    if v not in (None, ""):
                        extra[label_by_key.get(k, k)] = _jsonable(v)

                hit = existing.get(trademark_no) if trademark_no else existing_by_name.get(f"{name}|{category or ''}")

                if hit is not None:
                    if import_mode == "insert_only":
                        skipped += 1
                        errors.append({
                            "row": excel_row, "reason": f"商标编号 {trademark_no or name} 已存在（唯一编号 {hit.serial_no}），已跳过",
                        })
                        continue
                    # 覆盖更新：唯一编号保持不变，绝不被重写
                    # 源表没有金额列时不覆盖已有金额，避免把人工定价清空
                    _apply_fields(hit, values, extra, price, default_status, is_featured, is_update=True)
                    hit.updated_at = datetime.now()
                    if overwrite_images and parsed.images.get(excel_row):
                        _replace_images(db, hit, parsed.images[excel_row])
                    updated += 1
                else:
                    tm = Trademark(serial_no=allocator.next(), source_file=parsed.filename,
                                   source_row=excel_row, import_batch_id=batch_id)
                    _apply_fields(tm, values, extra, price, default_status, is_featured)
                    db.add(tm)
                    db.flush()
                    if parsed.images.get(excel_row):
                        _replace_images(db, tm, parsed.images[excel_row])
                    if trademark_no:
                        existing[trademark_no] = tm
                    existing_by_name[f"{tm.name}|{tm.category or ''}"] = tm
                    success += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append({"row": excel_row, "reason": f"{type(exc).__name__}: {exc}"})

            if idx % 25 == 0 or idx == total:
                batch.progress = int(idx * 100 / max(total, 1))
                batch.success_count, batch.updated_count = success, updated
                batch.skipped_count, batch.failed_count = skipped, failed
                db.commit()

        # 重新扫描全部动态列（跨批次合并），驱动列表页列渲染
        _register_dynamic_columns(db, parsed, mapping, extra_keys, label_by_key)

        batch.status = "done"
        batch.progress = 100
        batch.success_count, batch.updated_count = success, updated
        batch.skipped_count, batch.failed_count = skipped, failed
        batch.errors_json = errors[:500]
        batch.finished_at = datetime.now()
        batch.message = (
            f"新增 {success} 条，更新 {updated} 条，跳过 {skipped} 条，失败 {failed} 条；"
            f"提取图片 {batch.image_count} 张"
        )
        db.add(OperationLog(
            admin_id=batch.created_by, action="import_commit", target_type="import_batch",
            target_id=batch_id,
            detail=json.dumps({
                "filename": batch.filename, "success": success, "updated": updated,
                "skipped": skipped, "failed": failed,
                "price_mode": price_mode, "price": fixed_price,
            }, ensure_ascii=False),
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        batch.status = "failed"
        batch.message = f"导入中断：{exc}"
        batch.errors_json = [{"row": 0, "reason": traceback.format_exc()[-1500:]}]
        db.commit()
    finally:
        db.close()


def _apply_fields(tm: Trademark, values: dict, extra: dict, price, default_status: str,
                  is_featured: bool, is_update: bool = False) -> None:
    if values.get("name"):
        tm.name = values["name"]
    if values.get("trademark_no"):
        tm.trademark_no = values["trademark_no"]
    if values.get("category") is not None:
        tm.category = values["category"]
    if values.get("products"):
        tm.products = values["products"]
    if values.get("groups"):
        tm.groups = values["groups"]
    if values.get("registration_date"):
        tm.registration_date = values["registration_date"]
        if not values.get("expiry_date"):
            d = values["registration_date"]
            tm.expiry_date = date(d.year + 10, d.month, d.day) if d else None
    if values.get("expiry_date"):
        tm.expiry_date = values["expiry_date"]
    if values.get("legal_status"):
        tm.legal_status = values["legal_status"]
    if values.get("application_count") is not None:
        tm.application_count = values["application_count"]
    if values.get("ai_description"):
        tm.ai_description = values["ai_description"]
    if values.get("remark"):
        tm.remark = values["remark"]
    # 金额：有值就关联；更新场景下无值则保留原价，不赋空
    if price is not None or not is_update:
        tm.price = price
    if extra:
        tm.extra = extra
    if tm.id is None or not tm.status:
        tm.status = default_status or "off_shelf"
    if is_featured:
        tm.is_featured = True


def _replace_images(db: Session, tm: Trademark, refs) -> None:
    if tm.id:
        db.query(TrademarkImage).filter(TrademarkImage.trademark_id == tm.id).delete()
    for i, ref in enumerate(refs):
        db.add(TrademarkImage(
            trademark_id=tm.id, url=ref.rel_url, sort=i, is_primary=(i == 0), source_row=ref.row,
        ))


def _register_dynamic_columns(db: Session, parsed: ParsedSheet, mapping: dict, extra_keys: list[str],
                              label_by_key: dict[str, str]) -> None:
    """登记核心列元数据（幂等）+ 本次新增的动态列；并刷新所有动态列的填充率。"""
    existing_cols = {c.key: c for c in db.execute(select(TrademarkColumn)).scalars()}
    dtype_by_key = {c.key: c.data_type for c in parsed.columns}
    for key, label, dtype, sort, visible in CORE_COLUMN_META:
        if key not in existing_cols:
            db.add(TrademarkColumn(key=key, label=label, kind="core", data_type=dtype,
                                   sort=sort, visible=visible))
    for key in extra_keys:
        label = label_by_key.get(key, key)
        if key not in existing_cols:
            db.add(TrademarkColumn(key=key, label=label, kind="extra",
                                   data_type=dtype_by_key.get(key, "text"), sort=500, visible=True,
                                   first_seen_file=parsed.filename))
        else:
            existing_cols[key].visible = True
    db.commit()
    refresh_column_stats(db)


def refresh_column_stats(db: Session) -> None:
    """统计每列实际有值的记录数：动态列用于自动隐藏空列，核心列用于列管理面板展示。"""
    counters: dict[str, int] = {}
    for extra in db.execute(select(Trademark.extra).where(Trademark.extra.is_not(None))).scalars():
        if not isinstance(extra, dict):
            continue
        for k, v in extra.items():
            if v not in (None, ""):
                counters[k] = counters.get(k, 0) + 1

    core_counters = {
        "name": db.execute(select(func.count(Trademark.id)).where(Trademark.name.is_not(None))).scalar() or 0,
        "trademark_no": db.execute(select(func.count(Trademark.id)).where(Trademark.trademark_no.is_not(None))).scalar() or 0,
        "serial_no": db.execute(select(func.count(Trademark.id))).scalar() or 0,
        "price": db.execute(select(func.count(Trademark.id)).where(Trademark.price.is_not(None))).scalar() or 0,
        "category": db.execute(select(func.count(Trademark.id)).where(Trademark.category.is_not(None))).scalar() or 0,
        "status": db.execute(select(func.count(Trademark.id))).scalar() or 0,
        "registration_date": db.execute(select(func.count(Trademark.id)).where(Trademark.registration_date.is_not(None))).scalar() or 0,
        "expiry_date": db.execute(select(func.count(Trademark.id)).where(Trademark.expiry_date.is_not(None))).scalar() or 0,
        "application_count": db.execute(select(func.count(Trademark.id)).where(Trademark.application_count.is_not(None))).scalar() or 0,
        "groups": db.execute(select(func.count(Trademark.id)).where(Trademark.groups.is_not(None))).scalar() or 0,
        "products": db.execute(select(func.count(Trademark.id)).where(Trademark.products.is_not(None))).scalar() or 0,
        "ai_description": db.execute(select(func.count(Trademark.id)).where(Trademark.ai_description.is_not(None))).scalar() or 0,
        "remark": db.execute(select(func.count(Trademark.id)).where(Trademark.remark.is_not(None))).scalar() or 0,
        "legal_status": db.execute(select(func.count(Trademark.id)).where(Trademark.legal_status.is_not(None))).scalar() or 0,
        "images": db.execute(select(func.count(func.distinct(TrademarkImage.trademark_id)))).scalar() or 0,
        "is_featured": db.execute(select(func.count(Trademark.id)).where(Trademark.is_featured.is_(True))).scalar() or 0,
        "source_file": db.execute(select(func.count(Trademark.id)).where(Trademark.source_file.is_not(None))).scalar() or 0,
        "source_row": db.execute(select(func.count(Trademark.id)).where(Trademark.source_row.is_not(None))).scalar() or 0,
        "created_at": db.execute(select(func.count(Trademark.id))).scalar() or 0,
    }
    for col in db.execute(select(TrademarkColumn)).scalars():
        if col.kind == "extra":
            col.filled_count = counters.get(col.label, 0)
        else:
            col.filled_count = core_counters.get(col.key, 0)
    db.commit()


def cleanup_batch_files(batch_id: int, keep_images: bool = True) -> None:
    """删除快照与原始上传文件；图片默认保留（已入库引用）。"""
    work_dir = IMPORT_ROOT / str(batch_id)
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    if not keep_images:
        shutil.rmtree(TRADEMARK_MEDIA / f"batch_{batch_id}", ignore_errors=True)