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

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)