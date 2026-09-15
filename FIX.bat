@echo off
chcp 65001 >nul
set "ROOT=C:\Users\User\mystery-content-generator"
if not exist "%ROOT%\app.py" set "ROOT=%USERPROFILE%\mystery-content-generator"
if not exist "%ROOT%\app.py" set "ROOT=%~dp0"
cd /d "%ROOT%"
echo.
echo Updating: %CD%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/ufolk2011/mystery-content-generator/cursor/mascot-clip-3f0c/studio_update.py' -OutFile 'studio_update.py'"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/ufolk2011/mystery-content-generator/cursor/mascot-clip-3f0c/audio_timeline.py' -OutFile 'audio_timeline.py'"

if exist ".git" (
  git fetch origin cursor/mascot-clip-3f0c
  git checkout origin/cursor/mascot-clip-3f0c -- audio_timeline.py studio_update.py lip_sync.py tts.py run.bat
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" studio_update.py
) else (
  py -3 studio_update.py
)

echo.
echo Done. Close the old localhost window, then start run.bat
pause
