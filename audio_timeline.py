import json
import os
import re
from urllib.parse import quote, quote_plus

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


def clip_search_links(keyword):
    visual = f"{keyword} cinematic b-roll stock footage"
    return [
        ("YouTube", f"https://www.youtube.com/results?search_query={quote_plus(visual)}"),
        ("Pexels", f"https://www.pexels.com/search/videos/{quote(keyword)}/"),
        ("Pixabay", f"https://pixabay.com/videos/search/{quote(keyword)}/"),
        ("Coverr", f"https://coverr.co/search?q={quote_plus(keyword)}"),
    ]


def render_audio_timeline_page(embed=False):
    """Standalone page: upload voiceover → timestamped TH/EN → stock clips."""
    import streamlit as st
    from google import genai

    if "voice_timeline" not in st.session_state:
        st.session_state.voice_timeline = []

    key_prefix = "embed" if embed else "standalone"
    if embed:
        st.subheader("🎵 อัปโหลดไฟล์เสียงพากย์เพื่อดูว่าวินาทีนี้พูดอะไร")
        st.write("แปลไทย/อังกฤษ แล้วหาคลิปประกอบให้แต่ละช่วงเวลา")
    else:
        st.markdown('<div class="hero-kicker">Mystery Content Studio</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title">ไทม์ไลน์เสียงพากย์</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-sub">อัปโหลดไฟล์เสียง ดูว่าวินาทีนี้พูดอะไร แปลไทย/อังกฤษ แล้วหาคลิปประกอบ</div>',
            unsafe_allow_html=True,
        )

    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.get("api_key") or os.environ.get("GEMINI_API_KEY", ""),
        placeholder="วางคีย์ที่นี่",
        autocomplete="off",
        key=f"{key_prefix}_timeline_gemini_key",
    )
    if api_key:
        st.session_state.api_key = api_key
    model_name = st.selectbox(
        "โมเดล",
        ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
        key=f"{key_prefix}_timeline_model",
    )

    st.subheader("1. อัปโหลดไฟล์เสียงพากย์")
    uploaded_voice = st.file_uploader(
        "เลือกไฟล์เสียง (.mp3 / .wav / .m4a)",
        type=["mp3", "wav", "m4a", "aac", "ogg"],
        key=f"{key_prefix}_voice_upload",
    )
    if uploaded_voice is None:
        st.info("ลากไฟล์เสียงมาวางที่นี่ หรือกด Browse files")
        return

    if st.session_state.get("voice_tl_source") != uploaded_voice.name:
        st.session_state.voice_timeline = []
        st.session_state.voice_tl_source = uploaded_voice.name

    st.audio(uploaded_voice)
    st.caption(f"ไฟล์ที่เลือก: {uploaded_voice.name}")

    if not api_key:
        st.warning("ใส่ Gemini API Key ด้านบนก่อน")
        return

    if st.button(
        "ถอดเสียงตามวินาที แปลไทย/อังกฤษ และหาคลิปประกอบ",
        type="primary",
        use_container_width=True,
        key=f"{key_prefix}_transcribe_voice",
    ):
        try:
            with st.spinner("กำลังฟังเสียง แยกช่วงเวลา และหาคลิปประกอบ..."):
                audio_bytes = bytes(uploaded_voice.getbuffer())
                client = genai.Client(api_key=api_key)
                st.session_state.voice_timeline = transcribe_voice_timeline(
                    client,
                    model_name,
                    audio_bytes,
                    uploaded_voice.name,
                )
            try:
                uploaded_voice.seek(0)
            except Exception:
                pass
            st.success(f"ได้ {len(st.session_state.voice_timeline)} ช่วงจากไฟล์เสียง")
        except Exception as err:
            st.error(f"ถอดเสียงไม่สำเร็จ: {err}")
            return

    segments = st.session_state.voice_timeline
    if not segments:
        return

    st.markdown("---")
    st.subheader("2. วินาทีนี้พูดอะไร")
    for index, seg in enumerate(segments):
        st.markdown(f"**{format_clock(seg['start'])} – {format_clock(seg['end'])}**")
        thai_col, eng_col = st.columns(2)
        thai_col.markdown(f"**ไทย**  \n{seg.get('th') or '—'}")
        eng_col.markdown(f"**English**  \n{seg.get('en') or '—'}")
        for k_idx, keyword in enumerate((seg.get("keywords") or [])[:3]):
            st.caption(f"คลิปประกอบ: `{keyword}`")
            cols = st.columns(4)
            for col, (name, url) in zip(cols, clip_search_links(keyword)):
                col.link_button(
                    name,
                    url,
                    use_container_width=True,
                    key=f"{key_prefix}-tl-{index}-{k_idx}-{name}",
                )
