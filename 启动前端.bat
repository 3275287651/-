@echo off
chcp 65001 >nul
title 商标交易平台 - 前端 (Vite)
cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo 首次运行，正在安装依赖...
  call npm install --no-audit --no-fund
)

echo ============================================================
echo  商标交易平台 · 前端
echo  前台首页：http://127.0.0.1:5173
echo  运营后台：http://127.0.0.1:5173/admin/login
echo  请确保后端已在 8000 端口运行（双击「启动后端.bat」）
echo ============================================================
echo.

call npm run dev

pause