@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo กำลังเตรียมโปรแกรมครั้งแรก...
  "C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
