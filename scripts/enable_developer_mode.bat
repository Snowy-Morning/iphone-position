@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_env.bat"

echo ========================================
echo   显示并开启「开发者模式」
echo ========================================
echo.
echo 说明: 「与 App 开发者共享」不是开发者模式
echo       本脚本帮你在设置里「变出」开发者模式开关
echo.
echo 准备: USB连接 + start_tunnel.bat已打开 + iPhone解锁
echo.
pause

echo.
echo [A] 配对电脑与 iPhone...
"%PMD3%" lockdown pair
echo.

echo [B] reveal-developer-mode (带 tunnel)...
"%PMD3%" amfi reveal-developer-mode --tunnel
echo 退出码: %errorlevel%
echo.

echo [C] reveal-developer-mode (不带 tunnel)...
"%PMD3%" amfi reveal-developer-mode
echo 退出码: %errorlevel%
echo.

echo ========================================
echo 请立刻在 iPhone 上查看:
echo   设置 - 隐私与安全性
echo   是否出现「开发者模式」?
echo ========================================
echo.
echo 若出现了:
echo   1. 打开「开发者模式」开关
echo   2. 点「重新启动」
echo   3. 重启后解锁, 若有弹窗点「打开」
echo   4. 再运行 check_env.bat 确认状态为 true
echo.
echo 若仍然没有「开发者模式」这一项, 见下方「备用方案」
echo.
pause

echo.
echo [D] 尝试 enable-developer-mode...
"%PMD3%" amfi enable-developer-mode --tunnel
echo.

echo [E] 当前状态:
"%PMD3%" amfi developer-mode-status --tunnel
echo.

echo ========================================
echo 备用方案 (设置里始终没有开发者模式时):
echo.
echo  1. 确保已安装 iTunes 且 USB 信任此电脑
echo  2. 在 iPhone 安装任意「开发签名的 App」后,
echo     开发者模式选项才会出现 (iOS 16+ 苹果机制)
echo  3. 或借一台 Mac 用 Xcode 连接一次 iPhone
echo  4. iPhone 有锁屏密码时, 必须在设置里手动打开
echo ========================================
pause
