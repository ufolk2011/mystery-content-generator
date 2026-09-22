@echo off
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -r requirements.txt
echo.
echo เปิดเบราว์เซอร์ไปที่ http://127.0.0.1:8787
echo.
python -m uvicorn app:app --host 127.0.0.1 --port 8787
pause
