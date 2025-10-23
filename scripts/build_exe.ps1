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

$baseArgs = '--noconfirm --clean --windowed --name Gcode-Generator'
$dataArgs = "--add-data images;images --add-data translations.json;. --add-data config.json;."

if ($OneFile) {
    $cmd = "pyinstaller $baseArgs --onefile $dataArgs GUI.py"
} else {
    $cmd = "pyinstaller $baseArgs --onedir $dataArgs GUI.py"
}

Write-Host 'Running:' $cmd -ForegroundColor Green
Invoke-Expression $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Build complete. See dist\Gcode-Generator\' -ForegroundColor Green
} else {
    Write-Host "Build failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
