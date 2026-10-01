# -*- coding: utf-8 -*-
"""容器 1.0.3 复测：系统与授权接口、防护姿态、寄售链路（用随机手机号避免与历史测试数据冲突）。"""
import io
import random
import re

import requests
from PIL import Image

BASE = "http://127.0.0.1:8080"
s = requests.Session()

print("=== 1. 版本与防护姿态 ===")
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
ver = s.get(f"{BASE}/api/admin/system/version", headers=H).json()
print("  版本：", ver["version"], "｜构建时间：", ver["build_time"], "｜实例：", ver["instance_id"][:12], "…")
st = s.get(f"{BASE}/api/admin/system/status", headers=H).json()
print("  限流：", st["rate_limit"]["per_min"], "/", st["rate_limit"]["login_per_min"], "每分钟")
print("  签名模式：", st["signature"]["mode"], "｜授权模块启用：", st["license"]["enabled"],
      "｜升级密钥已配置：", st["upgrade"]["key_configured"])
print("  响应头 server 是否仍暴露：", "server" in {k.lower() for k in requests.get(f"{BASE}/api/health").headers})

print("\n=== 2. 客户寄售全链路（随机手机号）===")
rc = requests.get(f"{BASE}/api/auth/captcha")
key = rc.headers["x-captcha-key"]
code = "".join(re.findall(r">([A-Z0-9])</text>", rc.text))
phone = "135" + "".join(random.choice("0123456789") for _ in range(8))
reg = s.post(f"{BASE}/api/auth/register", json={
    "phone": phone, "password": "test123456", "nickname": "容器复测客户",
    "captcha": code, "captcha_key": key})
print(f"  注册 {phone}：HTTP {reg.status_code}")
if reg.status_code != 200:
    print("  ", reg.text[:200])
else:
    UH = {"Authorization": f"Bearer {reg.json()['token']}"}
    img = io.BytesIO(); Image.new("RGB", (80, 80), (15, 105, 161)).save(img, "PNG")
    d = s.post(f"{BASE}/api/submissions/upload", headers=UH,
               files={"file": ("d.png", img.getvalue(), "image/png")}).json()
    img2 = io.BytesIO(); Image.new("RGB", (80, 80), (180, 83, 9)).save(img2, "PNG")
    c = s.post(f"{BASE}/api/submissions/upload", headers=UH,
               files={"file": ("c.png", img2.getvalue(), "image/png")}).json()
    sub = s.post(f"{BASE}/api/submissions", headers=UH, json={
        "name": "1.0.3 容器复测标", "category": 30, "trademark_no": f"77{random.randint(10**7, 10**8-1)}",
        "price": 3300, "contact_name": "复测", "contact_phone": phone,
        "design_images": [d["url"]], "certificates": [c["url"]]})
    print(f"  提交寄售：HTTP {sub.status_code}")
    if sub.status_code == 200:
        sd = sub.json()["submission"]
        print(f"    唯一编号={sd['serial_no']}｜商标编号={sd['trademark_no']}｜{sd['review_label']}")
        tm_id = sd["id"]
        before = requests.get(f"{BASE}/api/trademarks/{tm_id}").status_code
        print(f"    审核前前台可见性：HTTP {before}（期望 404）")
        rv = s.post(f"{BASE}/api/admin/submissions/{sd['id']}/review", headers=H,
                    json={"action": "approve", "status": "on_sale"}).json()
        print(f"    审核通过：{rv['submission']['review_label']}｜状态={rv['submission']['status']}")
        pv = requests.get(f"{BASE}/api/trademarks/{sd['id']}")
        print(f"    审核后可见：HTTP {pv.status_code}｜{pv.json()['trademark']['price_text']}"
              f"｜商标证泄露={c['url'] in pv.text}")
        s.delete(f"{BASE}/api/admin/trademarks/{sd['id']}", headers=H)
        print("    已清理测试数据")

print("\n=== 3. 内容包与前端路由 ===")
con = s.get(f"{BASE}/api/admin/content/summary", headers=H).json()
print("  内容包：", con["uploads"]["files"], "个文件 /", con["uploads"]["megabytes"], "MB")
for p in ("/", "/sell", "/admin/system"):
    print(f"  SPA {p:<14} HTTP {requests.get(BASE + p).status_code}")
print("\n✅ 容器 1.0.3 复测完毕")