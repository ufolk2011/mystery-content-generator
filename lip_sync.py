import os
import shutil
import subprocess
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


class LipSyncError(RuntimeError):
    """Raised when a lip-sync pipeline step cannot run."""


def _env_path(name, default=""):
    value = (os.environ.get(name) or default or "").strip().strip('"').strip("'")
    return Path(value).expanduser() if value else None


def _python_bin():
    return os.environ.get("LIPSYNC_PYTHON") or os.environ.get("PYTHON") or shutil.which("python") or "python"


def require_file(path, kind="ไฟล์"):
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise LipSyncError(f"ไม่พบ{kind}: {path}")
    return resolved


def newest_video(folder, exclude_substr="_concat"):
    folder = Path(folder)
    if not folder.exists():
        return None
    videos = [item for item in folder.rglob("*") if item.suffix.lower() in VIDEO_SUFFIXES]
    if not videos:
        return None
    preferred = [item for item in videos if exclude_substr not in item.name]
    pool = preferred or videos
    return max(pool, key=lambda item: item.stat().st_mtime)


def run_command(cmd, cwd=None):
    if not cmd:
        raise LipSyncError("ไม่มีคำสั่งให้รัน")
    completed = subprocess.run(
        [str(part) for part in cmd],
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise LipSyncError(
            f"คำสั่งล้มเหลว ({completed.returncode}): {' '.join(str(part) for part in cmd)}\n{detail}"
        )
    return completed


def ffmpeg_bin():
    found = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def discover_model_home(*folder_names):
    roots = [
        Path.cwd(),
        Path.cwd() / "vendor",
        Path.cwd() / "models",
        Path.home(),
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Downloads",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for name in folder_names:
            candidate = root / name
            if (candidate / "inference.py").is_file():
                return candidate
    return None


def apply_discovered_homes():
    mapping = {
        "SADTALKER_HOME": ("SadTalker", "sadtalker"),
        "WAV2LIP_HOME": ("Wav2Lip", "wav2lip"),
        "LIVEPORTRAIT_HOME": ("LivePortrait", "liveportrait"),
    }
    for env_name, folders in mapping.items():
        if _env_path(env_name):
            continue
        found = discover_model_home(*folders)
        if found:
            os.environ[env_name] = str(found)


def mux_audio(video_path, audio_path, output_path):
    ffmpeg = ffmpeg_bin()
    if not ffmpeg:
        shutil.copy2(video_path, output_path)
        return Path(output_path)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    try:
        run_command(cmd)
    except LipSyncError:
        cmd[cmd.index("-c:v") + 1] = "libx264"
        run_command(cmd)
    return Path(output_path)


def sadtalker_command(audio_path, template_face, result_dir, extra_args=None):
    home = _env_path("SADTALKER_HOME")
    script = _env_path("SADTALKER_SCRIPT")
    if script is None and home:
        for name in ("inference.py", os.path.join("src", "inference.py")):
            candidate = home / name
            if candidate.is_file():
                script = candidate
                break
    if script is None or not script.is_file():
        return None
    cmd = [
        _python_bin(),
        str(script),
        "--driven_audio",
        str(audio_path),
        "--source_image",
        str(template_face),
        "--result_dir",
        str(result_dir),
        "--still",
        "--preprocess",
        os.environ.get("SADTALKER_PREPROCESS", "full"),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd, home if home and home.is_dir() else script.parent


def wav2lip_command(audio_path, template_face, output_video, extra_args=None):
    home = _env_path("WAV2LIP_HOME")
    if home is None or not home.is_dir():
        return None
    script = home / "inference.py"
    checkpoint = _env_path("WAV2LIP_CHECKPOINT") or home / "checkpoints" / "wav2lip_gan.pth"
    if not script.is_file():
        return None
    cmd = [
        _python_bin(),
        str(script),
        "--checkpoint_path",
        str(checkpoint),
        "--face",
        str(template_face),
        "--audio",
        str(audio_path),
        "--outfile",
        str(output_video),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd, home


def live_portrait_command(source_image, driving_video, output_dir, extra_args=None):
    home = _env_path("LIVEPORTRAIT_HOME")
    script = _env_path("LIVEPORTRAIT_SCRIPT")
    if script is None and home:
        candidate = home / "inference.py"
        if candidate.is_file():
            script = candidate
    if script is None or not script.is_file():
        return None
    cmd = [
        _python_bin(),
        str(script),
        "-s",
        str(source_image),
        "-d",
        str(driving_video),
        "-o",
        str(output_dir),
        "--flag_crop_driving_video",
        "--animation_region",
        os.environ.get("LIVEPORTRAIT_REGION", "all"),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd, home if home and home.is_dir() else script.parent


def describe_setup():
    apply_discovered_homes()
    tools = {
        "ffmpeg": bool(ffmpeg_bin()),
        "sadtalker": sadtalker_command("a.wav", "face.jpg", "out") is not None,
        "wav2lip": wav2lip_command("a.wav", "face.jpg", "out.mp4") is not None,
        "liveportrait": live_portrait_command("src.jpg", "drive.mp4", "out") is not None,
        "template_face": bool(_env_path("LIPSYNC_TEMPLATE_FACE") and _env_path("LIPSYNC_TEMPLATE_FACE").is_file()),
    }
    return tools


def generate_still_av_clip(image_path, audio_path, output_path):
    ffmpeg = ffmpeg_bin()
    if not ffmpeg:
        raise LipSyncError(
            "ยังไม่มี ffmpeg สำหรับประกอบคลิป — ในโฟลเดอร์โปรเจกต์รันคำสั่ง "
            "`pip install imageio-ffmpeg` แล้วเปิด run.bat ใหม่"
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        str(output_path),
    ]
    run_command(cmd)
    return output_path


def generate_driving_video(audio_path, template_face_path, output_dir, dry_run=False):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "driving_face.mp4"
    sadtalker = sadtalker_command(audio_path, template_face_path, output_dir / "sadtalker")
    wav2lip = wav2lip_command(audio_path, template_face_path, target)
    chosen = sadtalker or wav2lip
    if chosen is None:
        return None
    cmd, cwd = chosen
    if dry_run:
        return {"command": cmd, "cwd": str(cwd), "output": str(target)}
    (output_dir / "sadtalker").mkdir(parents=True, exist_ok=True)
    before = {item.resolve() for item in output_dir.rglob("*.mp4")}
    run_command(cmd, cwd=cwd)
    produced = newest_video(output_dir)
    if produced is not None and produced.resolve() in before and produced.resolve() != target.resolve():
        candidates = [item for item in output_dir.rglob("*.mp4") if item.resolve() not in before]
        produced = max(candidates, key=lambda item: item.stat().st_mtime) if candidates else produced
    if produced is None:
        raise LipSyncError("โมเดล Audio-to-Video รันจบแล้ว แต่ไม่พบไฟล์ .mp4")
    if produced.resolve() != target.resolve():
        shutil.copy2(produced, target)
    return target


def generate_live_portrait(source_image_path, driving_video_path, output_dir, dry_run=False):
    output_dir = Path(output_dir)
    portrait_dir = output_dir / "liveportrait"
    portrait_dir.mkdir(parents=True, exist_ok=True)
    configured = live_portrait_command(source_image_path, driving_video_path, portrait_dir)
    if configured is None:
        raise LipSyncError(
            "ยังไม่พบ LivePortrait — ตั้งค่า LIVEPORTRAIT_HOME ให้ชี้ไปที่โฟลเดอร์ที่ clone ไว้ "
            "(ต้องมีไฟล์ inference.py)"
        )
    cmd, cwd = configured
    if dry_run:
        return {"command": cmd, "cwd": str(cwd), "output_dir": str(portrait_dir)}
    before = {item.resolve() for item in portrait_dir.rglob("*.mp4")}
    run_command(cmd, cwd=cwd)
    produced = newest_video(portrait_dir)
    if produced is None or produced.resolve() in before:
        candidates = [
            item for item in portrait_dir.rglob("*.mp4") if item.resolve() not in before
        ]
        produced = max(candidates, key=lambda item: item.stat().st_mtime) if candidates else produced
    if produced is None:
        raise LipSyncError("LivePortrait รันจบแล้ว แต่ไม่พบไฟล์วิดีโอผลลัพธ์")
    return produced


def generate_lip_sync_pipeline(
    source_image_path,
    driving_audio_path=None,
    output_dir="output",
    template_face_path=None,
    driving_video_path=None,
    dry_run=False,
):
    """Audio → talking-face driving video → LivePortrait on the mascot still.

    If SadTalker / Wav2Lip / LivePortrait are not installed, fall back to a
    still-image clip with the uploaded voiceover so the button still produces a video.
    """
    apply_discovered_homes()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_image = require_file(source_image_path, "รูปคาแรกเตอร์")
    if source_image.suffix.lower() not in IMAGE_SUFFIXES:
        raise LipSyncError("รูปต้นทางต้องเป็น .jpg / .png / .webp")

    audio_path = None
    if driving_audio_path:
        audio_path = require_file(driving_audio_path, "ไฟล์เสียงพากย์")
        if audio_path.suffix.lower() not in AUDIO_SUFFIXES:
            raise LipSyncError("ไฟล์เสียงต้องเป็น .mp3 / .wav / .m4a")

    driving_video = None
    if driving_video_path:
        driving_video = require_file(driving_video_path, "Driving Video")

    template_face = template_face_path or _env_path("LIPSYNC_TEMPLATE_FACE")
    if template_face:
        template_face = require_file(template_face, "รูปหน้าเทมเพลต")
    elif audio_path:
        template_face = source_image

    can_drive = bool(
        driving_video
        or sadtalker_command("a.wav", "face.jpg", "out")
        or wav2lip_command("a.wav", "face.jpg", "out.mp4")
    )
    can_portrait = live_portrait_command("src.jpg", "drive.mp4", "out") is not None
    final_path = output_dir / "final_mascot_output.mp4"

    if dry_run:
        plan = {"steps": [], "output": str(final_path), "mode": "full"}
        if not can_drive or not can_portrait:
            plan["mode"] = "fallback"
            plan["steps"].append(
                {
                    "command": ["ffmpeg", "-loop", "1", "-i", str(source_image), "-i", str(audio_path or "")],
                    "cwd": str(output_dir),
                }
            )
            return plan
        if driving_video is None:
            plan["steps"].append(
                generate_driving_video(audio_path, template_face, output_dir, dry_run=True)
            )
            driving_video = output_dir / "driving_face.mp4"
        plan["steps"].append(
            generate_live_portrait(source_image, driving_video, output_dir, dry_run=True)
        )
        return plan

    if (not can_drive or not can_portrait) and audio_path:
        print("--- ยังไม่มีโมเดลขยับปาก กำลังประกอบคลิปรูปนิ่งกับเสียงพากย์ ---")
        generate_still_av_clip(source_image, audio_path, final_path)
        print(f"✨ สำเร็จ! เซฟวิดีโอไว้ที่: {final_path}")
        return {"path": str(final_path), "mode": "fallback"}

    if driving_video is None:
        if audio_path is None:
            raise LipSyncError("ต้องมีไฟล์เสียงพากย์ หรือ Driving Video อย่างน้อยอย่างใดอย่างหนึ่ง")
        print("--- [1/2] กำลังแปลงไฟล์เสียงเป็น Driving Video ---")
        driving_video = generate_driving_video(audio_path, template_face, output_dir)
        if driving_video is None:
            generate_still_av_clip(source_image, audio_path, final_path)
            return {"path": str(final_path), "mode": "fallback"}
    else:
        copied = output_dir / "driving_face.mp4"
        shutil.copy2(driving_video, copied)
        driving_video = copied
        print("--- [1/2] ใช้ Driving Video ที่อัปโหลดแล้ว ข้าม Audio-to-Video ---")

    print("--- [2/2] กำลังรัน LivePortrait เพื่อสวมหน้าคาแรกเตอร์จริง ---")
    portrait = generate_live_portrait(source_image, driving_video, output_dir)
    if audio_path and ffmpeg_bin():
        mux_audio(portrait, audio_path, final_path)
    else:
        shutil.copy2(portrait, final_path)
    print(f"✨ สำเร็จ! เซฟวิดีโอไว้ที่: {final_path}")
    return {"path": str(final_path), "mode": "full"}


def _save_upload(upload, folder, prefix):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.name).suffix.lower() or ""
    dest = folder / f"{prefix}{suffix}"
    dest.write_bytes(upload.getbuffer())
    return dest


def render_lip_sync_page():
    import streamlit as st

    st.subheader("🗣️ Mascot Lip-Sync Generator")
    st.write("อัปโหลดรูปมาสคอตและไฟล์เสียงพากย์ เพื่อสร้างปากขยับ")

    col1, col2 = st.columns(2)
    with col1:
        source_image = st.file_uploader(
            "1. อัปโหลดรูปหน้ามาสคอต (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            key="lipsync_source_image",
        )
        if source_image is not None:
            try:
                st.image(source_image, caption="รูปมาสคอต", use_container_width=True)
            except Exception:
                st.caption(f"อัปโหลดแล้ว: {source_image.name}")
            try:
                source_image.seek(0)
            except Exception:
                pass
    with col2:
        driving_audio = st.file_uploader(
            "2. อัปโหลดไฟล์เสียงพากย์ (.mp3 / .wav)",
            type=["mp3", "wav", "m4a"],
            key="lipsync_audio",
        )
        if driving_audio is not None:
            st.success("อัปโหลดเสียงสำเร็จ")
            try:
                st.audio(driving_audio)
                driving_audio.seek(0)
            except Exception:
                st.caption(f"ไฟล์เสียง: {driving_audio.name}")

    tools = describe_setup()
    models_ready = tools["liveportrait"] and (tools["sadtalker"] or tools["wav2lip"])
    if not models_ready:
        st.info(
            "เครื่องนี้ยังไม่มี SadTalker / LivePortrait กดเรนเดอร์ได้เลย "
            "ระบบจะทำคลิปรูปมาสคอตพร้อมเสียงพากย์ก่อน (ปากยังไม่ขยับจนกว่าจะติดตั้งโมเดล)"
        )
    with st.expander("ตั้งค่าโมเดลหลังบ้าน", expanded=False):
        if not tools["liveportrait"] or (not tools["sadtalker"] and not tools["wav2lip"]):
            st.caption(
                "ตั้ง `LIVEPORTRAIT_HOME` และ `SADTALKER_HOME` หรือ `WAV2LIP_HOME` "
                "ถ้ายังไม่ติดตั้ง ระบบจะแสดงคำสั่งที่จะรัน (dry run)"
            )
        live_home = st.text_input(
            "LIVEPORTRAIT_HOME",
            value=os.environ.get("LIVEPORTRAIT_HOME", ""),
            placeholder="/path/to/LivePortrait",
        )
        talker_home = st.text_input(
            "SADTALKER_HOME",
            value=os.environ.get("SADTALKER_HOME", ""),
            placeholder="/path/to/SadTalker",
        )
        wav_home = st.text_input(
            "WAV2LIP_HOME",
            value=os.environ.get("WAV2LIP_HOME", ""),
            placeholder="/path/to/Wav2Lip",
        )
        if live_home:
            os.environ["LIVEPORTRAIT_HOME"] = live_home.strip()
        if talker_home:
            os.environ["SADTALKER_HOME"] = talker_home.strip()
        if wav_home:
            os.environ["WAV2LIP_HOME"] = wav_home.strip()
        dry_run = st.checkbox(
            "ทดลองดูคำสั่งก่อนรันจริง (dry run)",
            value=False,
        )
        output_dir = st.text_input("โฟลเดอร์ผลลัพธ์", value="output")
        template_face = st.file_uploader(
            "รูปหน้าเทมเพลต SadTalker (ไม่บังคับ — ถ้าไม่ใส่จะใช้รูปมาสคอต)",
            type=["jpg", "jpeg", "png"],
            key="lipsync_template_face",
        )
        driving_video = st.file_uploader(
            "Driving Video พร้อมใช้ (ไม่บังคับ — ข้ามขั้นสร้างปากจากเสียง)",
            type=["mp4", "mov", "webm"],
            key="lipsync_driving_video",
        )

    if st.button("🚀 เริ่มเรนเดอร์มาสคอตขยับปาก", type="primary", use_container_width=True):
        if source_image is None or driving_audio is None:
            st.warning("⚠️ กรุณาอัปโหลดรูปและเสียงให้ครบก่อน")
            return
        st.info("กำลังประมวลผลหลังบ้าน...")
        work = Path(output_dir) / "uploads"
        try:
            source_path = _save_upload(source_image, work, "source")
            audio_path = _save_upload(driving_audio, work, "voice")
            template_path = (
                _save_upload(template_face, work, "template") if template_face else source_path
            )
            driving_path = _save_upload(driving_video, work, "driving") if driving_video else None
            with st.spinner("กำลังถอดเสียงเป็นคลิปปาก แล้วสวมหน้ามาสคอต..."):
                result = generate_lip_sync_pipeline(
                    str(source_path),
                    driving_audio_path=str(audio_path),
                    output_dir=output_dir,
                    template_face_path=str(template_path),
                    driving_video_path=str(driving_path) if driving_path else None,
                    dry_run=dry_run,
                )
        except LipSyncError as err:
            st.error(str(err))
            return
        except Exception as err:
            st.error(f"รันไม่สำเร็จ: {err}")
            return
        if dry_run:
            st.info("โหมดทดลอง — ยังไม่ได้เรียกโมเดลจริง")
            for index, step in enumerate(result.get("steps") or [], start=1):
                if not step:
                    continue
                st.markdown(f"**ขั้นที่ {index}**  cwd: `{step.get('cwd', '')}`")
                st.code(" ".join(str(part) for part in step.get("command") or []), language="bash")
            st.caption(f"ไฟล์ปลายทาง: {result.get('output')}")
            return
        if isinstance(result, str):
            result = {"path": result, "mode": "full"}
        video_path = result.get("path") or result.get("output")
        if result.get("mode") == "fallback":
            st.warning(
                "ยังไม่มีโมเดลขยับปากบนเครื่องนี้ จึงได้คลิปรูปนิ่งพร้อมเสียงพากย์ "
                "ถ้าต้องการปากขยับ ให้ติดตั้ง SadTalker หรือ Wav2Lip และ LivePortrait แล้วใส่ path ในตั้งค่าโมเดลหลังบ้าน"
            )
        else:
            st.success(f"✨ สำเร็จ! เซฟวิดีโอไว้ที่: {video_path}")
        if video_path and Path(video_path).is_file():
            st.video(str(video_path))
            st.download_button(
                "📥 ดาวน์โหลดคลิปสุดท้าย",
                data=Path(video_path).read_bytes(),
                file_name=Path(video_path).name,
                mime="video/mp4",
                use_container_width=True,
            )


