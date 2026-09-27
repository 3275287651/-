# -*- coding: utf-8 -*-
"""端到端验证：真实 Excel → 解析 → 列识别 → 落库 → 唯一编号/商标编号/金额校验 → 批量操作。

⚠️ 仅用于开发环境自测！脚本会：
   - 把两个真实 Excel 重新走一遍导入（重复数据按商标编号跳过，不产生重复记录）
   - 修改最新 3 条记录的价格与上下架状态
请勿在生产库上运行。
"""
import io
import json
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
F935 = r"c:\Users\32752\Desktop\SBJYWZ\-\商标-29类+31类+35类-935件(1).xlsx"
F554 = r"c:\Users\32752\Desktop\SBJYWZ\-\商标-3类-554件.xlsx"

s = requests.Session()


def step(title):
    print("\n" + "=" * 72)
    print("▶", title)
    print("=" * 72)


step("1. 管理员登录")
r = s.post(f"{BASE}/api/admin/auth/login", json={"username": "admin", "password": "admin888"})
r.raise_for_status()
tok = r.json()["token"]
H = {"Authorization": f"Bearer {tok}"}
print("  登录成功：", r.json()["admin"])


def upload(path):
    name = path.rsplit("\\", 1)[-1]
    with open(path, "rb") as f:
        data = f.read()
    r = s.post(f"{BASE}/api/admin/imports/upload", headers=H,
               files=[("files", (name, io.BytesIO(data),
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))])
    r.raise_for_status()
    js = r.json()
    if js.get("failed"):
        print("  上传失败：", js["failed"])
        sys.exit(1)
    return js["batches"][0]


def show_batch(b):
    print(f"  文件={b['filename']}  sheet={b['sheet_name']}")
    print(f"  数据行={b['total_rows']}  图片={b['image_count']}  列数={b['column_count']}")
    if b.get("message"):
        print("  提示：", b["message"])
    print("  列识别结果：")
    for c in b["columns"]:
        tag = c["mapped_field"] or "→动态列(extra)"
        print(f"    · {c['header']:<14} 类型={c['data_type']:<7} 有值={c['non_empty']:<5} 映射={tag}")
        if c["samples"]:
            print(f"        样例: {c['samples'][0][:50]}")


def run_flow(path, price_mode, label):
    step(label)
    b = upload(path)
    bid = b["id"]
    show_batch(b)

    step("   预览 + 自动映射")
    p = s.get(f"{BASE}/api/admin/imports/{bid}/preview", headers=H, params={"limit": 3}).json()
    print("  自动映射：")
    for k, v in p["auto_mapping"].items():
        print(f"    {k:<16} -> {v}")
    for row in p["preview_rows"][:2]:
        cells = {k: v for k, v in row["cells"].items() if v not in (None, "")}
        print(f"  行{row['excel_row']} 图片{len(row['images'])}张 {json.dumps(cells, ensure_ascii=False)[:160]}")

    step("   执行导入（后台任务 + 进度轮询）")
    r = s.post(f"{BASE}/api/admin/imports/commit", headers=H, json={
        "batch_id": bid, "mapping": p["auto_mapping"], "price_mode": price_mode,
        "status": "on_sale", "import_mode": "insert_only", "is_featured": False,
    })
    r.raise_for_status()
    t0 = time.time()
    last = -1
    while True:
        st = s.get(f"{BASE}/api/admin/imports/{bid}/status", headers=H).json()
        if st["progress"] != last:
            print(f"  进度 {st['progress']:>3}%  新增={st['success_count']} 更新={st['updated_count']} "
                  f"跳过={st['skipped_count']} 失败={st['failed_count']}")
            last = st["progress"]
        if st["status"] in ("done", "failed"):
            print(f"  结束：{st['status']}  耗时 {time.time() - t0:.1f}s")
            print("  结果：", st["message"])
            if st["errors"]:
                print("  失败清单（前5）：")
                for e in st["errors"][:5]:
                    print("   ", e)
            return st
        time.sleep(1)


