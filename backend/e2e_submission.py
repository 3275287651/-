# -*- coding: utf-8 -*-
"""验证新增能力：
A. 客户寄售：注册客户 → 上传图样+商标证 → 提交 → 审核通过 → 前台可见（商标证不公开）
B. 内容包：导出 ZIP → 重新导入 → 数据行数一致
"""
import io
import json
import re
import sys
import time

import requests
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8000"
s = requests.Session()


def step(t):
    print("\n" + "=" * 70)
    print("▶", t)
    print("=" * 70)


def png(text, color):
    img = Image.new("RGB", (200, 200), color)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 190, 190], outline=(255, 255, 255), width=4)
    d.text((60, 90), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
step("A1. 管理员登录")
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
AH = {"Authorization": f"Bearer {tok}"}
print("   OK")

step("A2. 客户注册（含图形验证码——从 SVG 中解析出字符，验证验证码链路）")
r = s.get(f"{BASE}/api/auth/captcha")
key = r.headers.get("x-captcha-key")
chars = re.findall(r">([A-Z0-9])</text>", r.text)
code = "".join(chars)
print(f"   验证码 key={key[:8]}… 识别字符={code}")
phone = f"139{int(time.time()) % 100000000:08d}"
reg = s.post(f"{BASE}/api/auth/register", json={
    "phone": phone, "password": "test123456", "nickname": "寄售测试客户",
    "captcha": code, "captcha_key": key,
})
print(f"   注册 HTTP {reg.status_code}", reg.json().get("user") or reg.json())
if reg.status_code != 200:
    sys.exit(1)
UH = {"Authorization": f"Bearer {reg.json()['token']}"}

step("A3. 客户上传商标图样与商标证（两份独立材料）")
up1 = s.post(f"{BASE}/api/submissions/upload", headers=UH,
             files={"file": ("design.png", png("LOGO", (15, 105, 161)), "image/png")}).json()
up2 = s.post(f"{BASE}/api/submissions/upload", headers=UH,
             files={"file": ("cert.png", png("CERT", (180, 83, 9)), "image/png")}).json()
print("   图样：", up1["url"])
print("   商标证：", up2["url"])

step("A4. 提交寄售（客户自定价）")
sub = s.post(f"{BASE}/api/submissions", headers=UH, json={
    "name": "寄售测试标", "category": 29, "trademark_no": f"999{int(time.time()) % 100000000:08d}",
    "registration_date": "2023-06-18", "groups": "2901；2902",
    "products": "加工过的坚果；肉；蛋", "price": 6600,
    "contact_name": "王老板", "contact_phone": phone,
    "remark": "同名多类:29;30;", "design_images": [up1["url"]], "certificates": [up2["url"]],
})
print(f"   HTTP {sub.status_code}")
if sub.status_code != 200:
    print(sub.text[:400]); sys.exit(1)
sd = sub.json()["submission"]
sid = sd["id"]
print(f"   唯一编号={sd['serial_no']}  商标编号={sd['trademark_no']}")
print(f"   期望售价={sd['price']}  审核={sd['review_label']}  状态={sd['status']}  来源={sd['source_label']}")
print(f"   图样={len(sd['designs'])}张  商标证={len(sd['certificates'])}张")
print("   提示：", sub.json()["message"])

step("A5. 重复提交同一商标编号（应被拦截并给出提示）")
dup = s.post(f"{BASE}/api/submissions", headers=UH, json={
    "name": "重复标", "category": 29, "trademark_no": sd["trademark_no"], "price": 100,
    "contact_name": "王老板", "contact_phone": phone,
    "design_images": [up1["url"]], "certificates": [up2["url"]],
})
print(f"   HTTP {dup.status_code}  提示：{dup.json().get('detail')}")

step("A6. 审核前：前台是否可见（应为不可见）")
pub = requests.get(f"{BASE}/api/trademarks/{sid}")
print(f"   详情接口 HTTP {pub.status_code}（期望 404）")
lst = requests.get(f"{BASE}/api/trademarks", params={"q": "寄售测试标"}).json()
print(f"   列表检索命中 {lst['total']} 条（期望 0）")

step("A7. 客户查看自己的提交")
mine = s.get(f"{BASE}/api/submissions/mine", headers=UH).json()
print(f"   共 {mine['counts']['total']} 条｜待审核 {mine['counts']['pending']}")
for it in mine["items"]:
    print(f"   · {it['name']} {it['review_label']} 商标证{len(it['certificates'])}张")

step("A8. 后台审核列表与汇总")
sumr = s.get(f"{BASE}/api/admin/submissions/summary", headers=AH).json()
print("   汇总：", {k: v for k, v in sumr.items() if k != "labels"})
pend = s.get(f"{BASE}/api/admin/submissions", headers=AH, params={"status": "pending"}).json()
print(f"   待审核列表 {pend['total']} 条")
item = next((x for x in pend["items"] if x["id"] == sid), None)
print("   含提交人信息：", item["submitter"] if item else "未找到")
print("   含商标证：", len(item["certificates"]) if item else 0, "张")

step("A9. 审核通过（调价 7200 并上架）")
rv = s.post(f"{BASE}/api/admin/submissions/{sid}/review", headers=AH,
            json={"action": "approve", "price": 7200, "status": "on_sale",
                  "remark": "材料齐全，已核实权属"}).json()
print(f"   审核={rv['submission']['review_label']}  售价={rv['submission']['price']}  状态={rv['submission']['status']}")

step("A10. 审核后：前台可见性 + 商标证是否泄露")
pub2 = requests.get(f"{BASE}/api/trademarks/{sid}")
print(f"   详情接口 HTTP {pub2.status_code}（期望 200）")
if pub2.status_code == 200:
    d = pub2.json()["trademark"]
    print(f"   {d['name']}｜{d['price_text']}｜图样 {len(d['images'])} 张")
    print("   前台响应中是否含商标证 URL：", up2["url"] in json.dumps(pub2.json()))
home = requests.get(f"{BASE}/api/site/home").json()
print(f"   首页在售数：{home['stats']['on_sale']}")

step("A11. 内容包：导出")
r = s.get(f"{BASE}/api/admin/content/export", headers=AH)
print(f"   HTTP {r.status_code}  大小 {len(r.content)/1024:.0f} KB")
zip_bytes = r.content
open(r"c:\Users\32752\Desktop\SBJYWZ\-\backend\_content_test.zip", "wb").write(zip_bytes)

sm = s.get(f"{BASE}/api/admin/content/summary", headers=AH).json()
before = sm["counts"]
print("   导出前各表行数：", {k: v for k, v in before.items() if v})

step("A12. 内容包：重新导入（整体覆盖）")
r = s.post(f"{BASE}/api/admin/content/import", headers=AH,
           files={"file": ("content.zip", io.BytesIO(zip_bytes), "application/zip")},
           params={"mode": "replace", "include_uploads": "true"})
print(f"   HTTP {r.status_code}")
if r.status_code != 200:
    print(r.text[:500]); sys.exit(1)
res = r.json()
print("   恢复行数：", {k: v for k, v in res["tables"].items() if v})
print("   恢复文件：", res["upload_files"], "个")
print("   提示：", res["message"])

step("A13. 导入后校验")
sm2 = s.get(f"{BASE}/api/admin/content/summary", headers=AH).json()
after = sm2["counts"]
same = all(after.get(k) == v for k, v in before.items())
print("   各表行数与导出前一致：", same)
if not same:
    for k, v in before.items():
        if after.get(k) != v:
            print(f"    差异 {k}: 导出前 {v} → 导入后 {after.get(k)}")
print("   登录态是否仍然有效（运营账户未被覆盖）：", s.get(f"{BASE}/api/admin/auth/me", headers=AH).status_code == 200)
lst2 = requests.get(f"{BASE}/api/trademarks", params={"q": "寄售测试标"}).json()
print(f"   前台检索到寄售标 {lst2['total']} 条")

step("A14. 清理测试数据")
d = s.delete(f"{BASE}/api/admin/trademarks/{sid}", headers=AH)
print(f"   删除测试商品 HTTP {d.status_code}")
print("\n✅ 验证完毕")