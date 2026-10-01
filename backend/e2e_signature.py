# -*- coding: utf-8 -*-
"""请求签名与防重放验证（需后端以 SIGN_MODE=write 启动）。

模拟前端行为：以登录令牌为密钥，对 METHOD+PATH+TS+NONCE+sha256(body) 做 HMAC-SHA256。
逐项验证：正确签名放行、缺签名拒绝、改请求体拒绝、重放同一 nonce 拒绝、时间戳过期拒绝。
"""
import hashlib
import hmac
import json
import secrets
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
WINDOW = 300


def step(t):
    print("\n" + "=" * 70)
    print("▶", t)
    print("=" * 70)


def sign(token, method, path, ts, nonce, body_text, skip_body=False):
    digest = hashlib.sha256(b"" if skip_body else body_text.encode()).hexdigest()
    msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{digest}"
    return hmac.new(token.encode(), msg.encode(), hashlib.sha256).hexdigest()


def headers(token, method, path, body_text, ts=None, nonce=None, skip_body=False):
    ts = ts or str(int(time.time()))
    nonce = nonce or secrets.token_hex(16)
    h = {
        "Authorization": f"Bearer {token}",
        "X-TS": ts,
        "X-Nonce": nonce,
        "X-Sign": sign(token, method, path, ts, nonce, body_text, skip_body),
        "Content-Type": "application/json",
    }
    if skip_body:
        h["X-Body-Mode"] = "skip"
    return h


step("1. 登录（登录接口无需签名）")
r = requests.post(f"{BASE}/api/admin/auth/login",
                  json={"username": "admin", "password": "admin888"})
if r.status_code != 200:
    sys.exit(f"登录失败：{r.status_code} {r.text[:200]}")
token = r.json()["token"]
print("  登录成功，令牌长度：", len(token))

step("2. 正确签名 → 写操作放行")
path = "/api/admin/trademarks/batch"
body = json.dumps({"action": "clear_price", "ids": [1]}, separators=(",", ":"))
r = requests.post(f"{BASE}{path}", headers=headers(token, "POST", path, body), data=body)
print(f"  HTTP {r.status_code}  {r.text[:110]}")

step("3. 不带签名 → 拒绝 401")
r = requests.post(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}",
                                            "Content-Type": "application/json"}, data=body)
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("4. 签名正确但请求体被篡改 → 拒绝 401")
h = headers(token, "POST", path, body)
tampered = json.dumps({"action": "delete", "ids": [1]}, separators=(",", ":"))
r = requests.post(f"{BASE}{path}", headers=h, data=tampered)
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("5. 重放同一 nonce → 第二次被拒（防重放）")
fixed_nonce = secrets.token_hex(16)
h = headers(token, "POST", path, body, nonce=fixed_nonce)
r1 = requests.post(f"{BASE}{path}", headers=h, data=body)
r2 = requests.post(f"{BASE}{path}", headers=h, data=body)
print(f"  第一次 HTTP {r1.status_code}；第二次 HTTP {r2.status_code}  提示：{r2.json().get('detail')}")

step("6. 时间戳超出窗口 → 拒绝 401")
old_ts = str(int(time.time()) - WINDOW - 60)
h = headers(token, "POST", path, body, ts=old_ts)
r = requests.post(f"{BASE}{path}", headers=h, data=body)
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("7. 上传（FormData，约定空体摘要 + X-Body-Mode: skip）→ 放行")
up_path = "/api/admin/upload"
h = headers(token, "POST", up_path, "", skip_body=True)
h.pop("Content-Type", None)
png = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
r = requests.post(f"{BASE}{up_path}", headers=h,
                  files={"file": ("s.png", png, "image/png")}, params={"scene": "test"})
print(f"  HTTP {r.status_code}  {r.text[:110]}")

step("8. 登录类接口不受签名约束（无令牌也能登录）")
r = requests.post(f"{BASE}/api/admin/auth/login",
                  json={"username": "admin", "password": "admin888"})
print(f"  HTTP {r.status_code}（期望 200）")

step("9. 普通读接口 GET 不受影响（SIGN_MODE=write 只管写操作）")
r = requests.get(f"{BASE}/api/trademarks", params={"page_size": 1})
print(f"  HTTP {r.status_code}（期望 200）")

print("\n✅ 签名与防重放验证完毕")