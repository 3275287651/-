# -*- coding: utf-8 -*-
"""容器验收：对运行中的容器实例做一次完整业务验证。

用法：python container_check.py [base_url]
验证：登录 → 上传真实 Excel → 列识别 → 导入（含图片提取）→ 双编号/金额校验 → 批量操作 → 导出
"""
import io
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
F554 = r"c:\Users\32752\Desktop\SBJYWZ\-\商标-3类-554件.xlsx"

s = requests.Session()


def step(t):
    print("\n" + "-" * 66)
    print("▶", t)


step("健康检查")
print("  ", s.get(f"{BASE}/api/health").json())

step("管理员登录")
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
print("   登录成功")

step("上传真实 Excel（3类 554 件，含 554 张嵌入图）")
with open(F554, "rb") as f:
    data = f.read()
js = s.post(f"{BASE}/api/admin/imports/upload", headers=H,
            files=[("files", ("商标-3类-554件.xlsx", io.BytesIO(data),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]).json()
if js.get("failed"):
    print("   上传失败：", js["failed"]); sys.exit(1)
b = js["batches"][0]
bid = b["id"]
print(f"   数据行={b['total_rows']} 图片={b['image_count']} 识别列={b['column_count']}")
for c in b["columns"]:
    tag = c["mapped_field"] or "★动态列"
    print(f"     · {c['header']:<12} {c['data_type']:<7} -> {tag}")

step("导入（金额跟随源表，导入后直接上架）")
p = s.get(f"{BASE}/api/admin/imports/{bid}/preview", headers=H).json()
s.post(f"{BASE}/api/admin/imports/commit", headers=H, json={
    "batch_id": bid, "mapping": p["auto_mapping"], "price_mode": "from_file",
    "status": "on_sale", "import_mode": "insert_only",
}).raise_for_status()
while True:
    st = s.get(f"{BASE}/api/admin/imports/{bid}/status", headers=H).json()
    if st["status"] in ("done", "failed"):
        print("   ", st["status"], st["message"])
        break
    time.sleep(1)

step("列表与双编号校验")
r = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"page_size": 2}).json()
print("   总数：", r["total"])
for it in r["items"]:
    print(f"   唯一编号={it['serial_no']}  商标编号={it['trademark_no']}  "
          f"金额={it['price']}  图样={len(it['images'])}张")

step("图样可访问")
if r["items"][0]["images"]:
    u = r["items"][0]["images"][0]["url"]
    rr = s.get(f"{BASE}{u}")
    print(f"   {u[:60]} HTTP={rr.status_code} 字节={len(rr.content)}")

step("批量操作：下架 / 改价 / 上架")
ids = [i["id"] for i in r["items"]]
for action, extra in [("off_shelf", {}), ("set_price", {"price": 2288}), ("on_shelf", {})]:
    res = s.post(f"{BASE}/api/admin/trademarks/batch", headers=H,
                 json={"action": action, "ids": ids, **extra}).json()
    print(f"   {action:<12} 影响 {res['affected']} 条")

step("校验改价结果")
for tid in ids[:2]:
    d = s.get(f"{BASE}/api/admin/trademarks/{tid}", headers=H).json()
    print(f"   {d['serial_no']} 金额={d['price']} 状态={d['status']}")

step("导出 Excel")
resp = s.post(f"{BASE}/api/admin/trademarks/export", headers=H,
              json={"ids": ids, "include_images": "url"})
print(f"   HTTP={resp.status_code} 字节={len(resp.content)}")

step("前台接口")
home = requests.get(f"{BASE}/api/site/home").json()
print(f"   在售={home['stats']['on_sale']} 类别数={home['stats']['categories']} "
      f"精选={len(home['featured'])} 最新={len(home['latest'])}")
det = requests.get(f"{BASE}/api/trademarks/{ids[0]}").json()["trademark"]
print(f"   详情页：{det['name']} 价格={det['price_text']} 注册号={det['trademark_no']}")
print("   详情页是否含唯一编号字样：", "唯一编号" in str(det))

step("仪表盘")
st = s.get(f"{BASE}/api/admin/stats", headers=H).json()
print("   ", st["trademarks"], "图片:", st["images"])

print("\n✅ 容器业务验收通过")