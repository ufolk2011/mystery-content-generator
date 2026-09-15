@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo กำลังเตรียมโปรแกรมครั้งแรก...
  "C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
)
echo กำลังอัปเดตหน้าไทม์ไลน์เสียง...
curl -fsSL -o "studio_update.py" "https://raw.githubusercontent.com/ufolk2011/mystery-content-generator/cursor/mascot-clip-3f0c/studio_update.py"
".venv\Scripts\python.exe" studio_update.py
echo กำลังตรวจไลบรารี...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
