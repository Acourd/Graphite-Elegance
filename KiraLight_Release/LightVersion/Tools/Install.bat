@echo off
py -3 "%~dp0apply_desktop_icons.py" || python "%~dp0apply_desktop_icons.py"
if errorlevel 1 pause
