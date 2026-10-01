"""全局配置：所有可变项通过环境变量注入，便于 Docker 部署。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
MEDIA_URL = "/media"

# 前端构建产物目录：源码布局在 <root>/frontend/dist，容器内由 Dockerfile 指定
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist")))

# 默认 SQLite（本地直接可跑）；生产用 Docker 注入 MySQL，如：
# mysql+pymysql://user:pass@mysql:3306/trademark?charset=utf8mb4
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'trademark.db').as_posix()}")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-please-change-in-production")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))

# 首次启动自动创建的超级管理员
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin888")

# 唯一编号前缀与流水位数：TM-20260927-0001
SERIAL_PREFIX = os.getenv("SERIAL_PREFIX", "TM")
SERIAL_PAD = int(os.getenv("SERIAL_PAD", "4"))

CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
).split(",") if o.strip()]

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
ALLOWED_EXCEL_EXT = {".xlsx", ".xlsm", ".csv"}

SITE_NAME = os.getenv("SITE_NAME", "尚标易")

# --------------------------------------------------------------------------- #
# 应用版本与升级
# --------------------------------------------------------------------------- #
APP_VERSION = os.getenv("APP_VERSION", "1.0.3")
BUILD_TIME = os.getenv("BUILD_TIME", "")
# 升级包签名校验密钥（HMAC-SHA256）：厂商侧持有同一把，用于签发升级清单
UPGRADE_KEY = os.getenv("UPGRADE_KEY", "")

# --------------------------------------------------------------------------- #
# 纵深防护开关（默认值偏保守：限流开、签名校验关，确认联调通过后再开）
# --------------------------------------------------------------------------- #
# 反向代理（Nginx / 瑞数等）后面部署时置 true，才信任 X-Forwarded-For
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")
# 单 IP 每分钟请求上限（普通接口 / 登录类接口分开，登录更严）
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "600"))
RATE_LIMIT_LOGIN_PER_MIN = int(os.getenv("RATE_LIMIT_LOGIN_PER_MIN", "30"))
# 请求签名与防重放：write=仅写操作 / all=全部接口 / off=关闭
SIGN_MODE = os.getenv("SIGN_MODE", "off").lower()
SIGN_WINDOW_SECONDS = int(os.getenv("SIGN_WINDOW_SECONDS", "300"))

# --------------------------------------------------------------------------- #
# 授权（License）：Ed25519 签名，公钥在本实例、私钥只在厂商手上
# --------------------------------------------------------------------------- #
# 32 字节公钥的 hex（64 位）或 base64；留空则授权模块不启用
LICENSE_PUBLIC_KEY = os.getenv("LICENSE_PUBLIC_KEY", "")
# warn=只提示不拦截 / block_admin_write=超期后禁后台写操作 / block_all=超期后仅保留登录与授权接口
LICENSE_ENFORCE = os.getenv("LICENSE_ENFORCE", "warn").lower()

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPGRADE_DIR = Path(os.getenv("UPGRADE_DIR", str(DATA_DIR / "upgrades")))
UPGRADE_DIR.mkdir(parents=True, exist_ok=True)