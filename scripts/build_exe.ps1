<#
Simple build script for PyInstaller. Assumes you activated the venv first:
  .\.venv\Scripts\Activate.ps1
  .\scripts\build_exe.ps1

Usage:
  .\scripts\build_exe.ps1      # one-dir build
  .\scripts\build_exe.ps1 -OneFile  # onefile build
#>

param([switch]$OneFile)

Write-Host 'Ensure PyInstaller is installed in the active environment' -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install pyinstaller

# Determine project root and entry script (GUI.py is in the repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $scriptDir '..')
$entryScript = Join-Path $projectRoot 'GUI.py'

# Use absolute paths for data files so PyInstaller finds them regardless of working dir
$root = $projectRoot.Path
$imagesSrc = Join-Path $root 'images'
$translationsSrc = Join-Path $root 'translations.json'
$configSrc = Join-Path $root 'config.json'

# Ensure dist/work go to project-level folders (not scripts\dist)
$distPath = Join-Path $root 'dist'
$workPath = Join-Path $root 'build'
$extraArgs = "--distpath=`"$distPath`" --workpath=`"$workPath`""

$baseArgs = '--noconfirm --clean --windowed --name Gcode-Generator'
# On Windows PowerShell we must quote the --add-data values and use '=' so semicolons don't split the command
$dataArgs = "--add-data=`"$imagesSrc;images`" --add-data=`"$translationsSrc;.`" --add-data=`"$configSrc;.`""

if ($OneFile) {
  $cmd = "pyinstaller $baseArgs --onefile $dataArgs $extraArgs `"$entryScript`""
} else {
  $cmd = "pyinstaller $baseArgs --onedir $dataArgs $extraArgs `"$entryScript`""
}

Write-Host 'Running:' $cmd -ForegroundColor Green
Invoke-Expression $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Build complete. See dist\Gcode-Generator\' -ForegroundColor Green
} else {
    Write-Host "Build failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
