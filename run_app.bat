@echo off
setlocal
cd /d "%~dp0"
python scripts\run_app.py
if errorlevel 1 (
  echo.
  echo The app failed to start.
  echo Make sure Python and the dependencies are installed:
  echo   pip install -r requirements.txt
  pause
)

