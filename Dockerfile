# ============================================================================
# 商标交易平台 —— 前后端一体单镜像
#
# 构建（普通）：docker build --provenance=false --sbom=false \
#                --build-arg APP_VERSION=1.0.3 -t trademark-market:1.0.3 .
# 构建（加固：后端编译为二进制，镜像内不含明文 .py）：
#       docker build --target hardened -t trademark-market:1.0.3-hardened .
# 导出：docker save -o trademark-market-1.0.3.tar trademark-market:1.0.3
# 部署：docker load -i trademark-market-1.0.3.tar
#       docker run -d --name trademark -p 8080:8000 \
#         -v trademark-data:/app/data -v trademark-uploads:/app/uploads \
#         trademark-market:1.0.3
#
# 特点：内置 SQLite（无需 MySQL/Redis），前端静态资源由后端同端口托管，
#       一条 docker run 即可使用；如需 MySQL，改 -e DATABASE_URL 即可。
# ============================================================================

# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS frontend

# 前端代码混淆开关：默认开启（提高读代码门槛），排障时可 --build-arg OBFS_ENABLE=false
ARG OBFS_ENABLE=true
ENV OBFS_ENABLE=${OBFS_ENABLE}

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npx vite build


# ---------- 可选阶段二：后端二进制化（Nuitka）----------
# 仅当显式 `--target hardened` 时构建；普通构建不会走这一步（耗时长且需额外编译工具链）
FROM python:3.12-slim AS backend-builder

ARG APP_VERSION=1.0.3

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc g++ patchelf ccache \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt nuitka ordered-set zstandard

COPY backend/app ./app
# 入口脚本：编译进二进制，运行时不依赖 .py 源码
RUN printf '%s\n' \
      'import uvicorn' \
      'from app.main import app' \
      '' \
      'if __name__ == "__main__":' \
      '    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)' > run.py
RUN python -m nuitka \
      --standalone --assume-yes-for-downloads --quiet \
      --output-dir=/build --output-filename=trademark \
      --include-package=app \
      --include-package=uvicorn --include-package=sqlalchemy --include-package=openpyxl \
      --include-package=multipart --include-package=jwt \
      --include-module=sqlalchemy.dialects.sqlite.pysqlite \
      --nofollow-import-to=tkinter,test,tests \
      run.py


# ---------- 可选阶段三：加固运行时（二进制 + 前端静态资源）----------
FROM python:3.12-slim AS hardened

ARG APP_VERSION=1.0.3
ARG BUILD_TIME=""

ENV PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    DATA_DIR=/app/data \
    UPLOAD_DIR=/app/uploads \
    FRONTEND_DIST=/app/frontend/dist \
    APP_VERSION=${APP_VERSION} \
    BUILD_TIME=${BUILD_TIME}

WORKDIR /app
RUN apt-get update \
 && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /build/run.dist ./
COPY --from=frontend /build/dist ./frontend/dist
RUN mkdir -p /app/data /app/uploads/trademarks

VOLUME ["/app/data", "/app/uploads"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1
CMD ["./trademark"]


# ---------- 阶段四（默认）：运行时（后端 + 前端静态资源）----------
FROM python:3.12-slim AS runtime

ARG APP_VERSION=1.0.3
ARG BUILD_TIME=""

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    DATA_DIR=/app/data \
    UPLOAD_DIR=/app/uploads \
    FRONTEND_DIST=/app/frontend/dist \
    APP_VERSION=${APP_VERSION} \
    BUILD_TIME=${BUILD_TIME}

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
# --no-server-header：不对外暴露 uvicorn 指纹
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]