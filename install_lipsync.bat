@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" install_lipsync.py
) else (
  python install_lipsync.py
)
echo.
pause
