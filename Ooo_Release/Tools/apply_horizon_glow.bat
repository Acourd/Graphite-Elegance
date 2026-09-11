@echo off
REM Isoform launcher - runs the shared engine with this theme's config.
setlocal
for %%I in ("%~dp0..") do set "THEMEDIR=%%~fI"
set "ENGINE=%~dp0..\..\Tools\icon_engine.py"
set "CONFIG=%THEMEDIR%\theme_horizon_glow.json"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [ERROR] Python 3 no encontrado en PATH.
  pause
  exit /b 1
)

%PY% "%ENGINE%" --config "%CONFIG%" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [ERROR] El motor termino con codigo %RC%.
  pause
)
endlocal & exit /b %RC%