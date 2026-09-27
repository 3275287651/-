# ---------- 后端镜像：FastAPI + openpyxl（Excel 解析与图片提取） ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    DATA_DIR=/app/data \
    UPLOAD_DIR=/app/uploads

WORKDIR /app

# 系统依赖：pillow 需要 libjpeg/zlib；mysql 客户端库由 pymysql 纯 Python 实现，无需额外包
RUN apt-get update \
 && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir pymysql cryptography

COPY app ./app

RUN mkdir -p /app/data /app/uploads/trademarks

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]