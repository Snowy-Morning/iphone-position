@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_env.bat"

echo ========================================
echo   环境检测
echo ========================================
echo.

echo [1/4] Apple USB 服务 (端口 27015)
powershell -NoProfile -Command "try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',27015);$c.Close();Write-Host '  OK';exit 0}catch{Write-Host '  失败 - 运行 install_apple_usb.bat';exit 1}"
echo.

echo [2/4] tunneld 隧道 (端口 49151)
powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:49151/hello' -UseBasicParsing -TimeoutSec 3)|Out-Null;Write-Host '  OK';exit 0}catch{Write-Host '  未运行 - 打开 start_tunnel.bat';exit 1}"
echo.

echo [3/4] iPhone 连接与隧道
"%PMD3%" usbmux list
powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:49151/' -UseBasicParsing -TimeoutSec 3;Write-Host $r.Content}catch{Write-Host '  无法查询隧道'}"
echo.

echo [4/4] 开发者模式与 DDI 缓存
"%PMD3%" amfi developer-mode-status --tunnel 2>nul
if exist "%USERPROFILE%\.pymobiledevice3\Xcode_iOS_DDI_Personalized\Image.dmg" (
    echo   DDI 镜像: OK
) else (
    echo   DDI 镜像: 未下载 - 运行 download_ddi.bat
)
echo.
echo ========================================
echo 全部 OK 后运行 start_app.bat
echo 开发者模式 false - 运行 enable_developer_mode.bat
echo ========================================
pause
