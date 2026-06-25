@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

title iPhone 虚拟定位 [开发]

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] 未找到 Python，请先安装 Python 3.10+
        pause
        exit /b 1
    )
)

echo 正在检查依赖...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [X] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [提示] 请先插上 iPhone、解锁屏幕并点「信任此电脑」
echo.

powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:49151/hello' -UseBasicParsing -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto launch_app

echo [提示] USB 隧道未运行（iOS 17+ 需要）
echo 将自动弹出隧道窗口，请在 UAC 提示中点「是」
powershell -NoProfile -Command "Start-Process -FilePath '%~dp0scripts\start_tunnel.bat' -Verb RunAs"
echo 等待隧道启动（最多 45 秒，请保持隧道窗口打开）...
set /a WAIT=0

:wait_tunnel
powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:49151/hello' -UseBasicParsing -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto tunnel_ready
set /a WAIT+=1
if !WAIT! geq 45 goto tunnel_timeout
timeout /t 1 >nul
goto wait_tunnel

:tunnel_ready
echo 隧道已就绪
goto launch_app

:tunnel_timeout
echo [警告] 隧道尚未就绪。请确认隧道窗口已打开，且 iPhone 已连接并解锁

:launch_app
echo.
echo 正在启动图形界面...
".venv\Scripts\python.exe" src\app.py
pause
endlocal
