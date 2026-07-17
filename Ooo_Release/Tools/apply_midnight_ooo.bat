@echo off
py -3 "%~dp0apply_midnight_ooo.py" || python "%~dp0apply_midnight_ooo.py"
if errorlevel 1 pause
