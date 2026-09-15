import json
import re

from google.genai import types

AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def audio_mime_type(filename):
    suffix = ("." + str(filename).rsplit(".", 1)[-1].lower()) if "." in str(filename) else ""
    return AUDIO_MIME.get(suffix, "audio/mpeg")


def parse_seconds(value):
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return 0.0
    if ":" in text:
        parts = text.split(":")
        try:
            numbers = [float(part) for part in parts]
        except ValueError:
            return 0.0
        if len(numbers) == 3:
            return max(0.0, numbers[0] * 3600 + numbers[1] * 60 + numbers[2])
        if len(numbers) == 2:
            return max(0.0, numbers[0] * 60 + numbers[1])
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def format_clock(seconds):
    total = max(0, int(round(float(seconds))))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _extract_json(text):
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[\s*\{.*\}\s*\])", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


def normalize_segments(payload):
    if isinstance(payload, dict):
        for key in ("segments", "scenes", "timeline", "beats", "items"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        return []

    segments = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        start = parse_seconds(item.get("start") or item.get("start_sec") or item.get("from"))
        end = parse_seconds(item.get("end") or item.get("end_sec") or item.get("to") or start)
        if end < start:
            end = start
        thai = str(item.get("th") or item.get("thai") or item.get("text_th") or item.get("text") or "").strip()
        english = str(item.get("en") or item.get("english") or item.get("text_en") or "").strip()
        raw_keywords = item.get("keywords") or item.get("broll") or item.get("clips") or []
        if isinstance(raw_keywords, str):
            keywords = [part.strip() for part in re.split(r"[,;\n|/]", raw_keywords) if part.strip()]
        elif isinstance(raw_keywords, list):
            keywords = [str(part).strip() for part in raw_keywords if str(part).strip()]
        else:
            keywords = []
        if not thai and not english:
            continue
        segments.append(
            {
                "start": start,
                "end": end,
                "th": thai,
                "en": english or thai,
                "keywords": keywords[:3],
            }
        )
    segments.sort(key=lambda item: item["start"])
    return segments


def timeline_prompt():
    return """
ฟังไฟล์เสียงพากย์นี้ แล้วแตกเป็นไทม์ไลน์ตามช่วงเวลาที่พูดจริง

ตอบเป็น JSON object เท่านั้น มีคีย์ segments เป็น array
แต่ละช่วงเป็น object ตามนี้:
- start: วินาทีเริ่มต้น (ตัวเลข)
- end: วินาทีสิ้นสุด (ตัวเลข)
- th: สิ่งที่พูดช่วงนี้ ภาษาไทย
- en: คำแปลภาษาอังกฤษ
- keywords: array วลีอังกฤษ 2-3 ชุด สำหรับค้นหาคลิป B-roll / ภาพประกอบ เช่น candle in darkness, foggy forest aerial

กฎ:
- แบ่งตามจังหวะเรื่องหรือประโยค ไม่รวมทั้งคลิปเป็นก้อนเดียว
- ถ้าเสียงเป็นภาษาไทย ให้ถอดไทยตามที่พูด แล้วแปลอังกฤษ
- ถ้าเสียงเป็นภาษาอังกฤษ ให้ถอดอังกฤษตามที่พูด แล้วแปลไทย
- keywords ต้องเป็นภาพที่หาเจอง่ายใน YouTube / Pexels / Pixabay
- ห้ามมี markdown หรือคำอธิบายนอก JSON
"""


def transcribe_voice_timeline(client, model_name, audio_bytes, filename):
    mime_type = audio_mime_type(filename)
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=bytes(audio_bytes), mime_type=mime_type),
            timeline_prompt(),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    segments = normalize_segments(_extract_json(response.text))
    if not segments:
        raise ValueError("ถอดเสียงแล้วแต่ยังไม่ได้ช่วงเวลา")
    return segments
