# -*- coding: utf-8 -*-
"""动态列 + 去重 + 更新模式 验证。

构造一个含「系统不认识的自定义列」的 Excel（货主 / 成本价 / 摆位），
验证：自定义列被识别为 extra、落库后在列表接口中自动成为表格列、去重与覆盖更新行为正确。

⚠️ 仅用于开发环境自测！会在项目根目录生成 `_test_extra_columns.xlsx`，
   并向数据库写入 3 条测试商标（云测标A/B/C）。请勿在生产库上运行。
"""
import io
import json
import time

import requests
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8000"
TEST_XLSX = r"c:\Users\32752\Desktop\SBJYWZ\-\_test_extra_columns.xlsx"


def build_test_file(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "测试自定义列"
    headers = ["序号", "图样", "商标名", "类别", "货主", "成本价", "摆位", "商标编号", "备注"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=1, column=i, value=h)
    rows = [
        (1, "云测标A", 29, "张三", 800, "A区-01", "999000000000000001", "同名多类:29;30;"),
        (2, "云测标B", 31, "李四", 1200, "A区-02", "999000000000000002", ""),
        (3, "云测标C", 35, "张三", 1500, "B区-07", "999000000000000003", "待续展"),
    ]
    for ri, r in enumerate(rows, start=2):
        ws.cell(row=ri, column=1, value=r[0])
        ws.cell(row=ri, column=3, value=r[1])
        ws.cell(row=ri, column=4, value=r[2])
        ws.cell(row=ri, column=5, value=r[3])
        ws.cell(row=ri, column=6, value=r[4])
        ws.cell(row=ri, column=7, value=r[5])
        c = ws.cell(row=ri, column=8, value=r[6])
        c.number_format = "@"
        ws.cell(row=ri, column=9, value=r[7])
        # 生成一张纯色小图当作商标图样，插到 B 列对应行
        img = Image.new("RGB", (60, 60), (15 + ri * 12, 105, 161))
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, 52, 52], outline=(255, 255, 255), width=3)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        ws.add_image(XLImage(buf), f"B{ri}")
    ws.column_dimensions["H"].width = 24
    wb.save(path)
    print(f"  已生成测试文件：{path}（3 行 + 3 张嵌入图 + 3 个自定义列）")


def step(t):
    print("\n" + "=" * 72)
    print("▶", t)
    print("=" * 72)


s = requests.Session()
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}

step("1. 生成含自定义列的测试 Excel")
build_test_file(TEST_XLSX)

step("2. 上传并检查列识别（自定义列应落为 extra）")
with open(TEST_XLSX, "rb") as f:
    data = f.read()
r = s.post(f"{BASE}/api/admin/imports/upload", headers=H,
           files=[("files", ("_test_extra_columns.xlsx", io.BytesIO(data),
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))])
js = r.json()
if js.get("failed"):
    print("  上传失败：", js["failed"]); raise SystemExit(1)
b = js["batches"][0]
bid = b["id"]
print(f"  行数={b['total_rows']} 图片={b['image_count']} 列数={b['column_count']}")
for c in b["columns"]:
    print(f"    · {c['header']:<10} 类型={c['data_type']:<7} 映射={c['mapped_field'] or '★动态列'}")

step("3. 提交导入（金额跟随源表 / 默认下架）")
p = s.get(f"{BASE}/api/admin/imports/{bid}/preview", headers=H).json()
print("  自动映射：", json.dumps(p["auto_mapping"], ensure_ascii=False))
s.post(f"{BASE}/api/admin/imports/commit", headers=H, json={
    "batch_id": bid, "mapping": p["auto_mapping"], "price_mode": "none",
    "status": "off_shelf", "import_mode": "insert_only",
}).raise_for_status()
while True:
    st = s.get(f"{BASE}/api/admin/imports/{bid}/status", headers=H).json()
    if st["status"] in ("done", "failed"):
        print("  结果：", st["status"], st["message"]); break
    time.sleep(1)

step("4. 列表接口是否自动出现这些自定义列")
r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"q": "云测标", "page_size": 5}).json()
print("  命中：", r["total"])
print("  列定义（含动态列）：")
for c in r["columns"]:
    star = "★" if c["kind"] == "extra" else " "
    print(f"   {star} {c['label']:<10} kind={c['kind']:<6} 有值={c['filled_count']}")
print("  记录中的动态列数据：")
for it in r["items"]:
    print(f"    {it['serial_no']}  {it['trademark_no']}  {it['name']}  金额={it['price']}  "
          f"extra={json.dumps(it['extra'], ensure_ascii=False)}  图片={len(it['images'])}")

step("5. 重复导入：insert_only 应全部跳过")
r2 = s.post(f"{BASE}/api/admin/imports/upload", headers=H,
            files=[("files", ("_test_extra_columns.xlsx", io.BytesIO(data),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))])
bid2 = r2.json()["batches"][0]["id"]
p2 = s.get(f"{BASE}/api/admin/imports/{bid2}/preview", headers=H).json()
s.post(f"{BASE}/api/admin/imports/commit", headers=H, json={
    "batch_id": bid2, "mapping": p2["auto_mapping"], "price_mode": "none",
    "status": "off_shelf", "import_mode": "insert_only",
}).raise_for_status()
while True:
    st2 = s.get(f"{BASE}/api/admin/imports/{bid2}/status", headers=H).json()
    if st2["status"] in ("done", "failed"):
        print("  结果：", st2["message"])
        for e in st2["errors"][:3]:
            print("    跳过原因：", e["reason"])
        break
    time.sleep(1)

step("6. 覆盖更新模式 + 统一价 1999（upsert）")
r3 = s.post(f"{BASE}/api/admin/imports/upload", headers=H,
            files=[("files", ("_test_extra_columns.xlsx", io.BytesIO(data),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))])
bid3 = r3.json()["batches"][0]["id"]
p3 = s.get(f"{BASE}/api/admin/imports/{bid3}/preview", headers=H).json()
s.post(f"{BASE}/api/admin/imports/commit", headers=H, json={
    "batch_id": bid3, "mapping": p3["auto_mapping"], "price_mode": "fixed",
    "fixed_price": 1999, "status": "on_sale", "import_mode": "upsert",
}).raise_for_status()
while True:
    st3 = s.get(f"{BASE}/api/admin/imports/{bid3}/status", headers=H).json()
    if st3["status"] in ("done", "failed"):
        print("  结果：", st3["message"]); break
    time.sleep(1)
r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"q": "云测标", "page_size": 5}).json()
for it in r["items"]:
    print(f"    {it['serial_no']}（唯一编号未变） 金额={it['price']} 状态={it['status']} "
          f"图片={len(it['images'])} 来源行={it['source_row']}")

step("7. 批次历史 / 清理")
h = s.get(f"{BASE}/api/admin/imports/history", headers=H).json()
for b2 in h["items"][:5]:
    print(f"    批次{b2['id']:<3} {b2['filename'][:34]:<36} {b2['status']:<8} "
          f"新增{b2['success_count']}/更新{b2['updated_count']}/跳过{b2['skipped_count']} 列{b2['column_count']}")

print("\n✅ 动态列验证完毕")