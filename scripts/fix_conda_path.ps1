# Fix Conda PATH Configuration
# This script configures PATH to use a single conda installation

Write-Host "========================================" -ForegroundColor Green
Write-Host "Fixing Conda PATH Configuration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Determine which conda to use (prefer Miniconda3)
$preferredConda = $null
$minicondaPath = "$env:USERPROFILE\Miniconda3"
$anacondaPath = "$env:USERPROFILE\Anaconda3"

if (Test-Path "$minicondaPath\Scripts\conda.exe") {
    $preferredConda = $minicondaPath
    Write-Host "[INFO] Using Miniconda3: $preferredConda" -ForegroundColor Green
} elseif (Test-Path "$anacondaPath\Scripts\conda.exe") {
    $preferredConda = $anacondaPath
    Write-Host "[INFO] Using Anaconda3: $preferredConda" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Cannot find preferred conda installation" -ForegroundColor Red
    Write-Host "Please run diagnose_conda_installations.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Get current user PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = $userPath -split ';'

# Remove all conda/anaconda entries
Write-Host "Cleaning PATH..." -ForegroundColor Yellow
$cleanedPath = $pathEntries | Where-Object { 
    $_ -notmatch 'conda|anaconda' -and $_ -ne ''
}

# Add preferred conda paths (in correct order)
$condaPaths = @(
    "$preferredConda",
    "$preferredConda\Scripts",
    "$preferredConda\Library\bin",
    "$preferredConda\condabin"
)

Write-Host "Adding conda paths:" -ForegroundColor Yellow
foreach ($path in $condaPaths) {
    if (Test-Path $path) {
        if ($cleanedPath -notcontains $path) {
            $cleanedPath += $path
            Write-Host "  [ADDED] $path" -ForegroundColor Green
        } else {
            Write-Host "  [EXISTS] $path" -ForegroundColor Cyan
        }
    }
}

# Update user PATH
$newPath = $cleanedPath -join ';'
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")

Write-Host ""
Write-Host "[OK] User PATH updated" -ForegroundColor Green
Write-Host ""

# Update current session PATH
$env:Path = $newPath

Write-Host "Testing conda..." -ForegroundColor Yellow
$condaVersion = & conda --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Conda working: $condaVersion" -ForegroundColor Green
} else {
    Write-Host "[WARN] Conda test failed (may need new terminal)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Restart your terminal/PowerShell for changes to take effect" -ForegroundColor Yellow
Write-Host ""
Write-Host "After restart, test with:" -ForegroundColor Cyan
Write-Host "  conda --version" -ForegroundColor White
Write-Host "  conda env list" -ForegroundColor White
Write-Host "  conda activate stats" -ForegroundColor White
Write-Host ""

