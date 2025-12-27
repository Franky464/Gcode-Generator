<#
Build helper: Run PyInstaller via existing build_exe.ps1 then (optionally) call Inno Setup's ISCC to make an installer.

Usage:
  .\.venv\Scripts\Activate.ps1
  .\scripts\make_installer.ps1          # one-dir build + attempt to run Inno Setup
  .\scripts\make_installer.ps1 -OneFile  # onefile build + attempt to run Inno Setup

Notes:
 - Requires PyInstaller (the script will install it into the active environment).
 - To produce an Inno Setup installer you need Inno Setup installed (ISCC.exe available).
 - If Inno Setup is not installed, the script will still produce the PyInstaller build; you can run ISCC manually later.
#>

param([switch]$OneFile, [string]$IsccPath)

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDir

Write-Host "Building exe with PyInstaller (via scripts/build_exe.ps1)..." -ForegroundColor Cyan
# Call existing build script (pass the -OneFile switch properly)
if ($OneFile) {
    & "$scriptDir\build_exe.ps1" -OneFile
} else {
    & "$scriptDir\build_exe.ps1"
}
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed with exit code $LASTEXITCODE"
    Pop-Location
    exit $LASTEXITCODE
}

# Determine dist folder produced by build_exe.ps1
$distDir = Join-Path -Path (Resolve-Path "$scriptDir\..\dist\Gcode-Generator").Path -ChildPath '' 2>$null
if (-not (Test-Path $distDir)) {
    # Try alternative for onefile: dist\Gcode-Generator.exe
    $onefileExe = Join-Path (Resolve-Path "$scriptDir\..\dist").Path 'Gcode-Generator.exe' 2>$null
    if (Test-Path $onefileExe) {
        $distDir = (Resolve-Path "$scriptDir\..\dist").Path
    } else {
        Write-Warning "Could not locate dist\Gcode-Generator. Check PyInstaller output."
        Pop-Location
        return
    }
}

Write-Host "Dist directory: $distDir" -ForegroundColor Green

# Try to find Inno Setup (ISCC.exe) - allow overriding via -IsccPath parameter
$iscc = $null
if ($IsccPath) {
    if (Test-Path $IsccPath) {
        $iscc = $IsccPath
        Write-Host "Using provided ISCC path: $iscc" -ForegroundColor Green
    } else {
        Write-Warning "Provided ISCC path not found: $IsccPath"
    }
}

if (-not $iscc) {
    $possibleIscc = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $possibleIscc) {
        if (Test-Path $p) { $iscc = $p; break }
    }
}

if (-not $iscc) {
    Write-Warning "Inno Setup compiler (ISCC.exe) not found in expected locations and no valid -IsccPath provided."
    Write-Host "You can install Inno Setup (https://jrsoftware.org/isinfo.php) and re-run this script, or run ISCC manually using the .iss file in scripts\\installer." -ForegroundColor Yellow
    Write-Host "PyInstaller build is ready in: $distDir" -ForegroundColor Green
    Pop-Location
    return
}

# Build installer via ISCC
$issPath = Join-Path $scriptDir 'installer\gcode_installer.iss'
if (-not (Test-Path $issPath)) {
    Write-Error "Inno Setup script not found at $issPath"
    Pop-Location
    exit 1
}

# ISCC supports preprocessor definitions; we pass DistPath to the script
$cmd = "& `"$iscc`" /DDistPath=`"$distDir`" `"$issPath`""
Write-Host "Running ISCC to create installer..." -ForegroundColor Cyan
Invoke-Expression $cmd
if ($LASTEXITCODE -eq 0) {
    Write-Host "Installer created in scripts\installer\..\installer_output (see OutputDir in .iss)" -ForegroundColor Green
} else {
    Write-Error "ISCC failed with exit code $LASTEXITCODE"
}

Pop-Location
