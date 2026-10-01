@echo off
chcp 65001 >nul
title 商标交易平台 - 载入镜像并启动
cd /d "%~dp0"

set IMAGE=trademark-market:1.0.3
set TARFILE=release\trademark-market-1.0.3.tar
set PORT=8080
set CONTAINER=trademark

rem ＝＝ 升级新版本时，改上面两行（IMAGE 与 TARFILE 的版本号）即可 ＝＝

echo ============================================================
echo  商标交易平台 · 一键载入并启动
echo ============================================================
echo.

docker version >nul 2>&1
if errorlevel 1 goto nodocker

echo [1/3] 检查镜像...
docker image inspect %IMAGE% >nul 2>&1
if errorlevel 1 goto loadimage
echo       镜像 %IMAGE% 已存在，跳过载入
goto startcontainer

:loadimage
if not exist "%TARFILE%" goto notar
echo       正在载入镜像（约 76MB，首次需要十几秒）...
docker load -i "%TARFILE%"
if errorlevel 1 goto loadfail
echo       镜像载入完成

:startcontainer
echo.
echo [2/3] 启动容器（端口 %PORT%，数据持久化到 docker 卷）...
docker rm -f %CONTAINER% >nul 2>&1
docker run -d --name %CONTAINER% -p %PORT%:8000 -v trademark-data:/app/data -v trademark-uploads:/app/uploads --restart=always %IMAGE%
if errorlevel 1 goto runfail

echo.
echo [3/3] 等待服务初始化...
rem 用 ping 做延时，避免在非控制台环境下 timeout 报错
ping 127.0.0.1 -n 9 >nul

echo.
echo ============================================================
echo  启动完成
echo    前台首页：http://127.0.0.1:%PORT%
echo    运营后台：http://127.0.0.1:%PORT%/admin/login
echo    默认账号：admin / admin888   （登录后请立即改密码）
echo.
echo  常用命令：
echo    查看日志：docker logs -f %CONTAINER%
echo    停止服务：docker stop %CONTAINER%
echo    再次启动：docker start %CONTAINER%
echo    备份数据：见 README.md「单镜像部署」一节
echo ============================================================
echo.

if "%~1"=="--no-open" goto noopen
start "" http://127.0.0.1:%PORT%
:noopen
if "%~1"=="--no-open" exit /b 0
pause
exit /b 0

:nodocker
echo [错误] 未检测到 Docker。请先安装并启动 Docker Desktop，然后重新运行本脚本。
echo        下载地址：https://www.docker.com/products/docker-desktop/
pause
exit /b 1

:notar
echo [错误] 找不到镜像包：%TARFILE%
echo        请确认 release 目录下的 tar 文件存在，或改用手动方式：
echo          docker load -i release\trademark-market-1.0.0.tar
pause
exit /b 1

:loadfail
echo [错误] 镜像载入失败，请检查 Docker 是否正常运行以及 tar 文件是否完整。
pause
exit /b 1

:runfail
echo [错误] 容器启动失败，请确认端口 %PORT% 未被占用（可在本脚本内修改 PORT 变量）。
pause
exit /b 1