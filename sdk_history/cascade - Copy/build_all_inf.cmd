@echo off
setlocal EnableExtensions
REM Runs gmake testInf (see makefile): all *_inf builds + copy into am273x\build_*_inf.
REM Prepend System32 so checkenv.bat's "find /i" is Windows FIND, not MSYS/Git find.
set "PATH=%SystemRoot%\system32;%SystemRoot%;%PATH%"

set "SDK_WIN=%~dp0..\..\..\..\"
for %%I in ("%SDK_WIN%") do set "SDK_WIN=%%~fI"
set "SETENV=%SDK_WIN%\scripts\windows\setenv.bat"
if not exist "%SETENV%" (
  echo ERROR: setenv.bat not found at "%SETENV%"
  exit /b 1
)

pushd "%~dp0..\..\..\..\scripts\windows" 2>nul
if errorlevel 1 (
  echo ERROR: could not cd to scripts\windows
  exit /b 1
)
call "%SETENV%"
if errorlevel 1 (
  popd
  exit /b 1
)
popd

set "GMAKE="
if exist "%XDC_INSTALL_PATH%\gmake.exe" set "GMAKE=%XDC_INSTALL_PATH%\gmake.exe"
if "%GMAKE%"=="" if exist "%XDC_INSTALL_PATH%\bin\gmake.exe" set "GMAKE=%XDC_INSTALL_PATH%\bin\gmake.exe"
if "%GMAKE%"=="" (
  where gmake.exe >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%G in ('where gmake.exe 2^>nul') do (
      set "GMAKE=%%G"
      goto :have_gmake
    )
  )
)
:have_gmake
if "%GMAKE%"=="" (
  echo ERROR: gmake.exe not found. Install XDC tools ^(see setenv.bat CCS_INSTALL_PATH / XDC_INSTALL_PATH^).
  exit /b 1
)

set "CASCADE_DIR=%~dp0"
for %%I in ("%CASCADE_DIR%") do set "CASCADE_DIR=%%~fI"
cd /d "%CASCADE_DIR%"
if errorlevel 1 exit /b 1

"%GMAKE%" testInf MMWAVE_SDK_DEVICE_TYPE=am273x
exit /b %ERRORLEVEL%
