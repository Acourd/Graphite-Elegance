@echo off
py -3 "%~dp0apply_horizon_glow.py" || python "%~dp0apply_horizon_glow.py"
if errorlevel 1 pause
