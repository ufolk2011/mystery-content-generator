#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
echo
echo "เปิดเบราว์เซอร์ไปที่ http://127.0.0.1:8787"
echo
exec .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8787
