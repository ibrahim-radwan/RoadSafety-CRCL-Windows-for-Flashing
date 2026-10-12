# build_v2_variants.ps1 - build + package _v2 cascade images (2026-10-10).
#
# For each "name=DEFINE" pair: compile with build_one_inf.bat, copy the
# .xer5f/.map into am273x\build_<name>_inf\, then elf2rprc + multicoreImageGen
# straight into the Jetson-layout tree:
#   <Out>\<name>\am273x_cascade_<name>.appimage
#   <Out>\_build_record\<name>\{<name>.rprc, <name>.xer5f, am273x_cascade_mss.map}
# The .rprc is generated from a uniquely named .xer5f inside the build record,
# so the shared-intermediate overwrite hazard of tools\boot cannot occur.
#
# The build runs through the SDK junction (see setup_sdk_junction.ps1): the
# makefile includes ../../../common/mmwave_sdk.mak, so the source must be
# reached from inside ti\utils\test\. The junction points back at this repo.
#
# Usage:
#   .\build_v2_variants.ps1 -Out <firmware dir> -Variants r017m_v2=CASCADE_CFG_R017M_V2,...
param(
  [Parameter(Mandatory)] [string]   $Out,
  [Parameter(Mandatory)] [string[]] $Variants,
  [string] $Src = 'C:\ti\mmwave_mcuplus_sdk_04_04_00_01\mmwave_mcuplus_sdk_04_04_00_01\ti\utils\test\cascade_radar'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path "$Src\build_one_inf.bat")) { throw "SDK junction not found at $Src - run tools\setup_sdk_junction.ps1" }
$Boot = 'C:\ti\mmwave_mcuplus_sdk_04_04_00_01\mcu_plus_sdk_am273x_08_05_00_24\tools\boot'
$Node = 'C:\ti\ccs2050\ccs\tools\node\node.exe'

foreach ($pair in $Variants) {
  $name, $def = $pair -split '='
  $log = Join-Path $env:TEMP "build_$name.log"
  cmd /c "`"$Src\build_one_inf.bat`" $def" *> $log
  if ($LASTEXITCODE -ne 0) { throw "build $name ($def) failed - see $log" }

  $bd = "$Src\am273x\build_${name}_inf"
  New-Item -ItemType Directory -Force $bd | Out-Null
  Copy-Item "$Src\am273x\am273x_cascade_mss.xer5f", "$Src\am273x\am273x_cascade_mss.map" $bd -Force

  $rec = "$Out\_build_record\$name"
  New-Item -ItemType Directory -Force $rec | Out-Null
  Copy-Item "$bd\am273x_cascade_mss.xer5f" "$rec\$name.xer5f" -Force
  Copy-Item "$bd\am273x_cascade_mss.map"   "$rec\am273x_cascade_mss.map" -Force
  Push-Location $rec
  try { & $Node "$Boot\out2rprc\elf2rprc.js" "$rec\$name.xer5f" | Out-Null } finally { Pop-Location }
  if (-not (Test-Path "$rec\$name.rprc")) { throw "elf2rprc produced no $name.rprc" }

  $pkg = "$Out\$name"
  New-Item -ItemType Directory -Force $pkg | Out-Null
  & $Node "$Boot\multicoreImageGen\multicoreImageGen.js" --devID 55 `
      --out "$pkg\am273x_cascade_$name.appimage" "$rec\$name.rprc@0" | Out-Null

  '{0,-18} rprc {1}  appimage {2}' -f $name,
    (Get-FileHash "$rec\$name.rprc" -Algorithm MD5).Hash.ToLower(),
    (Get-FileHash "$pkg\am273x_cascade_$name.appimage" -Algorithm MD5).Hash.ToLower()
}
