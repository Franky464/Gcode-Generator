<#
Helper to produce an installer for the PyInstaller dist output.
Priority:
 - If NSIS (makensis.exe) is available, build NSIS installer using scripts/installer/gcode_installer.nsi
 - Else if 7-Zip (7z.exe) is available, create a 7z SFX archive (self-extracting)
 - Else fall back to a zip archive using Compress-Archive

Usage:
  .\.venv\Scripts\Activate.ps1
  .\scripts\make_nsis_or_sfx.ps1 -DistPath "C:\...\dist"

This script does NOT require admin rights to create archives.
#>

param([string]$DistPath = "$(Resolve-Path '..\dist\Gcode-Generator' -ErrorAction SilentlyContinue)", [string]$OutDir = "installer_output")

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $scriptDir '..')

if (-not $DistPath) {
    $DistPath = Join-Path $projectRoot 'dist\Gcode-Generator'
}

Write-Host "Using DistPath: $DistPath" -ForegroundColor Cyan
if (-not (Test-Path $DistPath)) {
    Write-Error "Dist path not found: $DistPath. Run the PyInstaller build first."
    exit 1
}

$absOut = Join-Path $projectRoot $OutDir
New-Item -ItemType Directory -Path $absOut -Force | Out-Null

# 1) Try NSIS
$makensis = Get-Command makensis.exe -ErrorAction SilentlyContinue
if ($makensis) {
    Write-Host "Found makensis at: $($makensis.Path)" -ForegroundColor Green
    $nsi = Join-Path $scriptDir 'installer\gcode_installer.nsi'
    if (-not (Test-Path $nsi)) { Write-Error "NSI script not found: $nsi"; exit 1 }
    $cmd = "`"$($makensis.Path)`" /DDISTPATH=`"$DistPath`" `"$nsi`""
    Write-Host "Running: $cmd" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -eq 0) { Write-Host "NSIS installer produced (see output)" -ForegroundColor Green; exit 0 }
    else { Write-Warning "makensis failed with exit code $LASTEXITCODE" }
}

# 2) Try 7-Zip self-extracting archive
$seven = Get-Command 7z.exe -ErrorAction SilentlyContinue
if ($seven) {
    Write-Host "Found 7z at: $($seven.Path)" -ForegroundColor Green
    $archive = Join-Path $absOut 'gcode-generator.7z'
    $sfx = Join-Path $absOut 'gcode-generator.exe'
    & $seven.Path a -t7z "$archive" "$DistPath\*" | Out-Null
    # Create basic config for SFX (optional). Use 7z's default SFX module (7z.sfx)
    $sfxModule = Join-Path (Split-Path $seven.Path -Parent) '..\7z.sfx'
    if (-not (Test-Path $sfxModule)) { $sfxModule = "$($seven.Path)" } # fallback
    # Use copy to create simple self-extracting: cat sfx + config + archive
    $config = @"
;!@Install@!UTF-8!
Title="Gcode-Generator"
BeginPrompt="Install Gcode-Generator"
RunProgram="\"GUI.exe\""
;!@InstallEnd@!
"@
    $cfgPath = Join-Path $absOut 'config.txt'
    $config | Out-File -Encoding UTF8 $cfgPath
    # Build SFX: combine 7zSFX + cfg + archive
    $sfxBin = Join-Path $absOut 'gcode-generator-sfx.exe'
    try {
        Get-Content $sfxModule -Encoding Byte -ReadCount 0 | Set-Content -Encoding Byte $sfxBin
        Get-Content $cfgPath -Encoding Byte -ReadCount 0 | Add-Content -Encoding Byte $sfxBin
        Get-Content $archive -Encoding Byte -ReadCount 0 | Add-Content -Encoding Byte $sfxBin
        Write-Host "Created SFX: $sfxBin" -ForegroundColor Green
        exit 0
    } catch {
        Write-Warning "Failed to create SFX: $_"
    }
}

# 3) Fallback: zip using Compress-Archive
$zipOut = Join-Path $absOut 'gcode-generator-dist.zip'
if (Test-Path $zipOut) { Remove-Item $zipOut -Force }
Compress-Archive -Path (Join-Path $DistPath '*') -DestinationPath $zipOut -Force
Write-Host "Created ZIP archive: $zipOut" -ForegroundColor Green
Write-Host "Installer artifacts are in: $absOut" -ForegroundColor Green
