@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

title iPhone 虚拟定位

if not exist "PositionTool.exe" (
    echo [X] 找不到 PositionTool.exe
    echo 请解压完整发布包，不要只复制单个 bat 文件
    pause
    exit /b 1
)

if not exist "_internal" (
    echo [X] 缺少 _internal 文件夹，请解压完整 zip
    pause
    exit /b 1
)

powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:49151/hello' -UseBasicParsing -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto tunnel_prompt
goto launch_app

:tunnel_prompt
echo [提示] USB 隧道未运行（iOS 17+ 需要）
echo 请先插上 iPhone，右键 start_tunnel.bat - 以管理员身份运行
echo.
set /p "T=是否现在启动隧道? [Y/n]: "
if /i "!T!"=="n" goto launch_app
powershell -NoProfile -Command "Start-Process -FilePath '%~dp0start_tunnel.bat' -Verb RunAs"
echo 等待隧道启动...
timeout /t 4 >nul

:launch_app
echo 正在启动图形界面...
"%~dp0PositionTool.exe"
set "ERR=!errorlevel!"

if exist "%~dp0crash.log" (
    echo.
    echo [X] 程序启动失败，错误信息:
    type "%~dp0crash.log"
    echo.
    pause
    exit /b 1
)

if not "!ERR!"=="0" (
    echo.
    echo [X] 程序异常退出，错误码: !ERR!
    pause
    exit /b !ERR!
)

endlocal
