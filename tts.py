import asyncio
import io
import re
from concurrent.futures import ThreadPoolExecutor

import requests


def spoken_script(script):
    parts = [
        (script or {}).get("hook", ""),
        (script or {}).get("context", ""),
        (script or {}).get("twist", ""),
        (script or {}).get("reveal", ""),
    ]
    spoken = " ... ".join(part.strip() for part in parts if str(part).strip())
    return spoken.strip()


def safe_filename(title):
    slug = re.sub(r"[^\wก-๙\-]+", "_", title or "script", flags=re.UNICODE)
    return (slug.strip("_") or "script")[:60] + ".mp3"


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _edge_mp3(text, voice, rate, pitch):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    if not chunks:
        raise RuntimeError("สร้างเสียง Edge TTS ไม่สำเร็จ")
    return b"".join(chunks)


def synthesize(text, voice_id, eleven_key="", eleven_voice="male"):
    text = (text or "").strip()
    if not text:
        raise ValueError("ไม่มีข้อความสคริปต์ให้สร้างเสียง")

    if voice_id == "male_dark":
        return _run_async(_edge_mp3(text, "th-TH-NiwatNeural", "-12%", "-8Hz"))

    if voice_id == "female":
        return _run_async(_edge_mp3(text, "th-TH-PremwadeeNeural", "-4%", "+0Hz"))

    if voice_id == "gtts":
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=text, lang="th", slow=False).write_to_fp(buf)
        data = buf.getvalue()
        if not data:
            raise RuntimeError("สร้างเสียง gTTS ไม่สำเร็จ")
        return data

    if voice_id == "elevenlabs":
        if not eleven_key:
            raise ValueError("กรุณาใส่ ElevenLabs API Key ที่แถบซ้าย")
        voice_map = {
            "male": "pNInz6obpgDQGcFmaJgB",
            "female": "21m00Tcm4TlvDq8ikWAM",
        }
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_map.get(eleven_voice, voice_map['male'])}",
            headers={
                "xi-api-key": eleven_key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.42,
                    "similarity_boost": 0.75,
                    "style": 0.35,
                    "use_speaker_boost": True,
                },
            },
            timeout=90,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"ElevenLabs: {response.text[:240]}")
        return response.content

    raise ValueError("ไม่รู้จักตัวเลือกเสียงนี้")
