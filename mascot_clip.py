import shutil
import subprocess
from pathlib import Path

import numpy as np

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


class MascotClipError(RuntimeError):
    """Raised when the mascot clip cannot be assembled."""


def ffmpeg_exe():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as err:
        raise MascotClipError(
            "ไม่พบ ffmpeg — รัน `pip install imageio-ffmpeg` ในโฟลเดอร์โปรเจกต์"
        ) from err


def decode_mono_audio(audio_path, sample_rate=22050):
    ffmpeg = ffmpeg_exe()
    completed = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "pipe:1",
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout:
        detail = (completed.stderr or b"").decode("utf-8", errors="ignore")[-400:]
        raise MascotClipError(f"ถอดไฟล์เสียงไม่สำเร็จ\n{detail}")
    samples = np.frombuffer(completed.stdout, dtype=np.float32)
    if samples.size == 0:
        raise MascotClipError("ไฟล์เสียงว่างเปล่า")
    return samples, sample_rate


def rms_envelope(samples, sample_rate, fps):
    hop = max(int(sample_rate / fps), 1)
    n_frames = int(np.ceil(len(samples) / hop))
    env = np.zeros(n_frames, dtype=np.float32)
    for index in range(n_frames):
        chunk = samples[index * hop : (index + 1) * hop]
        if chunk.size:
            env[index] = float(np.sqrt(np.mean(np.square(chunk))))
    if n_frames >= 5:
        kernel = np.ones(5, dtype=np.float32) / 5
        env = np.convolve(env, kernel, mode="same").astype(np.float32)
    peak = float(env.max()) or 1.0
    return env / peak


def load_mascot_bgr(image_path):
    import cv2

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise MascotClipError(f"เปิดรูปไม่สำเร็จ: {image_path}")
    return image


def fit_on_canvas(image, canvas_w, canvas_h, scale=1.0, offset_x=0, offset_y=0):
    import cv2

    canvas = np.full((canvas_h, canvas_w, 3), (201, 248, 255), dtype=np.uint8)
    img_h, img_w = image.shape[:2]
    base = min(canvas_w / img_w, canvas_h / img_h) * 0.88 * float(scale)
    new_w = max(2, int(img_w * base) // 2 * 2)
    new_h = max(2, int(img_h * base) // 2 * 2)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    x = (canvas_w - new_w) // 2 + int(offset_x)
    y = (canvas_h - new_h) // 2 + int(offset_y)
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(canvas_w, x + new_w), min(canvas_h, y + new_h)
    src_x1 = x1 - x
    src_y1 = y1 - y
    src_x2 = src_x1 + (x2 - x1)
    src_y2 = src_y1 + (y2 - y1)
    if x2 > x1 and y2 > y1:
        canvas[y1:y2, x1:x2] = resized[src_y1:src_y2, src_x1:src_x2]
    return canvas


def make_mascot_clip(
    image_path,
    audio_path,
    output_path="output/mascot_clip.mp4",
    fps=25,
    width=720,
    height=1280,
):
    """Compose a talking-style mascot clip from a still and a voiceover.

    Motion follows the audio loudness (bounce + scale). No neural lip-sync models.
    """
    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    if image_path.suffix.lower() not in IMAGE_SUFFIXES:
        raise MascotClipError("รูปต้องเป็น .jpg / .png")
    if audio_path.suffix.lower() not in AUDIO_SUFFIXES:
        raise MascotClipError("เสียงต้องเป็น .mp3 / .wav / .m4a")
    if not image_path.is_file():
        raise MascotClipError(f"ไม่พบรูป: {image_path}")
    if not audio_path.is_file():
        raise MascotClipError(f"ไม่พบไฟล์เสียง: {audio_path}")

    samples, sample_rate = decode_mono_audio(audio_path)
    envelope = rms_envelope(samples, sample_rate, fps)
    mascot = load_mascot_bgr(image_path)
    width = width if width % 2 == 0 else width + 1
    height = height if height % 2 == 0 else height + 1
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = ffmpeg_exe()
    writer = subprocess.Popen(
        [
            ffmpeg,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        for index, level in enumerate(envelope):
            t = index / float(fps)
            scale = 1.0 + 0.07 * float(level)
            offset_y = int(-18 * float(level) + 4 * np.sin(2 * np.pi * t / 4.0))
            offset_x = int(10 * np.sin(2 * np.pi * t / 3.2))
            frame = fit_on_canvas(
                mascot,
                width,
                height,
                scale=scale,
                offset_x=offset_x,
                offset_y=offset_y,
            )
            writer.stdin.write(frame.tobytes())
    except BrokenPipeError as err:
        err_text = (writer.stderr.read() if writer.stderr else b"").decode("utf-8", errors="ignore")
        raise MascotClipError(f"เขียนวิดีโอไม่สำเร็จ\n{err_text[-400:]}") from err
    finally:
        if writer.stdin:
            writer.stdin.close()
        code = writer.wait()
    if code != 0 or not output_path.is_file():
        err_text = (writer.stderr.read() if writer.stderr else b"").decode("utf-8", errors="ignore")
        raise MascotClipError(f"รวมคลิปไม่สำเร็จ\n{err_text[-400:]}")
    return str(output_path)


def render_mascot_clip_page():
    import streamlit as st

    st.subheader("สร้างคลิปมาสคอตจากรูปและเสียง")
    st.write("อัปโหลดรูปกับไฟล์พากย์ ระบบจะตัดต่อเป็นคลิปแนวตั้งที่ขยับตามจังหวะเสียงทันที")

    col1, col2 = st.columns(2)
    with col1:
        image_file = st.file_uploader(
            "1. รูปมาสคอต (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            key="mascot_clip_image",
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
            key="mascot_clip_audio",
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
        dest = Path("output") / "mascot_clip.mp4"
        try:
            with st.spinner("กำลังประกอบคลิปตามจังหวะเสียง..."):
                result = make_mascot_clip(image_path, audio_path, dest)
        except MascotClipError as err:
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
            file_name="mascot_clip.mp4",
            mime="video/mp4",
            use_container_width=True,
        )
