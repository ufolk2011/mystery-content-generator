import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


class LipSyncError(RuntimeError):
    """Raised when the still+audio clip cannot be assembled."""


def _import_moviepy():
    try:
        from moviepy import AudioFileClip, ImageClip

        return ImageClip, AudioFileClip
    except ImportError:
        from moviepy.editor import AudioFileClip, ImageClip

        return ImageClip, AudioFileClip


def _pip_install(packages):
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "install", *packages],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _load_moviepy(install_if_missing=True):
    try:
        return _import_moviepy()
    except ImportError:
        pass
    if install_if_missing and _pip_install(["moviepy>=2.0.0", "imageio-ffmpeg>=0.5.1"]):
        try:
            return _import_moviepy()
        except ImportError:
            pass
    return None


def _with_duration(clip, duration):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _with_audio(clip, audio):
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def _resized(clip, **kwargs):
    if hasattr(clip, "resized"):
        return clip.resized(**kwargs)
    return clip.resize(**kwargs)


def ffmpeg_exe():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        if _pip_install(["imageio-ffmpeg>=0.5.1"]):
            try:
                import imageio_ffmpeg

                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                pass
    raise LipSyncError(
        "ไม่พบเครื่องมือตัดต่อวิดีโอ — ปิดแล้วเปิด run.bat ใหม่ "
        "หรือรัน `.venv\\Scripts\\python.exe -m pip install moviepy imageio-ffmpeg`"
    )


def _mux_with_moviepy(image_path, audio_path, output_path, fps, max_width, ImageClip, AudioFileClip):
    audio = None
    video = None
    try:
        audio = AudioFileClip(str(audio_path))
        duration = float(audio.duration or 0)
        if duration <= 0:
            raise LipSyncError("ไฟล์เสียงว่างเปล่า")
        video = ImageClip(str(image_path))
        width, height = video.size
        if width > max_width:
            video = _resized(video, width=max_width)
            width, height = video.size
        even_w = width - (width % 2)
        even_h = height - (height % 2)
        if even_w < 2 or even_h < 2:
            raise LipSyncError("รูปเล็กเกินไปสำหรับเข้ารหัสวิดีโอ")
        if (even_w, even_h) != (width, height):
            video = _resized(video, new_size=(even_w, even_h))
        video = _with_duration(video, duration)
        video = _with_audio(video, audio)
        video.write_videofile(
            str(output_path),
            fps=int(fps),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
    finally:
        for clip in (video, audio):
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass


def _mux_with_ffmpeg(image_path, audio_path, output_path, fps):
    ffmpeg = ffmpeg_exe()
    completed = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(int(fps)),
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0 or not output_path.is_file():
        detail = (completed.stderr or b"").decode("utf-8", errors="ignore")[-400:]
        raise LipSyncError(f"รวมคลิปไม่สำเร็จ\n{detail}")


def make_lip_sync_clip(
    image_path,
    audio_path,
    output_path="output/lip_sync.mp4",
    fps=24,
    max_width=720,
    install_if_missing=True,
):
    """Mux a mascot still with audio. Uses moviepy when available, otherwise ffmpeg."""
    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    if image_path.suffix.lower() not in IMAGE_SUFFIXES:
        raise LipSyncError("รูปต้องเป็น .jpg / .png")
    if audio_path.suffix.lower() not in AUDIO_SUFFIXES:
        raise LipSyncError("เสียงต้องเป็น .mp3 / .wav / .m4a")
    if not image_path.is_file():
        raise LipSyncError(f"ไม่พบรูป: {image_path}")
    if not audio_path.is_file():
        raise LipSyncError(f"ไม่พบไฟล์เสียง: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    loaded = _load_moviepy(install_if_missing=install_if_missing)
    try:
        if loaded is not None:
            ImageClip, AudioFileClip = loaded
            _mux_with_moviepy(
                image_path,
                audio_path,
                output_path,
                fps,
                max_width,
                ImageClip,
                AudioFileClip,
            )
        else:
            _mux_with_ffmpeg(image_path, audio_path, output_path, fps)
    except LipSyncError:
        raise
    except Exception as err:
        raise LipSyncError(f"รวมคลิปไม่สำเร็จ: {err}") from err

    if not output_path.is_file():
        raise LipSyncError("รวมคลิปไม่สำเร็จ")
    return str(output_path)


def _render_mascot_clip_form():
    import streamlit as st

    st.subheader("ลิปซิงค์มาสคอต")
    st.write(
        "อัปโหลดรูปมาสคอตกับไฟล์เสียง แล้วรวมเป็นวิดีโอทันที "
        "ไม่ต้องโหลดโมเดล AI"
    )

    col1, col2 = st.columns(2)
    with col1:
        image_file = st.file_uploader(
            "1. รูปมาสคอต (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            key="lip_sync_image",
        )
        if image_file is not None:
            try:
                st.image(image_file, caption="รูปมาสคอต", use_container_width=True)
                image_file.seek(0)
            except Exception:
                st.caption(image_file.name)
    with col2:
        audio_file = st.file_uploader(
            "2. ไฟล์เสียงพากย์ (.mp3 / .wav / .m4a)",
            type=["mp3", "wav", "m4a"],
            key="lip_sync_audio",
        )
        if audio_file is not None:
            st.audio(audio_file)
            try:
                audio_file.seek(0)
            except Exception:
                pass

    if st.button("สร้างคลิป", type="primary", use_container_width=True):
        if image_file is None or audio_file is None:
            st.warning("อัปโหลดทั้งรูปและเสียงก่อน")
            return
        work = Path("output") / "uploads"
        work.mkdir(parents=True, exist_ok=True)
        image_path = work / f"mascot{Path(image_file.name).suffix.lower() or '.jpg'}"
        audio_path = work / f"voice{Path(audio_file.name).suffix.lower() or '.mp3'}"
        image_path.write_bytes(image_file.getbuffer())
        audio_path.write_bytes(audio_file.getbuffer())
        dest = Path("output") / "lip_sync.mp4"
        try:
            with st.spinner("กำลังรวมรูปกับเสียงเป็นวิดีโอ..."):
                result = make_lip_sync_clip(image_path, audio_path, dest)
        except LipSyncError as err:
            st.error(str(err))
            return
        except Exception as err:
            st.error(f"สร้างคลิปไม่สำเร็จ: {err}")
            return
        st.success("ได้คลิปแล้ว")
        st.video(result)
        st.download_button(
            "ดาวน์โหลดคลิป",
            data=Path(result).read_bytes(),
            file_name="lip_sync.mp4",
            mime="video/mp4",
            use_container_width=True,
        )


def render_lip_sync_page():
    import streamlit as st

    try:
        from studio_update import apply_update

        apply_update()
    except Exception:
        pass

    tab_voice, tab_clip = st.tabs(["ถอดเสียงหาคลิป", "รวมรูปกับเสียง"])
    with tab_voice:
        try:
            from audio_timeline import render_audio_timeline_page

            render_audio_timeline_page(embed=True)
        except Exception as err:
            st.error(f"โหลดหน้าอัปโหลดเสียงไม่สำเร็จ: {err}")
    with tab_clip:
        _render_mascot_clip_form()


# Older imports keep working. This page never checks talking-head model folders.
render_mascot_clip_page = render_lip_sync_page
make_mascot_clip = make_lip_sync_clip
MascotClipError = LipSyncError
