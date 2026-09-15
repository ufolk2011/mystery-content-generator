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
INFO_NEEDLE = "เลือกเรื่องจากแท็บ 1 หรือเรื่องที่เก็บไว้ แล้วแตกฉากหาคลิปประกอบได้ด้านล่าง"
SUBHEADER_NEEDLE = "อัปโหลดไฟล์เสียงพากย์เพื่อสร้างไทม์ไลน์ภาพประกอบ"


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


def _newline_at(text, idx):
    return "\r\n" if "\r\n" in text[idx : idx + 80] else "\n"


def _inject_block(newline):
    return (
        f"{newline}    try:{newline}"
        f"        from audio_timeline import render_audio_timeline_page{newline}"
        f"        render_audio_timeline_page(embed=True){newline}"
        f"    except Exception as timeline_err:{newline}"
        f"        st.error(timeline_err){newline}"
        f"        st.file_uploader({newline}"
        f'            "เลือกไฟล์เสียงพากย์ (.mp3 / .wav / .m4a)",{newline}'
        f'            type=["mp3", "wav", "m4a", "aac", "ogg"],{newline}'
        f'            key="fixed_voice_upload",{newline}'
        f"        ){newline}"
    )


def _already_has_uploader(text):
    return (
        TAB2_INJECT_MARK in text
        or "timeline_voice_upload" in text
        or "fixed_voice_upload" in text
        or "standalone_voice_upload" in text
        or "embed_voice_upload" in text
    )


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

    if not _already_has_uploader(text):
        injected = False
        for needle in (INFO_NEEDLE, SUBHEADER_NEEDLE):
            idx = text.find(needle)
            if idx < 0:
                continue
            line_start = text.rfind("\n", 0, idx) + 1
            nl = _newline_at(text, idx)
            text = text[:line_start] + _inject_block(nl).lstrip("\r\n") + text[line_start:]
            injected = True
            break
        if not injected:
            for marker in ("with tab2:", "with tab_2:", "with timeline_tab:"):
                idx = text.find(marker)
                if idx < 0:
                    continue
                nl = _newline_at(text, idx)
                end = text.find(nl, idx)
                if end < 0:
                    end = len(text)
                text = text[: end + len(nl)] + _inject_block(nl) + text[end + len(nl) :]
                break
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


def candidate_roots():
    roots = [repo_root()]
    home = Path.home() / "mystery-content-generator"
    hardcoded = Path(r"C:\Users\User\mystery-content-generator")
    for item in (home, hardcoded):
        if item not in roots:
            roots.append(item)
    return [path for path in roots if (path / "app.py").is_file()]


def apply_update(root=None):
    if root is not None:
        targets = [Path(root)]
    else:
        targets = candidate_roots() or [repo_root()]
    changed = False
    for target in targets:
        changed = ensure_support_files(target) or changed
        changed = patch_app_py(target) or changed
    return changed


if __name__ == "__main__":
    apply_update()
