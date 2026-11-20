$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "missing .venv; create it first" }

& $Py -m pip install --quiet --upgrade pyinstaller
& $Py -m PyInstaller --clean --noconfirm desktop/sidecar/neurodaily-server.spec

$Triple = (rustc -vV | Select-String '^host:').ToString().Split(' ')[1]
$Dest = "desktop/tauri/src-tauri/binaries/neurodaily-server-$Triple.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
Copy-Item "dist/neurodaily-server.exe" $Dest -Force
Write-Host "sidecar -> $Dest"
