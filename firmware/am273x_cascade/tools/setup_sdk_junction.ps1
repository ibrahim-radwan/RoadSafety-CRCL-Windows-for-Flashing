# setup_sdk_junction.ps1 - expose this repo's firmware source inside the TI SDK.
#
# The cascade makefile includes ../../../common/mmwave_sdk.mak, so it only
# builds from <SDK>\ti\utils\test\<name>\. Instead of keeping a second copy of
# the source there, create a directory junction that points back at the repo:
#
#   <SDK>\ti\utils\test\cascade_radar  ->  <repo>\firmware\am273x_cascade
#
# Edits made in either place are the same file. Build outputs (obj_am273x\,
# am273x\build_*_inf\, *.xer5f, *.map) land in the repo folder and are ignored
# by .gitignore. A junction needs no admin rights.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File firmware\am273x_cascade\tools\setup_sdk_junction.ps1
param(
  [string] $Sdk  = 'C:\ti\mmwave_mcuplus_sdk_04_04_00_01\mmwave_mcuplus_sdk_04_04_00_01',
  [string] $Name = 'cascade_radar'
)
$ErrorActionPreference = 'Stop'
$Target = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Link   = Join-Path $Sdk "ti\utils\test\$Name"

if (-not (Test-Path (Join-Path $Sdk 'ti\common\mmwave_sdk.mak'))) {
  throw "mmWave SDK not found at $Sdk"
}
if (Test-Path $Link) {
  $item = Get-Item $Link -Force
  if ($item.LinkType -eq 'Junction' -and $item.Target -contains $Target) {
    Write-Host "OK: $Link already points at $Target"
    exit 0
  }
  throw "$Link exists and is not a junction to $Target - move it away first"
}
New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null
Write-Host "Created junction:"
Write-Host "  $Link"
Write-Host "  -> $Target"
