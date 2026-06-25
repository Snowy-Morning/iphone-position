@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_env.bat"

echo ========================================
echo   下载 iOS 开发者镜像 (DDI)
echo ========================================
echo.

if exist "%~dp0ddi_cache.py" (
    set "DDI_SRC=%~dp0"
) else (
    set "DDI_SRC=%~dp0..\src"
)

"%PY%" -c "import sys; sys.path.insert(0, r'%DDI_SRC%'); from ddi_cache import ensure_ddi_cache; ensure_ddi_cache(print)"

if %errorlevel% neq 0 (
    echo.
    echo [失败] 下载未完成，可开 VPN 后重试
    pause
    exit /b 1
)

echo.
echo [OK] 下载完成
pause
