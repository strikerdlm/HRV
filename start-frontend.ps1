# Author: Dr Diego Malpica MD
# PowerShell script to start the TypeScript frontend and API

Write-Host "Mission Control - Flight Surgeon (TypeScript Frontend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not installed. Please install Node.js 18+ LTS." -ForegroundColor Red
    exit 1
}

$nodeVersion = (node --version)
Write-Host "Node.js version: $nodeVersion" -ForegroundColor Green

# Navigate to project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Check if frontend dependencies are installed
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    Set-Location ..
}

# Start FastAPI backend in background
Write-Host ""
Write-Host "Starting FastAPI backend on http://localhost:8180..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "conda activate hrv-py312; uvicorn api.main:app --reload --port 8180"

# Wait for API to start
Start-Sleep -Seconds 3

# Start Next.js frontend
Write-Host ""
Write-Host "Starting Next.js frontend on http://localhost:3100..." -ForegroundColor Yellow
Set-Location frontend
npm run dev
