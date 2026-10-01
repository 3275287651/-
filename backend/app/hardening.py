"""纵深防护：IP 限流、请求签名与防重放、实例指纹、授权（License）校验。

⚠️ 能力边界（不夸大）：
- 前端代码在浏览器里必然可读，混淆只是提高门槛，不能"防止逆向"；
- 本模块的作用是挡住**脚本化抓取、批量爬取、请求重放**这类自动化攻击，
  不能防住有资源、有耐心做定向破解的攻击者；
- 真正保护资产的是交付形态（SaaS 自营、代码与数据不出服务器）与后端加固，
  而不是任何客户端技巧。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import (
    APP_VERSION, BUILD_TIME, DATA_DIR, LICENSE_ENFORCE, LICENSE_PUBLIC_KEY,
    RATE_LIMIT_LOGIN_PER_MIN, RATE_LIMIT_PER_MIN, SIGN_MODE, SIGN_WINDOW_SECONDS,
    TRUST_PROXY,
)

# --------------------------------------------------------------------------- #
# 客户端真实 IP
# --------------------------------------------------------------------------- #
def client_ip(request) -> str:
    """只有在反向代理后面（TRUST_PROXY=true）才信任转发头，避免被伪造绕过限流。"""
    if TRUST_PROXY:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "unknown"


# --------------------------------------------------------------------------- #
# 滑动窗口限流
# --------------------------------------------------------------------------- #
class SlidingWindowLimiter:
    """进程内滑动窗口计数。单实例足够；多副本部署时应换成 Redis 版。"""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_gc = 0.0

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        """返回 (是否放行, 建议等待秒数)。"""
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        with self._lock:
            dq = self._hits.get(key)
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            while dq and now - dq[0] > self.window:
                dq.popleft()
            if len(dq) >= limit:
                return False, int(self.window - (now - dq[0])) + 1
            dq.append(now)
            if now - self._last_gc > 300:
                self._gc(now)
            return True, 0

    def _gc(self, now: float) -> None:
        for key in [k for k, dq in self._hits.items() if not dq or now - dq[-1] > self.window]:
            self._hits.pop(key, None)
        self._last_gc = now

    def stats(self) -> dict:
        with self._lock:
            return {"tracked_ips": len(self._hits)}


limiter = SlidingWindowLimiter()


# --------------------------------------------------------------------------- #
# nonce 防重放
# --------------------------------------------------------------------------- #
class NonceStore:
    """记录已用过的 nonce，超时或超量自动淘汰。"""

    def __init__(self, ttl_seconds: int = 600, cap: int = 50_000) -> None:
        self.ttl = ttl_seconds
        self.cap = cap
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def use(self, nonce: str) -> bool:
        """登记 nonce；返回 False 表示这个 nonce 已经用过（疑似重放）。"""
        now = time.time()
        with self._lock:
            expired = [k for k, t in self._seen.items() if now - t > self.ttl]
            for k in expired:
                self._seen.pop(k, None)
            if len(self._seen) > self.cap:
                for k in sorted(self._seen, key=self._seen.get)[: self.cap // 5]:
                    self._seen.pop(k, None)
            if nonce in self._seen:
                return False
            self._seen[nonce] = now
            return True


nonces = NonceStore()


# --------------------------------------------------------------------------- #
# 请求签名（防篡改 + 防重放）
# --------------------------------------------------------------------------- #
def _body_digest(body: bytes, skip: bool) -> str:
    if skip:
        # 文件上传等无法在浏览器端稳定复算的请求体，约定用空体摘要，
        # 签名仍然覆盖 方法+路径+时间戳+nonce，重放保护不受影响
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(body).hexdigest()


def sign_request(token: str, method: str, path: str, ts: str, nonce: str,
                 body: bytes = b"", skip_body: bool = False) -> str:
    """前后端共用：以登录令牌为密钥计算签名。"""
    msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{_body_digest(body, skip_body)}"
    return hmac.new(token.encode(), msg.encode(), hashlib.sha256).hexdigest()


_SIGN_SKIP_PREFIXES = ("/api/auth/", "/api/admin/auth/", "/api/admin/system/")

# 真正的凭证类接口才用严格限流（验证码/注册/登录），避免误伤会话校验等普通请求
_STRICT_LIMIT_PATHS = (
    "/api/auth/captcha", "/api/auth/register", "/api/auth/login", "/api/admin/auth/login",
)


def is_strict_limited(path: str) -> bool:
    return path in _STRICT_LIMIT_PATHS


def sign_required(method: str, path: str) -> bool:
    if SIGN_MODE not in ("write", "all"):
        return False
    if not path.startswith("/api/") or path.startswith(_SIGN_SKIP_PREFIXES):
        return False
    if SIGN_MODE == "write":
        return method.upper() in ("POST", "PUT", "PATCH", "DELETE")
    return True


def verify_signature(token: str, method: str, path: str, headers, body: bytes) -> tuple[bool, str]:
    ts = headers.get("x-ts") or ""
    nonce = headers.get("x-nonce") or ""
    signature = headers.get("x-sign") or ""
    if not (ts and nonce and signature):
        return False, "缺少签名头（X-TS / X-Nonce / X-Sign）"
    try:
        ts_value = int(ts)
    except ValueError:
        return False, "时间戳格式非法"
    drift = abs(time.time() - ts_value)
    if drift > SIGN_WINDOW_SECONDS:
        return False, f"请求时间戳超出 {SIGN_WINDOW_SECONDS} 秒允许窗口（服务器与客户端时钟可能不同步）"
    skip_body = (headers.get("x-body-mode") or "").lower() == "skip"
    expected = sign_request(token, method, path, ts, nonce, body, skip_body)
    if not hmac.compare_digest(expected, signature):
        return False, "签名不匹配"
    if not nonces.use(nonce):
        return False, "该 nonce 已被使用（疑似重放请求）"
    return True, ""


# --------------------------------------------------------------------------- #
# 实例指纹
# --------------------------------------------------------------------------- #
def instance_id() -> str:
    """每套部署唯一且稳定的指纹，用于把授权码绑定到具体实例。"""
    path = DATA_DIR / "instance_id"
    try:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
        value = uuid.uuid4().hex
        path.write_text(value + "\n", encoding="utf-8")
        return value
    except OSError:
        return "unknown"


def version_info() -> dict:
    return {
        "version": APP_VERSION,
        "build_time": BUILD_TIME or "未记录（源码直接运行）",
        "instance_id": instance_id(),
    }


# --------------------------------------------------------------------------- #
# 授权（License）
# --------------------------------------------------------------------------- #
@dataclass
class LicenseStatus:
    enabled: bool = False            # 是否配置了公钥（授权模块是否启用）
    has_key: bool = False            # 是否填了授权码
    valid: bool = False
    customer: str = ""
    expires_at: str = ""
    days_left: int | None = None
    features: list[str] = field(default_factory=list)
    instance_match: bool = True
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "has_key": self.has_key,
            "valid": self.valid,
            "customer": self.customer,
            "expires_at": self.expires_at,
            "days_left": self.days_left,
            "features": self.features,
            "instance_match": self.instance_match,
            "reason": self.reason,
            "enforce": LICENSE_ENFORCE,
            "public_key_configured": bool(LICENSE_PUBLIC_KEY),
            "instance_id": instance_id(),
        }


def _public_key():
    """解析 LICENSE_PUBLIC_KEY（hex 或 base64 的 32 字节 Ed25519 公钥）。"""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    raw = LICENSE_PUBLIC_KEY.strip()
    if not raw:
        raise ValueError("未配置公钥")
    if len(raw) == 64:
        data = bytes.fromhex(raw)
    else:
        data = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    return Ed25519PublicKey.from_public_bytes(data)


def parse_license(key: str) -> LicenseStatus:
    """校验授权码：<base64url(payload)>.<base64url(signature)>，Ed25519 签名。"""
    status = LicenseStatus(enabled=bool(LICENSE_PUBLIC_KEY), has_key=bool(key))
    if not LICENSE_PUBLIC_KEY:
        status.reason = "未配置授权公钥（LICENSE_PUBLIC_KEY），授权模块未启用"
        return status
    if not key:
        status.reason = "尚未配置授权码"
        return status
    try:
        payload_b64, sig_b64 = key.strip().split(".", 1)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4))
        signature = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        _public_key().verify(signature, payload_bytes)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:  # noqa: BLE001
        status.reason = "授权码格式错误或签名校验失败（请确认是本系统签发的授权码）"
        return status

    status.customer = str(payload.get("customer") or "")
    status.expires_at = str(payload.get("expires") or "")
    status.features = list(payload.get("features") or [])

    bound = str(payload.get("instance") or "*")
    if bound not in ("*", instance_id()):
        status.instance_match = False
        status.reason = "授权码与当前实例指纹不一致（授权码可能属于另一套部署）"
        return status

    today = date.today()
    try:
        expires = datetime.strptime(status.expires_at, "%Y-%m-%d").date()
    except ValueError:
        status.reason = "授权码中的到期日期格式非法"
        return status
    status.days_left = (expires - today).days
    if expires < today:
        status.reason = f"授权已于 {status.expires_at} 到期"
        return status
    status.valid = True
    status.reason = "授权有效"
    return status


_license_cache: tuple[float, LicenseStatus] | None = None
_license_lock = threading.Lock()


def current_license(force: bool = False) -> LicenseStatus:
    """带 60 秒缓存的授权状态读取（授权码存在站点配置里）。"""
    global _license_cache
    now = time.time()
    with _license_lock:
        if not force and _license_cache and now - _license_cache[0] < 60:
            return _license_cache[1]
    key = ""
    try:
        from .database import SessionLocal
        from .settings_store import get_all

        db = SessionLocal()
        try:
            key = str(get_all(db).get("license_key") or "")
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        key = ""
    status = parse_license(key)
    with _license_lock:
        _license_cache = (now, status)
    return status


def clear_license_cache() -> None:
    global _license_cache
    with _license_lock:
        _license_cache = None


# --------------------------------------------------------------------------- #
# 中间件：限流 → 签名校验 → 授权拦截
# --------------------------------------------------------------------------- #
_LICENSE_OPEN_PREFIXES = ("/api/admin/auth/", "/api/admin/system/", "/api/auth/", "/api/health")

_LICENSE_BLOCKED_MSG = (
    "系统授权已过期或未生效，后台写操作已被拦截。"
    "请在「系统与授权」页填写有效授权码，或联系服务商续期。"
)


def _license_blocks(method: str, path: str) -> bool:
    if LICENSE_ENFORCE not in ("block_admin_write", "block_all"):
        return False
    if path.startswith(_LICENSE_OPEN_PREFIXES):
        return False
    status = current_license()
    if status.valid:
        return False
    if LICENSE_ENFORCE == "block_admin_write":
        return method.upper() in ("POST", "PUT", "PATCH", "DELETE") and path.startswith("/api/admin/")
    return path.startswith("/api/")


class HardeningMiddleware(BaseHTTPMiddleware):
    """把最外层防护放在路由之前：先限流，再验签，最后看授权。"""

    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method

        if path.startswith("/api/"):
            ip = client_ip(request)
            strict = is_strict_limited(path)
            limit = RATE_LIMIT_LOGIN_PER_MIN if strict else RATE_LIMIT_PER_MIN
            allowed, retry_after = limiter.allow(f"{ip}|{'auth' if strict else 'api'}", limit)
            if not allowed:
                return JSONResponse(
                    {"detail": f"请求过于频繁，请 {retry_after} 秒后重试"},
                    status_code=429, headers={"Retry-After": str(retry_after)},
                )

            if sign_required(method, path):
                authorization = request.headers.get("authorization") or ""
                token = authorization.split()[-1] if authorization else ""
                body = await request.body() if method.upper() in ("POST", "PUT", "PATCH", "DELETE") else b""
                ok, why = verify_signature(token, method, path, request.headers, body)
                if not ok:
                    return JSONResponse({"detail": f"请求校验失败：{why}"}, status_code=401)

            if _license_blocks(method, path):
                return JSONResponse({"detail": _LICENSE_BLOCKED_MSG}, status_code=403)

        response = await call_next(request)
        # 收紧响应头（server 指纹需在启动参数里关：uvicorn --no-server-header）
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def hardening_status() -> dict:
    """给后台展示当前防护姿态。"""
    return {
        "rate_limit": {
            "per_min": RATE_LIMIT_PER_MIN,
            "login_per_min": RATE_LIMIT_LOGIN_PER_MIN,
            "trust_proxy": TRUST_PROXY,
            "tracked_ips": limiter.stats()["tracked_ips"],
        },
        "signature": {
            "mode": SIGN_MODE,
            "window_seconds": SIGN_WINDOW_SECONDS,
            "enabled": SIGN_MODE in ("write", "all"),
            "note": "启用后必须使用 HTTPS（浏览器 Web Crypto 仅在安全上下文可用）",
        },
        "license": current_license().as_dict(),
        "anti_reverse": {
            "frontend_obfuscation": "构建期可选（OBFS_ENABLE）",
            "backend_compiled": "可选构建（Nuitka，见 Dockerfile 的 hardened 阶段）",
            "note": "前端代码无法真正保密，混淆仅提高门槛；SaaS 自营是最有效的保护",
        },
    }