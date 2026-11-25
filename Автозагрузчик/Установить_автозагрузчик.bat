@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set "VENV=%LOCALAPPDATA%\DzenDraftLoader\venv"
py -3.11 -m venv "%VENV%" || goto fail
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt || goto fail
"%VENV%\Scripts\python.exe" -m playwright install chromium || goto fail
if not exist "%LOCALAPPDATA%\DzenDraftLoader\config.json" copy /y config.example.json "%LOCALAPPDATA%\DzenDraftLoader\config.json" >nul
"%VENV%\Scripts\python.exe" main.py login || goto fail
pause
exit /b 0
:fail
echo See the messages above. Install Python 3.11 and run the installer first if needed.
pause
exit /b 1
