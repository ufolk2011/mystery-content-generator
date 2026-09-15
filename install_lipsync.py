"""Insert the lip-sync item into a local app.py sidebar menu if it is missing."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
IMPORT_LINE = "from lip_sync import render_lip_sync_page"


def _add_import(text: str) -> str:
    if IMPORT_LINE in text:
        return text
    if "from tts import" in text:
        return text.replace("from tts import", IMPORT_LINE + "\nfrom tts import", 1)
    return IMPORT_LINE + "\n" + text


def _patch_key_radio(text: str) -> str:
    text = re.sub(
        r'\["studio",\s*"crop",\s*"subtitle"\]',
        '["studio", "crop", "subtitle", "lipsync"]',
        text,
        count=1,
    )
    text = re.sub(
        r"\['studio',\s*'crop',\s*'subtitle'\]",
        "['studio', 'crop', 'subtitle', 'lipsync']",
        text,
        count=1,
    )
    if re.search(r'"lipsync"\s*:', text) is None and '"subtitle": "Auto Subtitle"' in text:
        text = text.replace(
            '"subtitle": "Auto Subtitle",',
            '"subtitle": "Auto Subtitle",\n        "lipsync": "ลิปซิงค์คาแรกเตอร์",',
            1,
        )
        if '"lipsync": "ลิปซิงค์คาแรกเตอร์"' not in text:
            text = text.replace(
                '"subtitle": "Auto Subtitle"',
                '"subtitle": "Auto Subtitle",\n        "lipsync": "ลิปซิงค์คาแรกเตอร์"',
                1,
            )
    return text


def _patch_thai_radio(text: str) -> str:
    replacements = [
        (
            '["ค้นหาเรื่อง", "✂️ ครอปคลิป 9:16", "Auto Subtitle"]',
            '["ค้นหาเรื่อง", "✂️ ครอปคลิป 9:16", "Auto Subtitle", "ลิปซิงค์คาแรกเตอร์"]',
        ),
        (
            '["ค้นหาเรื่อง", "ครอปคลิป 9:16", "Auto Subtitle"]',
            '["ค้นหาเรื่อง", "ครอปคลิป 9:16", "Auto Subtitle", "ลิปซิงค์คาแรกเตอร์"]',
        ),
    ]
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)
    return text


def _add_route(text: str) -> str:
    if "render_lip_sync_page()" in text:
        return text
    route_app_page = (
        'if app_page == "lipsync":\n'
        "    render_lip_sync_page()\n"
        "    st.stop()\n"
    )
    route_menu = (
        'if menu == "ลิปซิงค์คาแรกเตอร์":\n'
        "    render_lip_sync_page()\n"
        "    st.stop()\n"
    )
    for needle, route in (
        ('if app_page == "crop"', route_app_page),
        ('if app_page == "subtitle"', route_app_page),
        ('if menu == "ครอปคลิป', route_menu),
        ('if menu == "✂️ ครอปคลิป', route_menu),
        ('if menu == "Auto Subtitle"', route_menu),
    ):
        idx = text.find(needle)
        if idx != -1:
            return text[:idx] + route + text[idx:]
    hero = 'st.markdown(\'<div class="hero-kicker">'
    idx = text.rfind(hero)
    if idx != -1:
        return text[:idx] + route_menu + "\n" + text[idx:]
    return text + "\n" + route_menu


def patch_app_text(text: str) -> str:
    text = _add_import(text)
    text = _patch_key_radio(text)
    text = _patch_thai_radio(text)
    text = _add_route(text)
    return text


def install() -> str:
    if not APP.is_file():
        return "ไม่พบ app.py ในโฟลเดอร์นี้"
    original = APP.read_text(encoding="utf-8")
    updated = patch_app_text(original)
    if updated == original:
        if "ลิปซิงค์คาแรกเตอร์" in original and "render_lip_sync_page" in original:
            return "เมนู ลิปซิงค์คาแรกเตอร์ มีอยู่ใน app.py แล้ว"
        return "หาแถบเมนูใน app.py ไม่เจอ จึงไม่ได้แก้ไฟล์"
    backup = APP.with_suffix(".py.bak-lipsync")
    if not backup.exists():
        shutil.copy2(APP, backup)
    APP.write_text(updated, encoding="utf-8")
    return "เพิ่มเมนู ลิปซิงค์คาแรกเตอร์ ใน app.py แล้ว — ปิด Streamlit แล้วเปิด run.bat ใหม่"


if __name__ == "__main__":
    print(install())
