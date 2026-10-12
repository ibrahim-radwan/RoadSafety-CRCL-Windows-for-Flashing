@echo off
REM ============================================================================
REM  Build all 4 cascade radar configurations for AWR2243-2X-CAS-EVM
REM  (2-chip cascade, AM273x MSS R5F)
REM
REM  Output folders created under am273x\:
REM    build_longrange\         - Long range (151m, 0.87m res)
REM    build_shortrange\        - Short range (15m, 0.09m res)
REM    build_shortrange_calib\  - Short range calibration
REM    build_verylongrange\     - Very long range (151m, narrower slope)
REM
REM  Each folder contains:
REM    am273x_cascade_mss.xer5f  - R5F executable
REM    am273x_cascade_mss.map    - Linker map
REM    cascade_<mode>.cfg        - Matching PostProc config
REM ============================================================================

REM ============================================================================
REM  Environment Setup (adjust paths if your installation differs)
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

REM Add tools to PATH
set PATH=%CCS_INSTALL_PATH%/ccs/utils/bin;%CCS_INSTALL_PATH%/ccs/utils/cygwin;%XDC_INSTALL_PATH%;%XDC_INSTALL_PATH%/bin;%PATH%

echo -----------------------------------------------
echo mmWave Build Environment Configured
echo   CCS:      %CCS_INSTALL_PATH%
echo   Compiler: %R5F_CLANG_INSTALL_PATH%
echo   SDK:      %MMWAVE_SDK_INSTALL_PATH%
echo -----------------------------------------------

REM Navigate to the cascade build directory (where the makefile lives)
pushd "%~dp0"

echo.
echo ============================================================================
echo  Step 1: Generate SysConfig files (shared by all configurations)
echo ============================================================================
gmake syscfg
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: SysConfig generation failed.
    popd
    EXIT /B 1
)

REM ============================================================================
REM  Build each configuration
REM ============================================================================

call :BuildConfig CASCADE_CFG_LONGRANGE       longrange
IF %ERRORLEVEL% NEQ 0 goto :error

call :BuildConfig CASCADE_CFG_SHORTRANGE      shortrange
IF %ERRORLEVEL% NEQ 0 goto :error

call :BuildConfig CASCADE_CFG_SHORTRANGE_CALIB shortrange_calib
IF %ERRORLEVEL% NEQ 0 goto :error

call :BuildConfig CASCADE_CFG_VERYLONGRANGE   verylongrange
IF %ERRORLEVEL% NEQ 0 goto :error

echo.
echo ============================================================================
echo  All 4 configurations built successfully!
echo ============================================================================
echo.
echo  Output folders:
echo    am273x\build_longrange\am273x_cascade_mss.xer5f
echo    am273x\build_shortrange\am273x_cascade_mss.xer5f
echo    am273x\build_shortrange_calib\am273x_cascade_mss.xer5f
echo    am273x\build_verylongrange\am273x_cascade_mss.xer5f
echo.
popd
EXIT /B 0

REM ============================================================================
REM  Subroutine: BuildConfig <CASCADE_CONFIG_DEFINE> <label>
REM ============================================================================
:BuildConfig
set CFG_DEFINE=%~1
set CFG_LABEL=%~2
set OUT_DIR=am273x\build_%CFG_LABEL%

echo.
echo ============================================================================
echo  Building: %CFG_LABEL% (define: %CFG_DEFINE%)
echo ============================================================================

REM Clean previous objects
gmake mssTestClean 2>nul

REM Build with the selected configuration
gmake mssTest CASCADE_CONFIG=%CFG_DEFINE%
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed for %CFG_LABEL%
    EXIT /B 1
)

REM Create output directory
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

REM Copy build artifacts
copy /Y "am273x\am273x_cascade_mss.xer5f" "%OUT_DIR%\" >nul 2>&1
copy /Y "am273x\am273x_cascade_mss.bin"    "%OUT_DIR%\" >nul 2>&1
copy /Y "am273x\am273x_cascade_mss.map"    "%OUT_DIR%\" >nul 2>&1

REM Copy matching PostProc config
copy /Y "C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\config\cascade_%CFG_LABEL%.cfg" "%OUT_DIR%\" >nul 2>&1

echo  [OK] %CFG_LABEL% -^> %OUT_DIR%\am273x_cascade_mss.xer5f
EXIT /B 0

:error
echo.
echo ERROR: Build process failed.
popd
EXIT /B 1
