@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
"%LOCALAPPDATA%\DzenDraftLoader\venv\Scripts\python.exe" pilot.py
set "result=%errorlevel%"
pause
exit /b %result%
