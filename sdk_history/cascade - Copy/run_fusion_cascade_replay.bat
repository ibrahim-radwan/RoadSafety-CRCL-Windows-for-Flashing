@echo off
setlocal EnableExtensions
REM Launcher for RoadSafetyOnTwoWheelers FusionApp cascade_heatmap_replay.py
REM using MCU+ SDK cascade JSON configs under am273x\build_* .
REM Usage: double-click, or from cmd:
REM   run_fusion_cascade_replay.bat
REM   run_fusion_cascade_replay.bat --max-frames 5
REM   run_fusion_cascade_replay.bat --config "%~dp0am273x\build_longrange\cascade_longrange_config.json"

set "HERE=%~dp0"
set "FUSION_ROOT=C:\Users\RadarDemo\RoadSafetyOnTwoWheelers\FusionApp"
set "SCRIPT=%FUSION_ROOT%\cascade_heatmap_replay.py"

REM Default: short-range cascade JSON (edit to build_longrange / build_verylongrange / build_shortrange_calib)
if not defined CONFIG set "CONFIG=%HERE%am273x\build_shortrange\cascade_shortrange_config.json"

REM Default DCA / PostProc frames directory (override with --input-dir)
if not defined INPUT_DIR set "INPUT_DIR=C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\data\frames"

if not exist "%SCRIPT%" (
  echo ERROR: Fusion script not found:
  echo   "%SCRIPT%"
  echo Edit FUSION_ROOT in: "%~f0"
  exit /b 1
)
if not exist "%CONFIG%" (
  echo ERROR: Config JSON not found:
  echo   "%CONFIG%"
  exit /b 1
)

python "%SCRIPT%" --config "%CONFIG%" --input-dir "%INPUT_DIR%" --pattern "*.bin" --hold %*

endlocal
exit /b %ERRORLEVEL%
