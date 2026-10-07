# ============================================================
#  Node.js LTS download + install script (Windows)
#  Usage: run via install_nodejs.bat, or right-click "Run with PowerShell"
#  Strategy: try winget first; fallback to official MSI download.
#
#  NOTE: This file is intentionally ASCII-only (English messages).
#        Windows PowerShell 5.1 reads .ps1 using the system ANSI
#        codepage (GBK on Chinese Windows), which corrupts UTF-8
#        Chinese characters and breaks the parser. Keeping this file
#        pure ASCII avoids that entirely.
# ============================================================
$ErrorActionPreference = 'Stop'

# Change this to pin a specific LTS version (Windows x64 MSI)
$NodeVersion = 'v22.14.0'
$MsiUrl = "https://nodejs.org/dist/$NodeVersion/node-$NodeVersion-x64.msi"
$MsiPath = Join-Path $PSScriptRoot "node-$NodeVersion-x64.msi"

function Get-NodeVersion {
    try {
        $v = (& node --version) 2>$null
        if ($v) { return $v }
    } catch {}
    return $null
}

$existing = Get-NodeVersion
if ($existing) {
    Write-Host "[OK] Node.js already installed: $existing" -ForegroundColor Green
    try {
        $npmv = (& npm --version) 2>$null
        if ($npmv) { Write-Host "[OK] npm $npmv" -ForegroundColor Green }
    } catch {}
    exit 0
}

# ---------- Method 1: winget ----------
$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    Write-Host "==> Installing Node.js LTS via winget ..." -ForegroundColor Cyan
    try {
        winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
        Write-Host "[OK] winget install finished." -ForegroundColor Green
        Write-Host "    Please CLOSE and REOPEN the terminal, then verify with: node -v" -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "winget install failed, falling back to MSI download." -ForegroundColor Yellow
    }
}

# ---------- Method 2: download official MSI ----------
Write-Host "==> Downloading Node.js $NodeVersion MSI ..." -ForegroundColor Cyan
Write-Host "    $MsiUrl"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath

Write-Host "==> Launching installer (accept the UAC prompt if it appears) ..." -ForegroundColor Cyan
$proc = Start-Process msiexec.exe -ArgumentList "/i `"$MsiPath`" /qb" -Wait -PassThru
if ($proc.ExitCode -eq 0) {
    Write-Host "[OK] Node.js installed successfully." -ForegroundColor Green
    Write-Host "    Please CLOSE and REOPEN the terminal so PATH takes effect, then verify with: node -v" -ForegroundColor Yellow
} else {
    Write-Host "[ERR] Installer exit code: $($proc.ExitCode)." -ForegroundColor Red
    Write-Host "      You can install manually by double-clicking: $MsiPath" -ForegroundColor Red
    exit 1
}
