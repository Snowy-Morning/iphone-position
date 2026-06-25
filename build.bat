@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title 打包发布版

echo.
echo  打包独立发布版（新电脑解压即用，无需安装 Python）
echo  输出: release\PositionTool\  和  PositionTool-Windows.zip
echo.
pause

if not exist ".venv\Scripts\python.exe" (
    echo 创建构建用虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] 打包机需要 Python 3.10+（仅你这台电脑打包时用）
        pause
        exit /b 1
    )
)

echo [1/5] 安装构建依赖...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
".venv\Scripts\python.exe" -m pip install -q -r requirements-build.txt
if errorlevel 1 (
    echo [X] 依赖安装失败
    pause
    exit /b 1
)

echo [2/5] 编译图形界面 exe...
if exist "dist\PositionTool" rmdir /s /q "dist\PositionTool"
if exist "build\position" rmdir /s /q "build\position"
".venv\Scripts\pyinstaller.exe" --noconfirm pack\position.spec
if errorlevel 1 (
    echo [X] PyInstaller 失败
    pause
    exit /b 1
)

echo [3/5] 构建便携 runtime（含 pymobiledevice3）...
powershell -NoProfile -ExecutionPolicy Bypass -File "pack\prepare_runtime.ps1"
if errorlevel 1 (
    echo [X] runtime 构建失败
    pause
    exit /b 1
)

set OUT=release\PositionTool
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" 2>nul

echo [4/5] 组装发布包...
xcopy /E /I /Y /Q "dist\PositionTool\*" "%OUT%\" >nul
xcopy /E /I /Q "build\runtime" "%OUT%\runtime" >nul
copy /Y "src\config.py" "%OUT%\" >nul
copy /Y "src\ddi_cache.py" "%OUT%\" >nul
copy /Y "docs\使用说明.md" "%OUT%\" >nul
for %%f in (
    start_app.bat
    start_tunnel.bat
    check_env.bat
    install_apple_usb.bat
    install_apple_usb.ps1
    install_apple_usb_elevate.vbs
    download_ddi.bat
    enable_developer_mode.bat
    _env.bat
) do copy /Y "scripts\%%f" "%OUT%\" >nul
set ZIP=release\PositionTool-Windows.zip
if exist "%ZIP%" del /f /q "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%ZIP%' -Force"

echo.
echo  打包完成
echo  目录: %OUT%\
echo  压缩: %ZIP%
echo.
echo  发给新电脑: 解压 zip 即可，无需安装 Python
echo  本地开发: 仍用 run.bat
echo.
pause
endlocal
