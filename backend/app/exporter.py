"""导出引擎：把商标导出为 xlsx。

导出表头顺序刻意把「唯一编号」与「商标编号」放在最前两列，并加注释行说明语义差异，
避免运营把两个编号混用。图片支持：url（默认，轻量）/ embed（嵌入单元格）/ none。
"""
from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import MEDIA_URL, UPLOAD_DIR
from .models import STATUS_LABELS, Trademark

HEADERS = [
    ("serial_no", "唯一编号", 22),
    ("trademark_no", "商标编号", 24),
    ("name", "商标名", 14),
    ("category", "类别", 8),
    ("price", "金额(元)", 12),
    ("status_label", "状态", 10),
    ("registration_date", "注册日期", 12),
    ("expiry_date", "有效期至", 12),
    ("application_count", "申请量", 9),
    ("groups", "群组", 28),
    ("products", "产品/服务", 46),
    ("legal_status", "法律状态", 12),
    ("ai_description", "AI释义", 40),
    ("remark", "备注", 22),
    ("source_file", "来源文件", 22),
]
HEAD_FILL = PatternFill("solid", fgColor="0F172A")
HEAD_FONT = Font(color="FFFFFF", bold=True, size=11)


def _val(tm: Trademark, key: str):
    if key == "status_label":
        return STATUS_LABELS.get(tm.status, tm.status)
    if key == "price":
        return float(tm.price) if tm.price is not None else None
    if key in ("registration_date", "expiry_date"):
        v = getattr(tm, key)
        return v.isoformat()[:10] if isinstance(v, (date, datetime)) else None
    return getattr(tm, key, None)


def build_export(rows: list[Trademark], columns: list[str] | None = None,
                 include_images: str = "url") -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "商标列表"

    headers = [h for h in HEADERS if columns is None or h[0] in columns]
    if columns and "serial_no" not in columns:
        headers = [HEADERS[0]] + headers          # 唯一编号永远导出
    if columns and "trademark_no" not in columns:
        headers = [HEADERS[0], HEADERS[1]] + [h for h in headers if h[0] != "serial_no"]

    # 动态列（Excel 里带进来、系统未预置的列）
    extra_labels: list[str] = []
    for tm in rows:
        for k in (tm.extra or {}).keys():
            if k not in extra_labels:
                extra_labels.append(k)

    image_mode = include_images
    col_defs = list(headers)
    if image_mode == "url":
        col_defs.insert(0, ("__img_url", "图样链接", 30))
    elif image_mode == "embed":
        col_defs.insert(0, ("__img", "图样", 14))
    col_defs += [(f"__extra__{label}", label, 16) for label in extra_labels]
    col_defs += [("__serial_note", "编号说明", 34)]

    for i, (_, label, width) in enumerate(col_defs, start=1):
        c = ws.cell(row=1, column=i, value=label)
        c.fill = HEAD_FILL
        c.font = HEAD_FONT
        c.alignment = Alignment(vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"

    for ri, tm in enumerate(rows, start=2):
        designs = [im for im in (tm.images or []) if (im.kind or "design") == "design"]
        for ci, (key, _, _) in enumerate(col_defs, start=1):
            if key == "__img_url":
                urls = [im.url for im in designs]
                ws.cell(row=ri, column=ci, value=";".join(urls) if urls else None)
            elif key == "__img":
                continue
            elif key == "__serial_note":
                ws.cell(row=ri, column=ci,
                        value="唯一编号=系统生成；商标编号=官方注册号")
            elif key.startswith("__extra__"):
                label = key[len("__extra__"):]
                ws.cell(row=ri, column=ci, value=(tm.extra or {}).get(label))
            else:
                v = _val(tm, key)
                cell = ws.cell(row=ri, column=ci, value=v)
                if key == "price" and v is not None:
                    cell.number_format = "#,##0.00"
                if key in ("serial_no", "trademark_no"):
                    cell.number_format = "@"   # 强制文本，防科学计数法
        if image_mode == "embed" and designs:
            _embed_image(ws, ri, col_defs, designs[0].url)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _embed_image(ws, row_idx: int, col_defs: list, url: str) -> None:
    from openpyxl.drawing.image import Image as XLImage

    rel = url.replace(MEDIA_URL, "", 1).lstrip("/")
    path: Path = UPLOAD_DIR / rel
    if not path.exists():
        return
    col_idx = next((i for i, (k, _, _) in enumerate(col_defs, start=1) if k == "__img"), None)
    if not col_idx:
        return
    try:
        img = XLImage(str(path))
        img.width, img.height = 56, 56
        ws.row_dimensions[row_idx].height = 46
        ws.add_image(img, f"{get_column_letter(col_idx)}{row_idx}")
    except Exception:
        return