run_flow(F935, "none", "2. 导入【29+31+35类 935件】—— 源表无价格列，金额应留空")
run_flow(F554, "from_file", "3. 导入【3类 554件】—— 源表有价格列，金额应自动关联")

step("4. 列表接口：双编号 / 金额 / 动态列")
r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"page_size": 3, "sort_by": "created_at", "sort_dir": "desc"})
js = r.json()
print("  总数：", js["total"])
print("  动态列定义：")
for c in js["columns"]:
    print(f"    · {c['label']:<10} key={c['key']:<22} kind={c['kind']:<6} 有值={c['filled_count']}")
print("  样本记录：")
for it in js["items"]:
    print(f"    唯一编号={it['serial_no']}  商标编号={it['trademark_no']}  名称={it['name']}  "
          f"类别={it['category']}  金额={it['price']}  有价={it['has_price']}  图片={len(it['images'])}张")

step("5. 检索：按唯一编号 / 按商标编号")
first = js["items"][0]
for param in ({"q": first["serial_no"]}, {"q": first["trademark_no"]}, {"q": first["name"]}):
    r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={**param, "page_size": 2})
    d = r.json()
    print(f"  检索 {list(param.values())[0][:24]:<26} 命中 {d['total']} 条  提示={d.get('hints')}")

step("6. 筛选：未定价 / 有价")
for state in ("unset", "set"):
    r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"price_state": state, "page_size": 1})
    print(f"  price_state={state:<6} 命中 {r.json()['total']} 条")

step("7. 批量操作：上架 / 下架 / 改价 / 按比例调价")
ids = [i["id"] for i in js["items"]]
for action, extra in [
    ("off_shelf", {}), ("on_shelf", {}),
    ("set_price", {"price": 2880}),
    ("adjust_price", {"adjust_mode": "percent", "adjust_value": 10}),
]:
    r = s.post(f"{BASE}/api/admin/trademarks/batch", headers=H,
               json={"action": action, "ids": ids, **extra})
    print(f"  {action:<14} -> {r.json().get('affected')} 条  {json.dumps(r.json().get('detail', {}), ensure_ascii=False)[:110]}")

step("8. 校验批量改价结果")
for tid in ids[:3]:
    r = s.get(f"{BASE}/api/admin/trademarks/{tid}", headers=H).json()
    print(f"    {r['serial_no']}  {r['trademark_no']}  金额={r['price']}")

step("9. 导出 Excel")
both = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"page_size": 100}).json()["items"]
r = s.post(f"{BASE}/api/admin/trademarks/export", headers=H, json={"ids": [i["id"] for i in both], "include_images": "url"})
ok = r.status_code == 200 and len(r.content) > 3000
print(f"  导出状态={r.status_code}  字节={len(r.content)}  {'OK' if ok else 'FAILED'}")
if ok:
    out = r"C:\Users\32752\Desktop\SBJYWZ\-\_export_check.xlsx"
    open(out, "wb").write(r.content)
    print("  已保存：", out)

step("10. 图片静态访问")
img = js["items"][0]["images"]
if img:
    rr = s.get(f"{BASE}{img[0]['url']}")
    print(f"  {img[0]['url'][:70]}  HTTP={rr.status_code}  字节={len(rr.content)}")

step("11. 仪表盘")
d = s.get(f"{BASE}/api/admin/stats", headers=H).json()
print("  商标：", json.dumps(d["trademarks"], ensure_ascii=False))
print("  图片总数：", d["images"], " 导入批次：", d["import_batches"])
print("  类别分布：", json.dumps(d["categories"], ensure_ascii=False))
print("  价格分布：", json.dumps(d["price_dist"], ensure_ascii=False))
print("  到期提醒：", json.dumps(d["expiring"], ensure_ascii=False))

print("\n✅ 端到端验证脚本执行完毕")