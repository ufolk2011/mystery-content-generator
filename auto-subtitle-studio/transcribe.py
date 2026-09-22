import os
import time

from google import genai
from google.genai import types

from srt_utils import group_words, offset_to_ms

MODEL_ID = "gemini-3.5-transcribe"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"}
MIME_BY_EXT = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}


def mime_for_filename(filename):
    ext = os.path.splitext(filename or "")[1].lower()
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def _word_text(item):
    return str(getattr(item, "word", None) or getattr(item, "text", "") or "").strip()


def extract_words(response):
    words = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            transcription = getattr(part, "audio_transcription", None)
            if not transcription:
                continue
            for item in getattr(transcription, "words", []) or []:
                text = _word_text(item)
                if not text:
                    continue
                start_ms = offset_to_ms(getattr(item, "start_offset", 0))
                end_ms = max(offset_to_ms(getattr(item, "end_offset", 0)), start_ms + 40)
                words.append({"text": text, "start_ms": start_ms, "end_ms": end_ms})
    return words


def wait_until_active(client, uploaded, timeout_sec=120):
    deadline = time.time() + timeout_sec
    current = uploaded
    while time.time() < deadline:
        state = getattr(getattr(current, "state", None), "name", None) or str(
            getattr(current, "state", "")
        )
        if not state or state in {"ACTIVE", "FileState.ACTIVE"}:
            return current
        if "FAILED" in str(state).upper():
            raise RuntimeError("อัปโหลดไฟล์ไป Gemini ไม่สำเร็จ")
        time.sleep(1)
        current = client.files.get(name=current.name)
    return current


def transcribe_audio_file(path, original_name, words_per_line):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ยังไม่มี GEMINI_API_KEY ในไฟล์ .env")

    client = genai.Client(api_key=api_key)
    uploaded = None
    try:
        uploaded = client.files.upload(
            file=path,
            config=types.UploadFileConfig(
                mime_type=mime_for_filename(original_name),
            ),
        )
        uploaded = wait_until_active(client, uploaded)
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[uploaded],
            config=types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    word_timestamp=True,
                    mode="VERBATIM",
                )
            ),
        )
        words = extract_words(response)
        if not words:
            raise RuntimeError("ถอดเสียงได้แต่ไม่ได้รับเวลาต่อคำ กรุณาลองไฟล์อื่น")
        cues = group_words(words, words_per_line)
        return {"words": words, "cues": cues}
    finally:
        if uploaded is not None and getattr(uploaded, "name", None):
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass
