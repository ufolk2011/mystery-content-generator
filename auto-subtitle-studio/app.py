import os
import shutil
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from srt_utils import cues_to_srt, group_words, parse_srt_time
from transcribe import ALLOWED_EXTENSIONS, transcribe_audio_file

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = FastAPI(title="Auto Subtitle Studio")
STATIC = ROOT / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": "Auto Subtitle Studio",
        "model": "gemini-3.5-transcribe",
        "key_configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
    }


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    words_per_line: int = Form(2),
):
    filename = audio.filename or "audio.mp3"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะ MP3 WAV M4A AAC OGG FLAC และ WebM")
    if words_per_line not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="เลือกจำนวนคำต่อบรรทัดได้แค่ 1 ถึง 4")

    tmp_dir = Path(tempfile.mkdtemp(prefix="subtitle-studio-"))
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
    try:
        with tmp_path.open("wb") as handle:
            shutil.copyfileobj(audio.file, handle)
        if tmp_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="ไฟล์เสียงว่างเปล่า")
        result = transcribe_audio_file(str(tmp_path), filename, words_per_line)
        return {
            "filename": filename,
            "words_per_line": words_per_line,
            "words": result["words"],
            "cues": result["cues"],
            "srt": cues_to_srt(result["cues"]),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/srt")
def build_srt(payload: dict):
    cues = []
    for item in payload.get("cues") or []:
        start = str(item.get("start") or "")
        end = str(item.get("end") or "")
        cues.append(
            {
                "start": start,
                "end": end,
                "start_ms": parse_srt_time(start),
                "end_ms": parse_srt_time(end),
                "text": item.get("text") or "",
            }
        )
    words_per_line = payload.get("words_per_line")
    words = payload.get("words")
    if words and words_per_line in (1, 2, 3, 4) and not payload.get("cues"):
        cues = group_words(words, words_per_line)
    return {"srt": cues_to_srt(cues), "cues": cues}
