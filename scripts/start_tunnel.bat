@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_env.bat"

echo ========================================
echo   启动 iPhone USB 隧道
echo ========================================
echo.

powershell -NoProfile -Command "$a=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); if($a){'当前权限: 管理员'}else{'当前权限: 普通用户（若失败请右键以管理员运行）'}"
echo.
echo 请保持此窗口打开，然后运行 start_app.bat
echo 服务地址: http://127.0.0.1:49151
echo.
echo 重要: 请先插上 iPhone 并解锁，再打开本窗口
echo.

powershell -NoProfile -Command "try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',27015);$c.Close();exit 0}catch{exit 1}"
if %errorlevel% neq 0 (
    echo [警告] Apple USB 服务未运行
    echo 请先运行 install_apple_usb.bat 或 check_env.bat
    echo.
)

"%PMD3%" remote tunneld

set ERR=%errorlevel%
echo.
if %ERR% neq 0 (
    echo [错误] tunneld 启动失败，错误码: %ERR%
)
pause
exit /b %ERR%
