# Stickman Animation Agent — Bootstrap Script
# Creates venv and installs Python + npm dependencies.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "=== Stickman Animation Agent Bootstrap ===" -ForegroundColor Cyan

# 1. Create Python venv
$venvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating Python 3.12 venv..." -ForegroundColor Yellow
    py -3.12 -m venv $venvPath
} else {
    Write-Host "Venv already exists at $venvPath" -ForegroundColor Green
}

# 2. Install Python dependencies (kokoro_tts.py, whisper_transcribe.py, and
# generate_subtitles.py under scripts/ are committed to this repo and need
# no further setup once these are installed)
$pip = Join-Path $venvPath "Scripts\pip.exe"
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& $pip install -r (Join-Path $ProjectRoot "requirements.txt")

# 3. Install npm dependencies
Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
Set-Location $ProjectRoot
npm install

Write-Host ""
Write-Host "=== Bootstrap complete ===" -ForegroundColor Cyan
Write-Host "  Python venv: $venvPath"
Write-Host "  Activate:    .venv\Scripts\Activate.ps1"
Write-Host "  Run:         /stickman-animation"
