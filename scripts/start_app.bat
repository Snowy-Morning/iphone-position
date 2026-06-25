@echo off
chcp 65001 >nul
cd /d "%~dp0"

title iPhone Virtual Position

if not exist "PositionTool.exe" (
    echo [X] PositionTool.exe not found
    echo Extract the full release zip, do not copy a single bat file only
    pause
    exit /b 1
)

if not exist "_internal" (
    echo [X] Missing _internal folder, extract the full zip
    pause
    exit /b 1
)

powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:49151/hello' -UseBasicParsing -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (
    echo [Hint] tunneld not running (required on iOS 17+)
    echo Plug in iPhone, then run start_tunnel.bat as Administrator
    echo.
    set /p T=Start tunnel now? (Y/n): 
    if /i not "%T%"=="n" (
        powershell -NoProfile -Command "Start-Process -FilePath '%~dp0start_tunnel.bat' -Verb RunAs"
        echo Waiting for tunnel...
        timeout /t 4 >nul
    )
)

echo Starting...
"%~dp0PositionTool.exe"
set ERR=%errorlevel%

if exist "%~dp0crash.log" (
    echo.
    echo [X] Startup failed:
    type "%~dp0crash.log"
    echo.
    pause
    exit /b 1
)

if %ERR% neq 0 (
    echo.
    echo [X] Exited with error code: %ERR%
    pause
    exit /b %ERR%
)
