@echo off
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0Install.ps1"
if errorlevel 1 pause
