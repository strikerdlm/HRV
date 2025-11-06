# Fix Conda libmamba-solver Plugin Issue
# This script fixes the conda-libmamba-solver plugin error

Write-Host "========================================" -ForegroundColor Green
Write-Host "Fixing Conda libmamba-solver Issue" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Method 1: Try to uninstall the problematic plugin
Write-Host "Attempting to uninstall conda-libmamba-solver..." -ForegroundColor Yellow

# Try with base Python
$basePython = "C:\Users\User\Miniconda3\python.exe"
if (Test-Path $basePython) {
    Write-Host "Using base Python: $basePython" -ForegroundColor Cyan
    & $basePython -m pip uninstall -y conda-libmamba-solver 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] conda-libmamba-solver uninstalled" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Could not uninstall via pip (may not be installed via pip)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Base Python not found" -ForegroundColor Yellow
}

Write-Host ""

# Method 2: Edit conda configuration file directly
Write-Host "Attempting to fix conda configuration..." -ForegroundColor Yellow

$condaConfigPath = "$env:USERPROFILE\.condarc"
$condaConfigDir = "$env:USERPROFILE\.conda"

# Check if .condarc exists
if (Test-Path $condaConfigPath) {
    Write-Host "Found conda config at: $condaConfigPath" -ForegroundColor Cyan
    
    # Read current config
    $configContent = Get-Content $condaConfigPath -Raw
    
    # Check if solver is set to libmamba
    if ($configContent -match "solver:\s*libmamba") {
        Write-Host "Found libmamba solver in config, changing to classic..." -ForegroundColor Yellow
        
        # Replace libmamba with classic
        $configContent = $configContent -replace "solver:\s*libmamba", "solver: classic"
        $configContent = $configContent -replace "solver:\s*'libmamba'", "solver: classic"
        $configContent = $configContent -replace 'solver:\s*"libmamba"', "solver: classic"
        
        # Backup original
        Copy-Item $condaConfigPath "$condaConfigPath.backup" -Force
        Write-Host "[OK] Created backup: $condaConfigPath.backup" -ForegroundColor Green
        
        # Write updated config
        Set-Content -Path $condaConfigPath -Value $configContent -NoNewline
        Write-Host "[OK] Updated conda config to use classic solver" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Solver not set to libmamba in config" -ForegroundColor Cyan
        
        # Add solver setting if not present
        if ($configContent -notmatch "solver:") {
            Write-Host "Adding solver setting..." -ForegroundColor Yellow
            $configContent += "`nsolver: classic`n"
            
            # Backup original
            Copy-Item $condaConfigPath "$condaConfigPath.backup" -Force
            Write-Host "[OK] Created backup: $condaConfigPath.backup" -ForegroundColor Green
            
            # Write updated config
            Set-Content -Path $condaConfigPath -Value $configContent -NoNewline
            Write-Host "[OK] Added solver setting to conda config" -ForegroundColor Green
        }
    }
} else {
    Write-Host "[INFO] .condarc not found, creating new config..." -ForegroundColor Yellow
    
    # Create new config with classic solver
    $newConfig = "solver: classic`n"
    Set-Content -Path $condaConfigPath -Value $newConfig
    Write-Host "[OK] Created new conda config with classic solver" -ForegroundColor Green
}

Write-Host ""

# Method 3: Try to remove the plugin entry point
Write-Host "Checking for plugin entry points..." -ForegroundColor Yellow

$condaPluginsPath = "C:\Users\User\Miniconda3\Lib\site-packages\conda\plugins"
if (Test-Path $condaPluginsPath) {
    $libmambaPlugin = Get-ChildItem -Path $condaPluginsPath -Filter "*libmamba*" -Recurse -ErrorAction SilentlyContinue
    if ($libmambaPlugin) {
        Write-Host "[WARN] Found libmamba plugin files (not removing automatically for safety)" -ForegroundColor Yellow
        Write-Host "      Location: $($libmambaPlugin.FullName)" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] No libmamba plugin files found in plugins directory" -ForegroundColor Cyan
    }
}

Write-Host ""

# Test conda after fix
Write-Host "Testing conda after fix..." -ForegroundColor Yellow
$testResult = & conda --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Conda is working! Version: $testResult" -ForegroundColor Green
} else {
    Write-Host "[WARN] Conda still showing errors (may need shell restart)" -ForegroundColor Yellow
    Write-Host "      Error: $testResult" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Close and restart your terminal/PowerShell" -ForegroundColor White
Write-Host "2. Test conda: conda --version" -ForegroundColor White
Write-Host "3. List environments: conda env list" -ForegroundColor White
Write-Host "4. If still having issues, try: conda update conda" -ForegroundColor White
Write-Host ""


