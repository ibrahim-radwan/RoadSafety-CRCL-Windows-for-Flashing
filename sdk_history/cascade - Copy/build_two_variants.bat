@echo off
REM ============================================================================
REM  Build all 4 cascade configs x 2 variants (infinite frames + 1 frame)
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

pushd "%~dp0"

echo ============================================================================
echo  Step 1: Generate SysConfig files
echo ============================================================================
gmake syscfg
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: SysConfig generation failed.
    popd
    EXIT /B 1
)

REM ============================================================================
REM  VARIANT 1: Infinite frames (CFG_NUM_FRAMES = 0)
REM  cascade_config.h already has 0 — just build
REM ============================================================================
echo.
echo ############################################################################
echo  VARIANT 1: Infinite frames (numFrames = 0)
echo ############################################################################

call :BuildConfig CASCADE_CFG_LONGRANGE        longrange        build_longrange_inf
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_SHORTRANGE       shortrange       build_shortrange_inf
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_SHORTRANGE_CALIB shortrange_calib build_shortrange_calib_inf
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_VERYLONGRANGE    verylongrange    build_verylongrange_inf
IF %ERRORLEVEL% NEQ 0 goto :error

REM ============================================================================
REM  VARIANT 2: Single frame (CFG_NUM_FRAMES = 1)
REM  Patch cascade_config.h in-place
REM ============================================================================
echo.
echo ############################################################################
echo  VARIANT 2: Single frame (numFrames = 1)
echo ############################################################################

REM Replace CFG_NUM_FRAMES 0 -> 1
powershell -Command "(Get-Content 'am273x\cascade_config.h') -replace '#define CFG_NUM_FRAMES\s+\(0U\)', '#define CFG_NUM_FRAMES                (1U)' | Set-Content 'am273x\cascade_config.h'"

call :BuildConfig CASCADE_CFG_LONGRANGE        longrange        build_longrange_1frame
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_SHORTRANGE       shortrange       build_shortrange_1frame
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_SHORTRANGE_CALIB shortrange_calib build_shortrange_calib_1frame
IF %ERRORLEVEL% NEQ 0 goto :error
call :BuildConfig CASCADE_CFG_VERYLONGRANGE    verylongrange    build_verylongrange_1frame
IF %ERRORLEVEL% NEQ 0 goto :error

echo.
echo ============================================================================
echo  All 8 builds completed successfully!
echo ============================================================================
popd
EXIT /B 0

REM ============================================================================
:BuildConfig
set CFG_DEFINE=%~1
set CFG_LABEL=%~2
set OUT_DIR=am273x\%~3

echo.
echo  Building: %~3 (define: %CFG_DEFINE%)
echo --------------------------------------------

gmake mssTestClean 2>nul
gmake mssTest CASCADE_CONFIG=%CFG_DEFINE%
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed for %~3
    EXIT /B 1
)

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
copy /Y "am273x\am273x_cascade_mss.xer5f" "%OUT_DIR%\" >nul 2>&1
copy /Y "am273x\am273x_cascade_mss.bin"    "%OUT_DIR%\" >nul 2>&1
copy /Y "am273x\am273x_cascade_mss.map"    "%OUT_DIR%\" >nul 2>&1
copy /Y "C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\config\cascade_%CFG_LABEL%.cfg" "%OUT_DIR%\" >nul 2>&1

echo  [OK] %~3 -^> %OUT_DIR%\am273x_cascade_mss.xer5f
EXIT /B 0

:error
echo.
echo ERROR: Build process failed.
popd
EXIT /B 1
