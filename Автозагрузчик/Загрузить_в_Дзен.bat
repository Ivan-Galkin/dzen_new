@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set "VENV=%LOCALAPPDATA%\DzenDraftLoader\venv"
if not exist "%VENV%\Scripts\python.exe" goto fail
"%VENV%\Scripts\python.exe" main.py run || goto fail
pause
exit /b 0
:fail
echo See the messages above. Install Python 3.11 and run the installer first if needed.
pause
exit /b 1
