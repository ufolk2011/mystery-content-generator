@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if "%SADTALKER_HOME%"=="" set "SADTALKER_HOME=%USERPROFILE%\SadTalker"
if not exist "%SADTALKER_HOME%\inference.py" (
  echo ไม่พบ SadTalker ที่ %SADTALKER_HOME%
  echo clone ก่อน: git clone https://github.com/OpenTalker/SadTalker.git "%SADTALKER_HOME%"
  pause
  exit /b 1
)

echo ใช้โฟลเดอร์: %SADTALKER_HOME%
echo.

set "PY310="
py -3.10 -c "import sys; print(sys.executable)" >"%TEMP%\sadtalker-py310.txt" 2>nul
if exist "%TEMP%\sadtalker-py310.txt" (
  set /p PY310=<"%TEMP%\sadtalker-py310.txt"
)
if "%PY310%"=="" if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY310=%LocalAppData%\Programs\Python\Python310\python.exe"
if "%PY310%"=="" if exist "%ProgramFiles%\Python310\python.exe" set "PY310=%ProgramFiles%\Python310\python.exe"

if "%PY310%"=="" (
  echo SadTalker ใช้กับ Python 3.12 ไม่ได้ — เลยไปคอมไพล์ numpy แล้วเจอ error pkgutil.ImpImporter
  echo.
  echo ติดตั้ง Python 3.10 จาก:
  echo https://www.python.org/downloads/release/python-31011/
  echo เลือก Windows installer 64-bit แล้วติ๊ก Add python.exe to PATH
  echo ติดตั้งเสร็จแล้วรันไฟล์นี้ใหม่
  pause
  exit /b 1
)

echo พบ Python 3.10: %PY310%
if not exist "%SADTALKER_HOME%\.venv\Scripts\python.exe" (
  echo กำลังสร้าง .venv ในโฟลเดอร์ SadTalker...
  "%PY310%" -m venv "%SADTALKER_HOME%\.venv"
)

set "VENV=%SADTALKER_HOME%\.venv\Scripts\python.exe"
echo อัปเกรด pip / setuptools ^(กัน error ImpImporter^)
"%VENV%" -m pip install -U pip "setuptools>=69" wheel
echo ติดตั้ง numpy จากวงล้อสำเร็จรูป ไม่คอมไพล์เอง
"%VENV%" -m pip install "numpy==1.23.5" --only-binary=:all:
if errorlevel 1 (
  echo ติดตั้ง numpy ไม่สำเร็จ — ตรวจว่า Python เป็น 3.10 64-bit
  pause
  exit /b 1
)

cd /d "%SADTALKER_HOME%"
if exist requirements.txt (
  echo ติดตั้งชุด SadTalker จาก requirements.txt
  "%VENV%" -m pip install -r requirements.txt --only-binary=:all:
  if errorlevel 1 (
    echo บางแพ็กเกจไม่มีวงล้อ จะลองติดตั้งแบบปกติ ^(ไม่ build numpy ซ้ำ^)
    "%VENV%" -m pip install -r requirements.txt
  )
)

echo.
echo เสร็จแล้ว เปิด run.bat ของ Mystery Content Studio ใหม่
echo ระบบจะชี้ SADTALKER_HOME ไปที่ %SADTALKER_HOME% อัตโนมัติถ้ามีไฟล์ inference.py
pause
