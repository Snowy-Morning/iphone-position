@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   安装 Apple USB 服务
echo ========================================
echo.

powershell -NoProfile -Command "exit ([int](-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)))"
if %errorlevel% equ 0 goto :run_install

echo 需要管理员权限，正在请求提权...
echo 请在 UAC 弹窗中点击「是」
echo.
cscript //nologo "%~dp0install_apple_usb_elevate.vbs"
if %errorlevel% neq 0 (
    echo.
    echo [失败] 请右键 install_apple_usb.bat - 以管理员身份运行
    pause
    exit /b 1
)
echo.
echo 已在新的管理员窗口中启动，请查看 PowerShell 窗口。
pause
exit /b 0

:run_install
powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0install_apple_usb.ps1"
pause
