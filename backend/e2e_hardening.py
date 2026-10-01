# -*- coding: utf-8 -*-
"""验证纵深防护与「系统与授权」：限流、授权码（签发/篡改/过期/换机）、升级清单签名与暂存。"""
import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
BACKEND = Path(r"c:\Users\32752\Desktop\SBJYWZ\-\backend")
UPGRADE_KEY = "test-upgrade-key-please-change"
s = requests.Session()


def step(t):
    print("\n" + "=" * 70)
    print("▶", t)
    print("=" * 70)


def tool(*args, env_key=True):
    env = None
    if env_key:
        import os
        env = dict(os.environ, UPGRADE_KEY=UPGRADE_KEY)
    out = subprocess.run([sys.executable, str(BACKEND / "tools" / "license_gen.py"), *args],
                         capture_output=True, text=True, encoding="utf-8", env=env)
    return out.stdout + out.stderr


step("1. 健康检查与版本信息")
print("  ", requests.get(f"{BASE}/api/health").json())
tok = s.post(f"{BASE}/api/admin/auth/login",
             json={"username": "admin", "password": "admin888"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
ver = s.get(f"{BASE}/api/admin/system/version", headers=H).json()
print("  版本：", ver)

step("2. 实例指纹")
inst = requests.get(f"{BASE}/api/admin/system/instance").json()["instance_id"]
print("  实例指纹：", inst)

step("3. 状态接口（防护姿态 + 授权状态）")
st = s.get(f"{BASE}/api/admin/system/status", headers=H).json()
print("  限流：", st["rate_limit"])
print("  签名：", st["signature"])
print("  授权：", {k: v for k, v in st["license"].items() if k != "features"})
print("  升级：", st["upgrade"])

step("4. 签发授权码（厂商侧工具，绑定本实例）")
out = tool("issue", "--customer", "尚标易（自营）", "--expires", "2027-12-31", "--instance", inst)
key = [ln.strip() for ln in out.splitlines() if ln.strip().count(".") == 1][-1]
print("  授权码前 40 字符：", key[:40], "…")
print("  长度：", len(key))

step("5. 写入授权码 → 校验通过")
r = s.put(f"{BASE}/api/admin/system/license", headers=H, json={"key": key})
print(f"  HTTP {r.status_code}")
print("  ", (r.json().get("license") or r.json().get("detail")))

step("6. 篡改授权码 → 必须被拒")
bad = key[:-6] + ("A" if key[-6] != "A" else "B") + key[-5:]
r = s.put(f"{BASE}/api/admin/system/license", headers=H, json={"key": bad})
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("7. 已过期授权码 → 必须被拒且说明原因")
out = tool("issue", "--customer", "过期测试", "--expires", "2026-01-01", "--instance", inst)
expired = [ln.strip() for ln in out.splitlines() if ln.strip().count(".") == 1][-1]
r = s.put(f"{BASE}/api/admin/system/license", headers=H, json={"key": expired})
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("8. 绑定其它实例的授权码 → 必须被拒")
out = tool("issue", "--customer", "换机测试", "--expires", "2027-12-31", "--instance", "deadbeef" * 4)
other = [ln.strip() for ln in out.splitlines() if ln.strip().count(".") == 1][-1]
r = s.put(f"{BASE}/api/admin/system/license", headers=H, json={"key": other})
print(f"  HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("9. 重新写回正确授权码，确认状态恢复有效")
r = s.put(f"{BASE}/api/admin/system/license", headers=H, json={"key": key})
lic = r.json()["license"]
print(f"  HTTP {r.status_code}  有效={lic['valid']}  授权对象={lic['customer']}  "
      f"到期={lic['expires_at']}  剩余={lic['days_left']} 天")

step("10. 升级清单：签名校验")
manifest = {
    "version": "1.0.4", "released_at": "2026-10-08", "notes": "测试升级清单",
    "images": [{"name": "trademark-market", "tag": "1.0.4",
                "file": "trademark-market-1.0.4.tar", "sha256": "0" * 64}],
}
body = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
manifest["signature"] = __import__("hmac").new(UPGRADE_KEY.encode(), body, hashlib.sha256).hexdigest()
r = s.post(f"{BASE}/api/admin/system/upgrade/check", headers=H, json={"manifest": manifest})
print(f"  已签名清单：HTTP {r.status_code} ", r.json())
tampered = dict(manifest, version="9.9.9")
r = s.post(f"{BASE}/api/admin/system/upgrade/check", headers=H, json={"manifest": tampered})
print(f"  篡改版本号：HTTP {r.status_code}  提示：{r.json().get('detail')}")

step("11. 升级包暂存：sha256 不符应被拒，相符则暂存")
fake = b"fake image tar bytes for testing"
digest = hashlib.sha256(fake).hexdigest()
r = s.post(f"{BASE}/api/admin/system/upgrade/stage", headers=H,
           files={"manifest_json": (None, json.dumps(manifest)),
                  "file": ("trademark-market-1.0.4.tar", io.BytesIO(fake), "application/x-tar")})
print(f"  先按清单里的假 sha256（000…）：HTTP {r.status_code}  提示：{r.json().get('detail')}")
manifest["images"][0]["sha256"] = digest
body = json.dumps({k: v for k, v in manifest.items() if k != "signature"},
                  sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
manifest["signature"] = __import__("hmac").new(UPGRADE_KEY.encode(), body, hashlib.sha256).hexdigest()
r = s.post(f"{BASE}/api/admin/system/upgrade/stage", headers=H,
           files={"manifest_json": (None, json.dumps(manifest)),
                  "file": ("trademark-market-1.0.4.tar", io.BytesIO(fake), "application/x-tar")})
print(f"  正确 sha256：HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print("  暂存：", d["staged"])
    print("  应用命令：")
    for c in d["commands"]:
        print("    ", c)
r = s.get(f"{BASE}/api/admin/system/status", headers=H).json()
print("  暂存列表：", r["upgrade"]["staged"])
s.delete(f"{BASE}/api/admin/system/upgrade/staged/trademark-market-1.0.4.tar", headers=H)
print("  已清理暂存文件")

step("12. 限流：登录类接口 30 次/分钟")
codes = []
for i in range(36):
    codes.append(requests.post(f"{BASE}/api/admin/auth/login",
                               json={"username": "x", "password": "y"}).status_code)
print(f"  36 次连续请求状态码分布：{ {c: codes.count(c) for c in set(codes)} }")
print("  期望：前面 200/401 若干，末尾出现 429")

step("13. 防护响应头")
r = requests.get(f"{BASE}/api/health")
print("  ", {k: v for k, v in r.headers.items() if k.lower() in ("x-content-type-options", "referrer-policy", "server")})
print("\n✅ 防护与授权验证完毕")