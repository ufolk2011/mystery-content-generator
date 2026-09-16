@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo กำลังเตรียมโปรแกรมครั้งแรก...
  "C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
)
echo กำลังอัปเดตสคริปต์ไทย/อังกฤษ...
set "BRANCH=cursor/restore-english-scripts-5125"
set "BASE=https://raw.githubusercontent.com/ufolk2011/mystery-content-generator/%BRANCH%"
curl -fsSL -o "app.py" "%BASE%/app.py"
curl -fsSL -o "script_utils.py" "%BASE%/script_utils.py"
curl -fsSL -o "studio_update.py" "%BASE%/studio_update.py"
curl -fsSL -o "audio_timeline.py" "%BASE%/audio_timeline.py"
".venv\Scripts\python.exe" studio_update.py
echo กำลังตรวจไลบรารี...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
