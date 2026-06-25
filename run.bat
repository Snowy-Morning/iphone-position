@echo off
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
echo 提示: iOS 17+ 需先以管理员运行 scripts\start_tunnel.bat
echo.
".venv\Scripts\python.exe" src\app.py
pause
