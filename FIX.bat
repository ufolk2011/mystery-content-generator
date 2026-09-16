@echo off
chcp 65001 >nul
set "ROOT=C:\Users\User\mystery-content-generator"
if not exist "%ROOT%\app.py" set "ROOT=%USERPROFILE%\mystery-content-generator"
if not exist "%ROOT%\app.py" set "ROOT=%~dp0"
cd /d "%ROOT%"
echo.
echo Updating: %CD%
echo.

set "BRANCH=cursor/restore-english-scripts-5125"
set "BASE=https://raw.githubusercontent.com/ufolk2011/mystery-content-generator/%BRANCH%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri '%BASE%/app.py' -OutFile 'app.py'"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri '%BASE%/script_utils.py' -OutFile 'script_utils.py'"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri '%BASE%/studio_update.py' -OutFile 'studio_update.py'"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing -Uri '%BASE%/audio_timeline.py' -OutFile 'audio_timeline.py'"

if exist ".git" (
  git fetch origin %BRANCH%
  git checkout origin/%BRANCH% -- app.py script_utils.py audio_timeline.py studio_update.py lip_sync.py tts.py run.bat
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" studio_update.py
) else (
  py -3 studio_update.py
)

echo.
echo Done. Close the old localhost window, then start run.bat
pause
