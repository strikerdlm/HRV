# Fix Jupyter Kernel for HRV Analysis Notebooks
# This script reinstalls the kernel using the correct Python environment

Write-Host "========================================" -ForegroundColor Green
Write-Host "Fixing Jupyter Kernel Configuration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if stats environment exists
$statsPython = "C:\Users\User\Miniconda3\envs\stats\python.exe"
if (-not (Test-Path $statsPython)) {
    Write-Host "[ERROR] Stats environment not found at: $statsPython" -ForegroundColor Red
    Write-Host "Please ensure the 'stats' conda environment exists." -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Found stats environment Python: $statsPython" -ForegroundColor Green
$version = & $statsPython --version
Write-Host "  Python version: $version" -ForegroundColor Cyan
Write-Host ""

# Check if ipykernel is installed in stats environment
Write-Host "Checking ipykernel installation..." -ForegroundColor Yellow
$ipykernelCheck = & $statsPython -c "import ipykernel; print('OK')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] ipykernel not found in stats environment" -ForegroundColor Yellow
    Write-Host "Installing ipykernel..." -ForegroundColor Yellow
    & $statsPython -m pip install ipykernel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install ipykernel" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] ipykernel installed" -ForegroundColor Green
} else {
    Write-Host "[OK] ipykernel is installed" -ForegroundColor Green
}
Write-Host ""

# Remove old kernel if it exists
Write-Host "Removing old kernel (if exists)..." -ForegroundColor Yellow
$kernelPath = "$env:APPDATA\jupyter\kernels\valquiria-analysis"
if (Test-Path $kernelPath) {
    Remove-Item -Path $kernelPath -Recurse -Force
    Write-Host "[OK] Old kernel removed" -ForegroundColor Green
}
Write-Host ""

# Install kernel using stats environment Python
Write-Host "Installing kernel using stats environment..." -ForegroundColor Yellow
& $statsPython -m ipykernel install --user --name=valquiria-analysis --display-name="Valquiria Space Analog Analysis"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Kernel installed successfully!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to install kernel" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Verify kernel installation
Write-Host "Verifying kernel installation..." -ForegroundColor Yellow
$kernels = & $statsPython -m jupyter kernelspec list 2>&1
if ($kernels -match "valquiria-analysis") {
    Write-Host "[OK] Kernel verified and available" -ForegroundColor Green
} else {
    Write-Host "[WARN] Kernel may not be properly registered" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Kernel Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Restart your Jupyter server (if running)" -ForegroundColor White
Write-Host "2. Open your notebook" -ForegroundColor White
Write-Host "3. Select Kernel -> Change Kernel -> 'Valquiria Space Analog Analysis'" -ForegroundColor White
Write-Host "4. Try running a cell" -ForegroundColor White
Write-Host ""

