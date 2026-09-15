import urllib.request
from pathlib import Path

RAW_BASE = (
    "https://raw.githubusercontent.com/ufolk2011/"
    "mystery-content-generator/cursor/mascot-clip-3f0c/"
)
DOWNLOAD_FILES = ("audio_timeline.py", "studio_update.py")
RADIO_TOKEN = '"ไทม์ไลน์เสียง"'
TAB2_INJECT_MARK = "render_audio_timeline_page(embed=True)"
ROUTE_MARK = 'if menu in ("ไทม์ไลน์เสียง", "ไทม์ไลน์"):'


def repo_root():
    return Path(__file__).resolve().parent


def download_text(name):
    url = RAW_BASE + name
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def ensure_support_files(root=None):
    root = Path(root or repo_root())
    updated = False
    for name in DOWNLOAD_FILES:
        dest = root / name
        try:
            payload = download_text(name)
        except Exception:
            continue
        if not dest.is_file() or dest.read_bytes() != payload:
            dest.write_bytes(payload)
            updated = True
    return updated


def patch_app_text(text):
    original = text
    if RADIO_TOKEN not in text:
        if '"ค้นหาเรื่อง",' in text:
            text = text.replace('"ค้นหาเรื่อง",', '"ค้นหาเรื่อง", "ไทม์ไลน์เสียง",', 1)
        elif "'ค้นหาเรื่อง'," in text:
            text = text.replace("'ค้นหาเรื่อง',", "'ค้นหาเรื่อง', 'ไทม์ไลน์เสียง',", 1)

    if ROUTE_MARK not in text:
        route = (
            "\n"
            'if menu in ("ไทม์ไลน์เสียง", "ไทม์ไลน์"):\n'
            "    from audio_timeline import render_audio_timeline_page\n"
            "    render_audio_timeline_page()\n"
            "    st.stop()\n"
        )
        for anchor in (
            'if menu in ("ลิปซิงค์", "สร้างคลิปมาสคอต"):',
            'if menu == "ลิปซิงค์":',
            'if menu in ("ลิปซิงค์",):',
        ):
            if anchor in text:
                text = text.replace(anchor, route + anchor, 1)
                break

    if TAB2_INJECT_MARK not in text and "timeline_voice_upload" not in text:
        marker = "with tab2:"
        idx = text.find(marker)
        if idx >= 0:
            newline = "\r\n" if "\r\n" in text[idx:idx + 40] else "\n"
            end = text.find(newline, idx)
            if end < 0:
                end = len(text)
            inject = (
                f"{newline}    try:{newline}"
                f"        from audio_timeline import render_audio_timeline_page{newline}"
                f"        render_audio_timeline_page(embed=True){newline}"
                f"    except Exception as timeline_err:{newline}"
                f"        st.error(timeline_err){newline}"
            )
            text = text[: end + len(newline)] + inject + text[end + len(newline) :]
    return text, text != original


def patch_app_py(root=None):
    path = Path(root or repo_root()) / "app.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    patched, changed = patch_app_text(text)
    if changed:
        path.write_text(patched, encoding="utf-8")
    return changed


def apply_update():
    files_changed = ensure_support_files()
    app_changed = patch_app_py()
    return files_changed or app_changed


if __name__ == "__main__":
    apply_update()
