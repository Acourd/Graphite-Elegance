@echo off
REM Isoform launcher - runs the shared engine with this theme's config.
setlocal
for %%I in ("%~dp0..") do set "THEMEDIR=%%~fI"
set "ENGINE=%~dp0..\..\Tools\icon_engine.py"
set "CONFIG=%THEMEDIR%\theme_horizon_glow.json"
py -3 "%ENGINE%" --config "%CONFIG%" %* || python "%ENGINE%" --config "%CONFIG%" %*
if errorlevel 1 pause
endlocal
