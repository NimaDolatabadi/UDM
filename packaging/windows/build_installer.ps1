# Build UDM.exe with PyInstaller, then a portable zip and an Inno Setup installer.
#
# Usage: pwsh packaging/windows/build_installer.ps1
# Requires: Pillow (icon conversion) and Inno Setup 6 (iscc.exe).
# Output: dist\UDM-<version>-windows-x64-setup.exe, dist\UDM-<version>-windows-x64.zip
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$Version = (Get-Content "$Root\VERSION" -Raw).Trim()
$Build = "$Root\build\windows"
$Dist = "$Root\dist"

if (Test-Path $Build) { Remove-Item $Build -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Build, $Dist | Out-Null

Write-Host "Creating application icon"
$Icon = "$Build\UDM.ico"
& $Python -c "import sys; from PIL import Image; Image.open(sys.argv[1]).save(sys.argv[2], sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])" "$Root\logo.png" $Icon
if ($LASTEXITCODE -ne 0) { throw "Icon conversion failed" }

Write-Host "Building UDM $Version"
$env:UDM_ICON = $Icon
& $Python -m PyInstaller --noconfirm --clean --distpath "$Build\dist" --workpath "$Build\work" "$Root\packaging\udm.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "Packaging portable zip"
Compress-Archive -Path "$Build\dist\UDM" -DestinationPath "$Dist\UDM-$Version-windows-x64.zip" -Force

Write-Host "Packaging installer"
$Iscc = if ($env:ISCC) { $env:ISCC } else { "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
& $Iscc "/DAppVersion=$Version" "/DSourceDir=$Build\dist\UDM" "/DIconFile=$Icon" "/DOutputDir=$Dist" "$Root\packaging\windows\udm.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

Write-Host "Done: $Dist"
