@echo off
chcp 65001 >nul
title 商标交易平台 - 后端服务 (FastAPI)
cd /d "%~dp0backend"

echo ============================================================
echo  商标交易平台 · 后端服务
echo  接口地址：http://127.0.0.1:8000
echo  接口文档：http://127.0.0.1:8000/api/docs
echo  后台入口：http://127.0.0.1:5173/admin/login  (需先启动前端)
echo  默认账号：admin / admin888
echo ============================================================
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause