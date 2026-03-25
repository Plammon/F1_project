@echo off
setlocal
cd /d "%~dp0"
python scripts\build_windows_exe.py
if errorlevel 1 (
  echo.
  echo EXE build failed.
  echo Make sure the dependencies are installed:
  echo   pip install -r requirements.txt
  pause
)

