# ============================================================================
# 商标交易平台 —— 前后端一体单镜像
#
# 构建：docker build -t trademark-market:1.0.0 .
# 导出：docker save -o trademark-market-1.0.0.tar trademark-market:1.0.0
# 部署：docker load -i trademark-market-1.0.0.tar
#       docker run -d --name trademark -p 8080:8000 \
#         -v trademark-data:/app/data -v trademark-uploads:/app/uploads \
#         trademark-market:1.0.0
#
# 特点：内置 SQLite（无需 MySQL/Redis），前端静态资源由后端同端口托管，
#       一条 docker run 即可使用；如需 MySQL，改 -e DATABASE_URL 即可。
# ============================================================================

# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npx vite build


# ---------- 阶段二：运行时（后端 + 前端静态资源） ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    DATA_DIR=/app/data \
    UPLOAD_DIR=/app/uploads \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app

# pillow 依赖 libjpeg/zlib；curl 供 HEALTHCHECK 使用
RUN apt-get update \
 && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g curl \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
# pymysql/cryptography 用于可选的 MySQL 部署，装上后同一镜像既能跑 SQLite 也能连 MySQL
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir pymysql cryptography

COPY backend/app ./app
COPY --from=frontend /build/dist ./frontend/dist

RUN mkdir -p /app/data /app/uploads/trademarks

# 数据与图样：声明为卷，未显式挂载时也会随容器保留（推荐用命名卷，见 README）
VOLUME ["/app/data", "/app/uploads"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# SQLite + 进程内图形验证码：固定单 worker，保证会话一致
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]