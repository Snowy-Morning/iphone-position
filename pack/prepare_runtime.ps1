# 为发布包准备便携 Python 运行时（新电脑无需安装 Python）
param(
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Stop"
$version = "3.12.9"
$cacheDir = Join-Path $PSScriptRoot "cache"
$embedZip = Join-Path $cacheDir "python-$version-embed-amd64.zip"
$runtimeDir = Join-Path $ProjectRoot "build\runtime"
$requirements = Join-Path $PSScriptRoot "runtime-requirements.txt"

New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

if (-not (Test-Path $embedZip)) {
    Write-Host "下载 Python $version embed..."
    $url = "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip"
    Invoke-WebRequest -Uri $url -OutFile $embedZip -UseBasicParsing
}

if (Test-Path $runtimeDir) {
    Remove-Item -Recurse -Force $runtimeDir
}
Expand-Archive -Path $embedZip -DestinationPath $runtimeDir -Force

$pthFile = Get-ChildItem "$runtimeDir\python*._pth" | Select-Object -First 1
$pthLines = Get-Content $pthFile.FullName
$pthLines = $pthLines | ForEach-Object { $_ -replace '^#\s*import site', 'import site' }
if ($pthLines -notcontains 'Lib\site-packages') {
    $pthLines += 'Lib\site-packages'
}
Set-Content -Path $pthFile.FullName -Value $pthLines -Encoding ASCII

New-Item -ItemType Directory -Force -Path "$runtimeDir\Lib\site-packages" | Out-Null
New-Item -ItemType Directory -Force -Path "$runtimeDir\Scripts" | Out-Null

$getPip = Join-Path $cacheDir "get-pip.py"
if (-not (Test-Path $getPip)) {
    Write-Host "下载 get-pip.py..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
}

$py = Join-Path $runtimeDir "python.exe"
Write-Host "安装 pip / setuptools / pymobiledevice3（约 2-5 分钟）..."
& $py $getPip --no-warn-script-location
& $py -m pip install -q --upgrade pip setuptools wheel
& $py -m pip install -q -r $requirements --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "pymobiledevice3 安装失败 (pip exit $LASTEXITCODE)"
}

# embed 版 pip 把 exe 装在 runtime 根目录，复制到 Scripts\ 统一路径
$scriptsDir = Join-Path $runtimeDir "Scripts"
foreach ($name in @("pymobiledevice3.exe", "pip.exe", "pip3.exe")) {
    $src = Join-Path $runtimeDir $name
    if (Test-Path $src) {
        Copy-Item -Force $src (Join-Path $scriptsDir $name)
    }
}

# 若仍无 exe，用 cmd 包装（python -m pymobiledevice3）
$pmd3 = Join-Path $scriptsDir "pymobiledevice3.exe"
if (-not (Test-Path $pmd3)) {
    $cmd = Join-Path $scriptsDir "pymobiledevice3.cmd"
    @"
@echo off
"%~dp0..\python.exe" -m pymobiledevice3 %*
"@ | Set-Content -Path $cmd -Encoding ASCII
    Write-Host "使用 pymobiledevice3.cmd 启动器"
} else {
    Write-Host "pymobiledevice3.exe 已就绪"
}

# 验证
& $py -m pymobiledevice3 --help | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "pymobiledevice3 无法运行"
}

Write-Host "[OK] 便携 runtime: $runtimeDir"
