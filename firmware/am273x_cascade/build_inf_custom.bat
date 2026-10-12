@echo off
REM ============================================================================
REM  Build all cascade variants with CASCADE_INF=1 (infinite frames).
REM  Uses the makefile's own mssTestInf target, which passes CASCADE_INF=1 and
REM  copies outputs into am273x\build_*_inf\ — matching the firmware currently
REM  in use. Do NOT use build_all_configs.bat or build_two_variants.bat: their
REM  gmake lines omit CASCADE_INF=1 and produce single-frame binaries.
REM ============================================================================
set MMWAVE_SDK_DEVICE=am273x
set DOWNLOAD_FROM_CCS=yes

set MMWAVE_SDK_TOOLS_INSTALL_PATH=C:/ti/mmwave_mcuplus_sdk_04_04_00_01
set MMWAVE_SDK_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mmwave_mcuplus_sdk_04_04_00_01

set CCS_INSTALL_PATH=C:/ti/ccs2050
set R5F_CLANG_INSTALL_PATH=%CCS_INSTALL_PATH%/ccs/tools/compiler/ti-cgt-armllvm_4.0.4.LTS
set C66X_CODEGEN_INSTALL_PATH=%CCS_INSTALL_PATH%/ccs/tools/compiler/ti-cgt-c6000_8.5.0.LTS
set XDC_INSTALL_PATH=%CCS_INSTALL_PATH%/ccs/utils

set MMWAVE_XWR2XXX_DFP_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mmwave_dfp_02_02_04_00
SET MCU_PLUS_AM273X_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mcu_plus_sdk_am273x_08_05_00_24
SET MCU_PLUS_AWR294X_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mcu_plus_sdk_awr294x_08_06_00_28
SET SYSCONFIG_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/sysconfig_1.14.0
set MMWAVE_AWR294X_DFP_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mmwave_dfp_02_04_08_01
set AWR294X_RADARSS_IMAGE_BIN=%MMWAVE_AWR294X_DFP_INSTALL_PATH%/firmware/radarss/xwr2xxx_radarss_metarprc.bin
set C66x_DSPLIB_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/dsplib_c66x_3_4_0_0
set C66x_MATHLIB_INSTALL_PATH=%MMWAVE_SDK_TOOLS_INSTALL_PATH%/mathlib_c66x_3_1_2_1

set PATH=%CCS_INSTALL_PATH%/ccs/utils/bin;%CCS_INSTALL_PATH%/ccs/utils/cygwin;%XDC_INSTALL_PATH%;%XDC_INSTALL_PATH%/bin;%PATH%

echo -----------------------------------------------
echo   CCS:      %CCS_INSTALL_PATH%
echo   Compiler: %R5F_CLANG_INSTALL_PATH%
echo   SDK:      %MMWAVE_SDK_INSTALL_PATH%
echo -----------------------------------------------

pushd "%~dp0"
gmake mssTestInf MMWAVE_SDK_DEVICE_TYPE=am273x
set BUILD_RESULT=%ERRORLEVEL%
popd

IF %BUILD_RESULT% NEQ 0 (
    echo.
    echo ERROR: build failed with code %BUILD_RESULT%
    EXIT /B 1
)
echo.
echo ===== BUILT ARTEFACTS =====
powershell -NoProfile -Command ^
  "$f = Get-ChildItem -Path 'am273x' -Recurse -Filter 'am273x_cascade_mss.xer5f' |" ^
  "     Where-Object { $_.Directory.Name -like 'build_*_inf' } |" ^
  "     Sort-Object { $_.Directory.Name };" ^
  "if (-not $f) { Write-Host 'NO ARTEFACTS FOUND'; exit 1 };" ^
  "$f | ForEach-Object { '{0,-28} {1,9:N0} B  {2}' -f $_.Directory.Name, $_.Length, (Get-FileHash $_.FullName -Algorithm MD5).Hash };" ^
  "$h = $f | ForEach-Object { (Get-FileHash $_.FullName -Algorithm MD5).Hash };" ^
  "$u = ($h | Select-Object -Unique).Count;" ^
  "Write-Host '';" ^
  "Write-Host ('{0} variant(s) in build_*_inf, {1} distinct hash(es)' -f $f.Count, $u);" ^
  "if ($f.Count -ne $u) { Write-Host '*** FAIL: two variants are byte-identical - a -D define did not take effect' } else { Write-Host 'OK: all variants distinct' }"
EXIT /B 0