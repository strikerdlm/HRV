# Diagnose Multiple Conda Installations
# This script identifies all conda installations and helps choose which to use

Write-Host "========================================" -ForegroundColor Green
Write-Host "Conda Installation Diagnostic" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Find all conda installations
Write-Host "Scanning for conda installations..." -ForegroundColor Yellow
Write-Host ""

$condaInstallations = @()

# Check common locations
$possibleLocations = @(
    "$env:USERPROFILE\Anaconda3",
    "$env:USERPROFILE\anaconda3",
    "$env:USERPROFILE\Miniconda3",
    "$env:USERPROFILE\miniconda3",
    "C:\ProgramData\Anaconda3",
    "C:\ProgramData\Miniconda3"
)

foreach ($location in $possibleLocations) {
    if (Test-Path $location) {
        $condaExe = Join-Path $location "Scripts\conda.exe"
        if (Test-Path $condaExe) {
            $version = & $condaExe --version 2>&1
            $size = (Get-ChildItem $location -Recurse -ErrorAction SilentlyContinue | 
                    Measure-Object -Property Length -Sum).Sum / 1GB
            
            $envCount = 0
            $envsPath = Join-Path $location "envs"
            if (Test-Path $envsPath) {
                $envCount = (Get-ChildItem $envsPath -Directory -ErrorAction SilentlyContinue).Count
            }
            
            $condaInstallations += [PSCustomObject]@{
                Path = $location
                Version = $version
                SizeGB = [math]::Round($size, 2)
                Environments = $envCount
                CondaExe = $condaExe
            }
        }
    }
}

# Display findings
Write-Host "Found Conda Installations:" -ForegroundColor Cyan
Write-Host ""

for ($i = 0; $i -lt $condaInstallations.Count; $i++) {
    $inst = $condaInstallations[$i]
    $isActive = $false
    
    # Check if this is the active conda
    $currentConda = (Get-Command conda -ErrorAction SilentlyContinue).Source
    if ($currentConda -and $currentConda -like "$($inst.Path)*") {
        $isActive = $true
        Write-Host "[ACTIVE] " -ForegroundColor Green -NoNewline
    } else {
        Write-Host "        " -NoNewline
    }
    
    Write-Host "Installation $($i + 1):" -ForegroundColor Yellow
    Write-Host "  Path: $($inst.Path)" -ForegroundColor White
    Write-Host "  Version: $($inst.Version)" -ForegroundColor White
    Write-Host "  Size: $($inst.SizeGB) GB" -ForegroundColor White
    Write-Host "  Environments: $($inst.Environments)" -ForegroundColor White
    Write-Host ""
}

# Check PATH
Write-Host "PATH Analysis:" -ForegroundColor Cyan
$pathEntries = $env:PATH -split ';' | Where-Object { $_ -match 'conda|anaconda' }
Write-Host "  Conda-related PATH entries:" -ForegroundColor White
foreach ($entry in $pathEntries) {
    $priority = if ($entry -like "*anaconda3*") { "[ANACONDA]" } else { "[MINICONDA]" }
    Write-Host "    $priority $entry" -ForegroundColor Gray
}
Write-Host ""

# Check which conda is being used
Write-Host "Current Active Conda:" -ForegroundColor Cyan
$activeConda = (Get-Command conda -ErrorAction SilentlyContinue).Source
if ($activeConda) {
    Write-Host "  $activeConda" -ForegroundColor Green
    
    # Find which installation this belongs to
    $activeInstall = $condaInstallations | Where-Object { $activeConda -like "$($_.Path)*" } | Select-Object -First 1
    if ($activeInstall) {
        Write-Host "  Belongs to: $($activeInstall.Path)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  [ERROR] Cannot determine active conda" -ForegroundColor Red
}
Write-Host ""

# Check environments
Write-Host "Environment Locations:" -ForegroundColor Cyan
foreach ($inst in $condaInstallations) {
    $envsPath = Join-Path $inst.Path "envs"
    if (Test-Path $envsPath) {
        $envs = Get-ChildItem $envsPath -Directory -ErrorAction SilentlyContinue | 
                Select-Object -ExpandProperty Name
        if ($envs) {
            Write-Host "  $($inst.Path):" -ForegroundColor Yellow
            foreach ($env in $envs) {
                Write-Host "    - $env" -ForegroundColor Gray
            }
        }
    }
}
Write-Host ""

# Recommendations
Write-Host "========================================" -ForegroundColor Green
Write-Host "Recommendations" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

if ($condaInstallations.Count -gt 1) {
    Write-Host "[WARN] Multiple conda installations detected!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This can cause:" -ForegroundColor White
    Write-Host "  - Environment not found errors" -ForegroundColor Gray
    Write-Host "  - Conflicting package installations" -ForegroundColor Gray
    Write-Host "  - PATH conflicts" -ForegroundColor Gray
    Write-Host "  - Slower conda operations" -ForegroundColor Gray
    Write-Host ""
    
    # Recommend keeping Miniconda3 (smaller, more common)
    $miniconda = $condaInstallations | Where-Object { $_.Path -like "*Miniconda3*" } | Select-Object -First 1
    $anaconda = $condaInstallations | Where-Object { $_.Path -like "*Anaconda3*" } | Select-Object -First 1
    
    if ($miniconda) {
        Write-Host "Recommended: Keep Miniconda3" -ForegroundColor Green
        Write-Host "  - Smaller footprint ($($miniconda.SizeGB) GB vs $($anaconda.SizeGB) GB)" -ForegroundColor White
        Write-Host "  - More environments ($($miniconda.Environments) vs $($anaconda.Environments))" -ForegroundColor White
        Write-Host "  - Path: $($miniconda.Path)" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Run: .\scripts\fix_conda_path.ps1" -ForegroundColor White
    Write-Host "     This will configure PATH to use one conda installation" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Or manually remove Anaconda3 from PATH if not needed" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Consider uninstalling unused conda installation" -ForegroundColor White
    Write-Host "     (Keep the one with your environments)" -ForegroundColor Gray
} else {
    Write-Host "[OK] Only one conda installation found" -ForegroundColor Green
}

Write-Host ""

