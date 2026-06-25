# Apple USB service installer for Windows
# Called by install_apple_usb.bat (run as Administrator)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# TLS 1.2 for older PowerShell
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

$UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

function Wait-Exit {
    param([string]$Message = "Press Enter to exit")
    Write-Host ""
    Read-Host $Message
}

function Test-UsbMux {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect([System.Net.IPAddress]::Loopback, 27015)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-FileSizeMB {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    return [math]::Round((Get-Item $Path).Length / 1MB, 1)
}

function Test-ValidExe {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $size = (Get-Item $Path).Length
    if ($size -lt 50MB) { return $false }
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        return ($bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A)  # MZ header
    }
    catch {
        return $false
    }
}

function Download-FileRobust {
    param(
        [string]$Url,
        [string]$OutFile,
        [string]$Label
    )

    $dir = Split-Path $OutFile -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    $partFile = "$OutFile.part"
    $resumeFrom = 0
    if (Test-Path $partFile) {
        $resumeFrom = (Get-Item $partFile).Length
        if ($resumeFrom -gt 0) {
            Write-Host "  Resume partial file: $([math]::Round($resumeFrom/1MB,1)) MB"
        }
    }
    elseif (Test-Path $OutFile) {
        $resumeFrom = (Get-Item $OutFile).Length
        if ($resumeFrom -gt 0) {
            Copy-Item $OutFile $partFile -Force
            Write-Host "  Resume existing file: $([math]::Round($resumeFrom/1MB,1)) MB"
        }
    }

    # Method 1: BITS (resume support, stable on Windows)
    if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
        try {
            Write-Host "  [$Label] BITS download..."
            if ($resumeFrom -gt 0 -and (Test-Path $partFile)) {
                Start-BitsTransfer -Source $Url -Destination $partFile -TransferType Download -ErrorAction Stop
            }
            else {
                Start-BitsTransfer -Source $Url -Destination $OutFile -TransferType Download -ErrorAction Stop
            }
            if (Test-Path $partFile) {
                Move-Item $partFile $OutFile -Force
            }
            if ((Test-Path $OutFile) -and (Get-Item $OutFile).Length -gt 1MB) {
                Write-Host "  [$Label] OK ($(Get-FileSizeMB $OutFile) MB)" -ForegroundColor Green
                return $true
            }
        }
        catch {
            Write-Host "  [$Label] BITS failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    # Method 2: WebClient with resume
    try {
        Write-Host "  [$Label] WebClient download..."
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", $UserAgent)
        $target = if (Test-Path $partFile) { $partFile } else { $OutFile }

        if ($resumeFrom -gt 0) {
            $wc.Headers.Add("Range", "bytes=$resumeFrom-")
            $existing = [System.IO.File]::ReadAllBytes($target)
            $newData = $wc.DownloadData($Url)
            $fs = [System.IO.File]::Open($target, [System.IO.FileMode]::Append)
            $fs.Write($newData, 0, $newData.Length)
            $fs.Close()
        }
        else {
            $wc.DownloadFile($Url, $target)
        }

        if (Test-Path $partFile) {
            Move-Item $partFile $OutFile -Force
        }
        if ((Test-Path $OutFile) -and (Get-Item $OutFile).Length -gt 1MB) {
            Write-Host "  [$Label] OK ($(Get-FileSizeMB $OutFile) MB)" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "  [$Label] WebClient failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    # Method 3: Invoke-WebRequest (last resort)
    try {
        Write-Host "  [$Label] Invoke-WebRequest..."
        $params = @{
            Uri             = $Url
            OutFile         = $OutFile
            UseBasicParsing = $true
            Headers         = @{ "User-Agent" = $UserAgent }
            MaximumRedirection = 10
        }
        Invoke-WebRequest @params
        if ((Test-Path $OutFile) -and (Get-Item $OutFile).Length -gt 1MB) {
            Write-Host "  [$Label] OK ($(Get-FileSizeMB $OutFile) MB)" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "  [$Label] IWR failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    return $false
}

function Install-MsiQuiet {
    param([string]$MsiPath)
    Write-Host "Installing: $(Split-Path $MsiPath -Leaf)"
    $argList = "/i `"$MsiPath`" /quiet /norestart"
    $proc = Start-Process msiexec.exe -ArgumentList $argList -Wait -PassThru
    return ($proc.ExitCode -eq 0 -or $proc.ExitCode -eq 3010)
}

function Start-AppleMobileService {
    Write-Host ""
    Write-Host "Starting Apple Mobile Device Service..."
    foreach ($name in @("Apple Mobile Device Service", "Apple Mobile Device")) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc) {
            if ($svc.Status -ne "Running") {
                Start-Service $name
            }
            Set-Service $name -StartupType Automatic -ErrorAction SilentlyContinue
            Write-Host "[OK] Service started: $name" -ForegroundColor Green
            return
        }
    }
    Write-Host "[WARN] Service not found yet. Reboot may be required." -ForegroundColor Yellow
}

try {
    if (-not (Test-IsAdmin)) {
        Write-Host "[ERROR] Administrator rights required." -ForegroundColor Red
        Write-Host "Right-click install_apple_usb.bat -> Run as administrator"
        Wait-Exit
        exit 1
    }

    Set-Location $PSScriptRoot

    Write-Host "========================================"
    Write-Host "  Install Apple USB Service"
    Write-Host "========================================"
    Write-Host ""

    if (Test-UsbMux) {
        Write-Host "[OK] Apple USB service is running (port 27015)" -ForegroundColor Green
        Write-Host "You can run start_tunnel.bat and start_app.bat now."
        Wait-Exit
        exit 0
    }

    Write-Host "[INFO] Apple USB service not found. Installing..."
    Write-Host ""

    $workDir = Join-Path $PSScriptRoot ".apple_install"
    New-Item -ItemType Directory -Force -Path $workDir | Out-Null
    $setupExe = Join-Path $workDir "iTunes64Setup.exe"
    $msiOnly = Join-Path $workDir "AppleMobileDeviceSupport64.msi"

    $installed = $false

    # --- Option A: small MSI direct download (~30MB, recommended) ---
    if (-not $installed) {
        Write-Host "[Step 1] Try direct USB service package (small, ~30MB)..."
        $msiUrls = @(
            "https://swcdn.apple.com/content/downloads/47/50/042-92438/wm9fwo0icox4nzlrguw23zu25vmy4nst08/AppleMobileDeviceSupport64.msi",
            "http://swcdn.apple.com/content/downloads/47/50/042-92438/wm9fwo0icox4nzlrguw23zu25vmy4nst08/AppleMobileDeviceSupport64.msi"
        )
        foreach ($url in $msiUrls) {
            if (Download-FileRobust -Url $url -OutFile $msiOnly -Label "MSI") {
                if (Install-MsiQuiet -MsiPath $msiOnly) {
                    $installed = $true
                    Write-Host "[OK] Apple Mobile Device Support installed" -ForegroundColor Green
                }
                break
            }
        }
    }

    # --- Option B: use existing local iTunes installer ---
    if (-not $installed) {
        if (Test-ValidExe $setupExe) {
            Write-Host "[Step 2] Found valid local iTunes64Setup.exe ($(Get-FileSizeMB $setupExe) MB)"
        }
        elseif (Test-Path $setupExe) {
            $sz = Get-FileSizeMB $setupExe
            if ($sz -gt 100) {
                Write-Host "[Step 2] Found large partial download ($sz MB), will try to use it..."
            }
            else {
                Remove-Item $setupExe -Force -ErrorAction SilentlyContinue
            }
        }
    }

    # --- Option C: download full iTunes installer ---
    if (-not $installed -and -not (Test-ValidExe $setupExe)) {
        Write-Host "[Step 3] Download full iTunes installer (~200MB, may take a while)..."
        $exeUrls = @(
            "https://secure-appldnld.apple.com/itunes12/042-92440-20231213-DDE54149-6537-4DB9-97D6-69413CD6CF86/iTunes64Setup.exe",
            "https://www.apple.com/cn/itunes/download/win64",
            "https://www.apple.com/itunes/download/win64"
        )
        foreach ($url in $exeUrls) {
            if (Download-FileRobust -Url $url -OutFile $setupExe -Label "iTunes") {
                break
            }
        }
    }

    # --- Install from iTunes package ---
    if (-not $installed -and (Test-Path $setupExe) -and (Get-Item $setupExe).Length -gt 50MB) {
        $sevenZip = @(
            "$env:ProgramFiles\7-Zip\7z.exe",
            "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1

        if ($sevenZip) {
            Write-Host "Extracting AppleMobileDeviceSupport64.msi from iTunes package..."
            $extractDir = Join-Path $workDir "extract"
            if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
            New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
            & $sevenZip x $setupExe "-o$extractDir" -y | Out-Null
            $msi = Get-ChildItem -Path $extractDir -Filter "AppleMobileDeviceSupport64.msi" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($msi -and (Install-MsiQuiet -MsiPath $msi.FullName)) {
                $installed = $true
                Write-Host "[OK] Installed from extracted MSI" -ForegroundColor Green
            }
        }

        if (-not $installed) {
            Write-Host "Installing full iTunes (passive mode)..."
            $proc = Start-Process $setupExe -ArgumentList "/passive" -Wait -PassThru
            if ($proc.ExitCode -eq 0 -or $proc.ExitCode -eq 3010) {
                $installed = $true
            }
            else {
                Write-Host "[WARN] iTunes installer exit code: $($proc.ExitCode)" -ForegroundColor Yellow
            }
        }
    }

    if (-not $installed) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "  Auto install failed" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Manual steps (most reliable):"
        Write-Host "  1. Browser open: https://www.apple.com/cn/itunes/download/"
        Write-Host "  2. Download 64-bit iTunes, install it"
        Write-Host "  3. OR save file as:"
        Write-Host "     $setupExe"
        Write-Host "     then run this script again"
        Write-Host "  4. Run check_env.bat"
        Write-Host ""
        Start-Process "https://www.apple.com/cn/itunes/download/"
        Wait-Exit
        exit 1
    }

    Start-AppleMobileService
    Start-Sleep -Seconds 2

    Write-Host ""
    if (Test-UsbMux) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  SUCCESS - USB service is ready" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next: connect iPhone -> start_tunnel.bat -> start_app.bat"
    }
    else {
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "  Installed but port 27015 not ready yet" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. Connect iPhone via USB, unlock, tap Trust"
        Write-Host "2. Reboot PC"
        Write-Host "3. Run check_env.bat"
        Write-Host ""
        Write-Host "If still failing, Device Manager -> update driver:"
        Write-Host "  C:\Program Files\Common Files\Apple\Mobile Device Support\Drivers"
    }

    Write-Host ""
    Wait-Exit
}
catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual: https://www.apple.com/cn/itunes/download/"
    Wait-Exit
    exit 1
}
