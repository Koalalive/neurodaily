param(
  [Parameter(Mandatory = $true)][string]$ReleaseDir,
  [Parameter(Mandatory = $true)][string]$Target
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$iconPath = (Resolve-Path "$PSScriptRoot/tauri/src-tauri/icons/icon.ico").Path
$installer = (Get-ChildItem -LiteralPath (Join-Path $ReleaseDir "bundle/nsis") -Filter "*-setup.exe").FullName
if (@($installer).Count -ne 1) { throw "Expected one NSIS installer in $ReleaseDir" }
$paths = @(
  (Join-Path $ReleaseDir "neurodaily-desktop.exe"),
  $installer,
  "$PSScriptRoot/tauri/src-tauri/binaries/neurodaily-server-$Target.exe"
)

foreach ($path in $paths) {
  $absolute = (Resolve-Path $path).Path
  $actualIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($absolute)
  if ($null -eq $actualIcon) { throw "No embedded application icon in $absolute" }
  $actual = $actualIcon.ToBitmap()
  $referenceIcon = [System.Drawing.Icon]::new($iconPath, $actual.Width, $actual.Height)
  $reference = $referenceIcon.ToBitmap()
  try {
    if ($actual.Size -ne $reference.Size) { throw "Unexpected icon dimensions in $absolute" }
    $difference = 0
    for ($x = 0; $x -lt $actual.Width; $x++) {
      for ($y = 0; $y -lt $actual.Height; $y++) {
        $pixel = $actual.GetPixel($x, $y)
        $expected = $reference.GetPixel($x, $y)
        $difference += [Math]::Abs([int]$pixel.R - [int]$expected.R)
        $difference += [Math]::Abs([int]$pixel.G - [int]$expected.G)
        $difference += [Math]::Abs([int]$pixel.B - [int]$expected.B)
      }
    }
    if ($difference / (3 * $actual.Width * $actual.Height) -gt 4) {
      throw "Embedded icon does not match the NeuroDaily logo in $absolute"
    }
    Write-Host "Verified embedded NeuroDaily logo in $(Split-Path -Leaf $absolute)"
  } finally {
    $actual.Dispose()
    $reference.Dispose()
    $actualIcon.Dispose()
    $referenceIcon.Dispose()
  }
}
