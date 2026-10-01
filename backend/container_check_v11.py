# -*- coding: utf-8 -*-
"""容器实例验收：新功能是否都在，以及「新镜像 + 旧数据卷」是否自动迁移成功。"""
import io
import re
import requests
from PIL import Image

BASE = "http://127.0.0.1:8080"

print("=== 1. 服务与前端版本 ===")
h = requests.get(f"{BASE}/api/health", timeout=10).json()
home = requests.get(f"{BASE}/", timeout=10)
m = re.search(r"index-[A-Za-z0-9_\-]+\.js", home.text)
print(f"  健康={h}  首页=HTTP {home.status_code}  前端包={m.group(0) if m else '?'}")
for path in ("/sell", "/admin/login", "/admin/submissions", "/admin/content"):
    r = requests.get(f"{BASE}{path}", timeout=10)
    print(f"  SPA 路由 {path:<20} HTTP {r.status_code}")

print("\n=== 2. 登录与自动迁移 ===")
s = requests.Session()
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
print("  默认管理员登录：OK")
st = s.get(f"{BASE}/api/admin/trademarks", headers=H, params={"page_size": 1}).json()
print(f"  商标总数：{st['total']}")
if st["items"]:
    it = st["items"][0]
    print(f"  老库新列已自动补齐：来源={it['source_label']}｜审核={it['review_label']}｜"
          f"图样={len(it['designs'])}张｜商标证={len(it['certificates'])}张")

print("\n=== 3. 三项新功能接口 ===")
cfg = requests.get(f"{BASE}/api/site/config", timeout=10).json()
print(f"  favicon 字段：{'favicon_url' in cfg}｜站点名：{cfg['site_name']}"
      f"｜Cache-Control={requests.get(f'{BASE}/api/site/config').headers.get('cache-control')}")
sub = s.get(f"{BASE}/api/admin/submissions/summary", headers=H).json()
print(f"  寄售审核接口：待审核 {sub['pending']}｜累计 {sub['total']}")
con = s.get(f"{BASE}/api/admin/content/summary", headers=H).json()
print(f"  内容包接口：文件 {con['uploads']['files']} 个 / {con['uploads']['megabytes']}MB"
      f"｜格式 v{con['format_version']}")
r = s.get(f"{BASE}/api/admin/content/export", headers=H)
print(f"  导出内容包：HTTP {r.status_code}｜大小 {len(r.content)/1024:.0f} KB")

print("\n=== 4. 容器内跑一遍客户寄售全链路 ===")
rc = requests.get(f"{BASE}/api/auth/captcha", timeout=10)
key = rc.headers["x-captcha-key"]
code = "".join(re.findall(r">([A-Z0-9])</text>", rc.text))
reg = s.post(f"{BASE}/api/auth/register", json={
    "phone": "13700009999", "password": "test123456", "nickname": "容器测试客户",
    "captcha": code, "captcha_key": key})
print(f"  客户注册：HTTP {reg.status_code}")
if reg.status_code == 200:
    UH = {"Authorization": f"Bearer {reg.json()['token']}"}
    img = io.BytesIO(); Image.new("RGB", (80, 80), (15, 105, 161)).save(img, "PNG")
    d = s.post(f"{BASE}/api/submissions/upload", headers=UH,
               files={"file": ("d.png", img.getvalue(), "image/png")}).json()
    img2 = io.BytesIO(); Image.new("RGB", (80, 80), (180, 83, 9)).save(img2, "PNG")
    c = s.post(f"{BASE}/api/submissions/upload", headers=UH,
               files={"file": ("c.png", img2.getvalue(), "image/png")}).json()
    sub2 = s.post(f"{BASE}/api/submissions", headers=UH, json={
        "name": "容器寄售测试标", "category": 35, "trademark_no": "8888888888",
        "price": 5200, "contact_name": "李老板", "contact_phone": "13700009999",
        "design_images": [d["url"]], "certificates": [c["url"]]})
    print(f"  提交寄售：HTTP {sub2.status_code}")
    if sub2.status_code == 200:
        sd = sub2.json()["submission"]
        print(f"    唯一编号={sd['serial_no']}｜商标编号={sd['trademark_no']}｜"
              f"{sd['review_label']}｜图样{len(sd['designs'])}张｜商标证{len(sd['certificates'])}张")
        pv = requests.get(f"{BASE}/api/trademarks/{sd['id']}")
        print(f"    审核前前台可见性：HTTP {pv.status_code}（期望 404）")
        rv = s.post(f"{BASE}/api/admin/submissions/{sd['id']}/review", headers=H,
                    json={"action": "approve", "status": "on_sale"}).json()
        print(f"    审核通过：{rv['submission']['review_label']}｜状态={rv['submission']['status']}")
        pv2 = requests.get(f"{BASE}/api/trademarks/{sd['id']}")
        d2 = pv2.json()["trademark"]
        print(f"    审核后前台可见性：HTTP {pv2.status_code}｜{d2['name']}｜{d2['price_text']}")
        print(f"    商标证是否泄露到前台：{c['url'] in pv2.text}")
        s.delete(f"{BASE}/api/admin/trademarks/{sd['id']}", headers=H)
        print("    已清理容器内测试数据")

print("\n=== 5. 数据卷 ===")
print(f"  容器数据卷商标数：{s.get(f'{BASE}/api/admin/trademarks', headers=H, params={'page_size': 1}).json()['total']}")
print("\n✅ 容器验收完毕")