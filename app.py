import html
import json
import os
import re
import uuid
from urllib.parse import quote, quote_plus

from google import genai
from google.genai import types
import streamlit as st
import streamlit.components.v1 as components

from tts import safe_filename, spoken_script, synthesize

st.set_page_config(page_title="Mystery Content Generator", layout="wide")

HISTORY_FILE = "history_topics.json"
SAVED_FILE = "saved_stories.json"

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;500;600;700&display=swap');

    html, body, .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"], [data-testid="stMarkdown"],
    button, input, textarea, label, p, h1, h2, h3, h4, [class*="css"] {
        font-family: "Kanit", sans-serif !important;
    }
    .stApp {
        background: #FFF8C9;
        color: #111111;
    }
    [data-testid="stSidebar"] {
        background: #8EE6FF !important;
        border-right: 3px solid #111111;
    }
    [data-testid="stSidebar"] > div:first-child {
        background: #8EE6FF;
        padding: 1.5rem 1.15rem 2.4rem;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.95rem !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #111111 !important;
        font-family: "Kanit", sans-serif !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: #ffffff !important;
        color: #111111 !important;
        border: 2px solid #111111 !important;
        min-height: 42px;
        border-radius: 14px !important;
        font-family: "Kanit", sans-serif !important;
        font-weight: 600 !important;
    }
    [data-testid="stTextInput"] > div > div {
        background: #ffffff !important;
        border: 2px solid #111111 !important;
        border-radius: 16px !important;
        box-shadow: none !important;
    }
    [data-testid="stTextInput"] input {
        border: 0 !important;
        background: transparent !important;
        color: #111111 !important;
        font-family: "Kanit", sans-serif !important;
        padding: 0.55rem 0.8rem !important;
    }
    [data-testid="stTextInput"] button {
        background: transparent !important;
        color: #111111 !important;
        border: 0 !important;
        min-width: 36px !important;
        min-height: 36px !important;
        width: 36px !important;
        padding: 0 !important;
        box-shadow: none !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"] {
        display: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255,255,255,0.72);
        border: 2px solid #111111;
        border-radius: 16px;
    }
    [data-testid="stSidebar"] footer,
    [data-testid="stSidebar"] [data-testid="stDecoration"] {
        display: none !important;
    }
    .sidebar-note {
        background: rgba(255,255,255,0.55);
        border: 2px solid #111111;
        border-radius: 14px;
        padding: 8px 10px;
        font-size: 0.9rem;
        color: #111111;
        font-family: "Kanit", sans-serif;
    }
    h1, h2, h3 {
        color: #111111 !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }
    .hero-kicker {
        text-align: center;
        color: #111111;
        letter-spacing: 0.12em;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }
    .hero-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        color: #111111;
        line-height: 1.15;
        margin: 0 0 8px;
    }
    .hero-sub {
        text-align: center;
        color: #111111;
        opacity: 0.72;
        margin-bottom: 18px;
    }
    [data-testid="stVerticalBlock"]:has(> div .mood-yellow) {
        background: #FFF18F;
        border: 3px solid #111111;
        border-radius: 32px;
        padding: 18px 16px 10px;
    }
    [data-testid="stVerticalBlock"]:has(> div .mood-pink) {
        background: #FF808C;
        border: 3px solid #111111;
        border-radius: 32px;
        padding: 18px 16px 10px;
    }
    [data-testid="stVerticalBlock"]:has(> div .mood-blue) {
        background: #8EE6FF;
        border: 3px solid #111111;
        border-radius: 32px;
        padding: 18px 16px 10px;
    }
    .card-title {
        font-size: 1.55rem;
        font-weight: 800;
        color: #111111;
        line-height: 1.25;
        margin: 0 0 8px;
        text-align: center;
    }
    .card-summary {
        color: #111111;
        font-size: 0.98rem;
        line-height: 1.5;
        margin-bottom: 12px;
        text-align: center;
    }
    .script-block {
        background: rgba(255, 255, 255, 0.55);
        border: 2px solid #111111;
        border-radius: 18px;
        padding: 10px 12px;
        margin: 0 0 10px;
    }
    .script-label {
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #111111;
        margin-bottom: 4px;
    }
    .script-text {
        color: #111111;
        font-size: 0.96rem;
        line-height: 1.55;
        white-space: pre-wrap;
    }
    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {
        background: #111111 !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        box-shadow: none !important;
        font-family: "Kanit", sans-serif !important;
    }
    .stTextInput input, .stSelectbox [data-baseweb="select"] > div {
        border-radius: 16px !important;
        background: #ffffff !important;
        color: #111111 !important;
        font-family: "Kanit", sans-serif !important;
    }
    .stSelectbox [data-baseweb="select"] > div {
        border: 2px solid #111111 !important;
    }
    [data-testid="stAlert"] {
        border-radius: 20px;
        border: 2px solid #111111;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("### ตั้งค่าระบบ")
st.sidebar.caption("ใส่คีย์แล้วเลือกเสียงก่อนเริ่มค้นหาเรื่อง")
default_key = os.environ.get("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "Gemini API Key",
    value=st.session_state.get("api_key", default_key),
    placeholder="วางคีย์ที่นี่",
    autocomplete="off",
)
if api_key:
    st.session_state.api_key = api_key

model_name = st.sidebar.selectbox(
    "โมเดล",
    ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
    index=0,
    key="model_name_v2",
)

st.sidebar.subheader("เลือกเสียงพากย์")
voice_labels = {
    "male_dark": "ผู้ชายโทนดาร์ก / ลึกลับ",
    "female": "ผู้หญิง",
    "gtts": "Google gTTS (ไทย)",
    "elevenlabs": "ElevenLabs API",
}
voice_id = st.sidebar.selectbox(
    "เสียง",
    list(voice_labels.keys()),
    format_func=lambda key: voice_labels[key],
    key="voice_id",
)
eleven_key = ""
eleven_voice = "male"
if voice_id == "elevenlabs":
    eleven_key = st.sidebar.text_input(
        "ElevenLabs API Key",
        type="password",
        value=st.session_state.get("eleven_key", os.environ.get("ELEVENLABS_API_KEY", "")),
    )
    if eleven_key:
        st.session_state.eleven_key = eleven_key
    eleven_voice = st.sidebar.selectbox(
        "เสียง ElevenLabs",
        ["male", "female"],
        format_func=lambda key: "ผู้ชายลึกลับ" if key == "male" else "ผู้หญิง",
        key="eleven_voice",
    )
else:
    st.sidebar.markdown('<div class="sidebar-note">เสียงดาร์กและเสียงผู้หญิงใช้ได้ทันที ไม่ต้องใส่คีย์เพิ่ม</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")


def load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_json_list(path, items):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)


def load_history():
    return [str(item) for item in load_json_list(HISTORY_FILE)]


def save_history(topics):
    save_json_list(HISTORY_FILE, topics)


def load_saved():
    return load_json_list(SAVED_FILE)


def save_saved(stories):
    save_json_list(SAVED_FILE, stories)


def extract_json(text):
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\[\s*\{.*\}\s*\])", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


SCRIPT_SECTIONS = (
    ("hook", "ฮุค", "#a78bfa"),
    ("context", "บริบท", "#38bdf8"),
    ("twist", "แต่", "#f59e0b"),
    ("reveal", "เฉลย", "#34d399"),
)


def normalize_keywords(raw):
    empty = {key: [] for key, _, _ in SCRIPT_SECTIONS}
    if isinstance(raw, str):
        bits = [part.strip() for part in re.split(r"[,;\n|/]", raw) if part.strip()]
        if bits:
            empty["hook"] = bits[:3]
        return empty
    if not isinstance(raw, dict):
        return empty
    aliases = {
        "hook": ("hook", "ฮุค", "1"),
        "context": ("context", "บริบท", "2"),
        "twist": ("twist", "แต่", "3"),
        "reveal": ("reveal", "เฉลย", "4"),
    }
    out = dict(empty)
    for key, names in aliases.items():
        value = None
        for name in names:
            if name in raw:
                value = raw[name]
                break
        items = []
        if isinstance(value, str):
            items = [part.strip() for part in re.split(r"[,;\n|/]", value) if part.strip()]
        elif isinstance(value, list):
            items = [str(part).strip() for part in value if str(part).strip()]
        out[key] = items[:4]
    return out


def clip_search_links(keyword):
    visual = f"{keyword} cinematic b-roll stock footage"
    return [
        ("YouTube", f"https://www.youtube.com/results?search_query={quote_plus(visual)}"),
        ("Pexels", f"https://www.pexels.com/search/videos/{quote(keyword)}/"),
        ("Pixabay", f"https://pixabay.com/videos/search/{quote(keyword)}/"),
        ("Coverr", f"https://coverr.co/search?q={quote_plus(keyword)}"),
    ]


def broll_prompt(title, script):
    return f"""
คุณเป็นผู้ช่วยหา B-roll สำหรับตัดคลิปสั้นแนวลึกลับ
เรื่อง: {title}
สคริปต์:
- ฮุค: {script.get('hook', '')}
- บริบท: {script.get('context', '')}
- แต่: {script.get('twist', '')}
- เฉลย: {script.get('reveal', '')}

ตอบเป็น JSON object เท่านั้น มี 4 คีย์: hook, context, twist, reveal
แต่ละคีย์เป็น array ของคีย์เวิร์ดภาษาอังกฤษ 2-3 ชุด
แต่ละชุดเป็นวลีสั้นๆ สำหรับค้นหาคลิปวิดีโอใน YouTube / Pexels / Pixabay
เน้นภาพที่หาเจอง่าย เช่น dark hallway, candle in darkness, old photograph, city night traffic
ห้ามใส่คำอธิบายอื่น
"""


def generate_broll_keywords(client, title, script):
    response = client.models.generate_content(
        model=model_name,
        contents=broll_prompt(title, script),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return normalize_keywords(extract_json(response.text))


def has_broll(broll):
    return any((broll or {}).get(key) for key, _, _ in SCRIPT_SECTIONS)


def normalize_script(raw):
    labels = {
        "hook": ("ฮุค", "hook", "1"),
        "context": ("บริบท", "context", "2"),
        "twist": ("แต่", "twist", "3"),
        "reveal": ("เฉลย", "reveal", "4"),
    }
    empty = {key: "" for key in labels}
    if isinstance(raw, dict):
        out = dict(empty)
        for key, aliases in labels.items():
            for alias in (key, *aliases):
                if alias in raw and str(raw[alias]).strip():
                    out[key] = str(raw[alias]).strip()
                    break
        return out
    text = str(raw or "").strip()
    named = re.findall(
        r"(ฮุค|บริบท|แต่|เฉลย)\s*[:：\-)]\s*(.*?)(?=(?:\n\s*(?:ฮุค|บริบท|แต่|เฉลย)\s*[:：\-)]|\Z))",
        text,
        flags=re.DOTALL,
    )
    if named:
        mapping = {"ฮุค": "hook", "บริบท": "context", "แต่": "twist", "เฉลย": "reveal"}
        out = dict(empty)
        for label, body in named:
            out[mapping[label]] = body.strip()
        return out
    parts = re.split(r"(?:^|\n)\s*(?:ฮุค|บริบท|แต่|เฉลย)\s*[:：\-)]\s*", text)
    if len(parts) >= 5:
        return {
            "hook": parts[1].strip(),
            "context": parts[2].strip(),
            "twist": parts[3].strip(),
            "reveal": parts[4].strip(),
        }
    return {**empty, "hook": text}


def normalize_topics(payload):
    if isinstance(payload, dict):
        for key in ("topics", "items", "stories", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("ผลลัพธ์ไม่ใช่รายการเรื่อง")

    topics = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        topics.append(
            {
                "id": str(uuid.uuid4()),
                "title": title,
                "summary": str(item.get("summary") or "").strip(),
                "script": normalize_script(item.get("script")),
                "broll": normalize_keywords(
                    item.get("video_keywords")
                    or item.get("broll")
                    or item.get("clip_keywords")
                ),
            }
        )
    return topics[:5]


def add_history_title(title):
    history = load_history()
    if title not in history:
        history.append(title)
        save_history(history)
    st.session_state.history = history


def script_copy_text(title, script):
    return (
        f"{title}\n\n"
        f"ฮุค: {script.get('hook', '')}\n\n"
        f"บริบท: {script.get('context', '')}\n\n"
        f"แต่: {script.get('twist', '')}\n\n"
        f"เฉลย: {script.get('reveal', '')}"
    ).strip()


def copy_script_button(text, key):
    payload = json.dumps(text, ensure_ascii=False)
    safe_key = html.escape(key)
    components.html(
        f"""
        <div style="font-family:sans-serif">
          <button id="{safe_key}" type="button" style="width:100%;border:0;border-radius:16px;padding:10px 14px;background:#111111;color:#ffffff;font-size:14px;font-weight:700;cursor:pointer">📋 Copy สคริปต์</button>
        </div>
        <script>
          const btn = document.getElementById("{safe_key}");
          const text = {payload};
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText(text);
              btn.textContent = "✅ คัดลอกแล้ว";
              setTimeout(() => btn.textContent = "📋 Copy สคริปต์", 1600);
            }} catch (err) {{
              btn.textContent = "คัดลอกไม่สำเร็จ";
            }}
          }});
        </script>
        """,
        height=52,
    )


def render_script_sections(script):
    for key, label, color in SCRIPT_SECTIONS:
        st.markdown(
            f"""
            <div class="script-block" style="--accent:{color}">
              <div class="script-label">{label}</div>
              <div class="script-text">{html.escape(script.get(key, ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def store_broll(audio_key, broll, topic=None):
    st.session_state.broll[audio_key] = broll
    st.session_state.show_broll[audio_key] = True
    if topic is not None:
        topic["broll"] = broll
    if str(audio_key).startswith("saved-"):
        try:
            idx = int(str(audio_key).split("-", 1)[1])
            saved = list(st.session_state.saved)
            if 0 <= idx < len(saved):
                saved[idx]["broll"] = broll
                save_saved(saved)
                st.session_state.saved = saved
        except ValueError:
            pass
    st.session_state.results = [
        {**item, "broll": broll} if item.get("id") == audio_key else item
        for item in st.session_state.results
    ]


def render_broll_finder(audio_key, title, script, existing=None, topic=None):
    broll = st.session_state.broll.get(audio_key) or normalize_keywords(existing)
    if st.button("🎬 ค้นหาคลิปประกอบ", key=f"broll-{audio_key}", use_container_width=True):
        if not has_broll(broll):
            if not api_key:
                st.error("ใส่ Gemini API Key ก่อนเพื่อให้ AI หาคีย์เวิร์ดคลิป")
                return
            try:
                with st.spinner("กำลังหาคีย์เวิร์ดคลิปประกอบแต่ละท่อน..."):
                    client = genai.Client(api_key=api_key)
                    broll = generate_broll_keywords(client, title, script)
            except Exception as err:
                st.error(f"หาคลิปไม่สำเร็จ: {err}")
                return
        store_broll(audio_key, broll, topic)
        st.rerun()

    if not st.session_state.show_broll.get(audio_key) and not has_broll(broll):
        return
    if not has_broll(broll):
        return

    st.markdown("**Video B-roll Finder** — กดลิงก์ไปเซฟคลิปสั้นมาตัดต่อได้เลย")
    for key, label, color in SCRIPT_SECTIONS:
        keywords = broll.get(key) or []
        if not keywords:
            continue
        st.markdown(f"<div class='script-label' style='color:#111111;margin:8px 0 4px'>{label}</div>", unsafe_allow_html=True)
        for idx, keyword in enumerate(keywords[:2]):
            st.caption(f"คีย์เวิร์ด: `{keyword}`")
            cols = st.columns(4)
            for col, (name, url) in zip(cols, clip_search_links(keyword)):
                col.link_button(name, url, use_container_width=True)


def render_tts_controls(audio_key, title, script):
    if st.button("▶️ ลองฟังเสียงพากย์", key=f"tts-{audio_key}", use_container_width=True):
        try:
            with st.spinner("กำลังสร้างเสียงให้ลองฟังในหน้าเว็บ..."):
                audio_bytes = synthesize(
                    spoken_script(script),
                    voice_id,
                    eleven_key=eleven_key,
                    eleven_voice=eleven_voice,
                )
            st.session_state.audio[audio_key] = audio_bytes
            st.rerun()
        except Exception as err:
            st.error(f"สร้างเสียงไม่สำเร็จ: {err}")

    audio_bytes = st.session_state.audio.get(audio_key)
    if not audio_bytes:
        return

    st.caption("ลองฟังเสียง (Audio Preview) — กด Play ได้เลย ไม่ต้องโหลดไฟล์ลงเครื่อง")
    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    st.download_button(
        "📥 ดาวน์โหลดไฟล์เสียง (.mp3)",
        data=audio_bytes,
        file_name=safe_filename(title),
        mime="audio/mpeg",
        key=f"dl-{audio_key}",
        use_container_width=True,
        help="เซฟไฟล์เก็บไว้ตัดต่อ แยกจากการลองฟังในหน้าเว็บ",
    )


def render_card(topic, tone="yellow"):
    st.markdown(f'<div class="mood-{tone}"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card-title">{html.escape(topic["title"])}</div>
        <div class="card-summary">{html.escape(topic["summary"])}</div>
        """,
        unsafe_allow_html=True,
    )
    render_script_sections(topic["script"])
    copy_script_button(script_copy_text(topic["title"], topic["script"]), f"copy-{topic['id']}")
    render_tts_controls(topic["id"], topic["title"], topic["script"])
    render_broll_finder(topic["id"], topic["title"], topic["script"], topic.get("broll"), topic)
    keep_col, drop_col = st.columns(2)
    if keep_col.button("💾 เก็บไว้", key=f"keep-{topic['id']}", type="primary", use_container_width=True):
        add_history_title(topic["title"])
        saved = load_saved()
        saved.append({k: v for k, v in topic.items() if k != "id"})
        save_saved(saved)
        st.session_state.saved = saved
        st.session_state.results = [item for item in st.session_state.results if item["id"] != topic["id"]]
        st.toast(f"บันทึก «{topic['title']}» ลง history แล้ว รอบหน้าจะไม่สุ่มซ้ำ")
        st.rerun()
    if drop_col.button("🗑️ ลบทิ้ง", key=f"discard-{topic['id']}", use_container_width=True):
        st.session_state.results = [item for item in st.session_state.results if item["id"] != topic["id"]]
        st.rerun()


if "results" not in st.session_state:
    st.session_state.results = []
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "saved" not in st.session_state:
    st.session_state.saved = load_saved()
if "audio" not in st.session_state:
    st.session_state.audio = {}
if "broll" not in st.session_state:
    st.session_state.broll = {}
if "show_broll" not in st.session_state:
    st.session_state.show_broll = {}

st.sidebar.markdown(f"**เรื่องที่เคยเก็บไว้**  {len(st.session_state.history)} เรื่อง")
if st.session_state.history:
    with st.sidebar.expander("ประวัติชื่อเรื่อง (ห้ามซ้ำ)"):
        for title in reversed(st.session_state.history[-40:]):
            st.caption(title)
    if st.sidebar.button("ล้างประวัติชื่อเรื่อง", use_container_width=True):
        save_history([])
        st.session_state.history = []
        st.rerun()

st.markdown('<div class="hero-kicker">Mystery Content Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">AI ค้นหาเรื่องลึกลับ</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">เขียนสคริปต์ 30-60 วินาที พากย์เสียง และหาคลิปประกอบได้ในที่เดียว</div>', unsafe_allow_html=True)

if not api_key:
    st.warning("กรุณาใส่ Gemini API Key ที่ Sidebar ด้านซ้ายก่อนเริ่มใช้งาน")
else:
    client = genai.Client(api_key=api_key)

    if st.button("🚀 ค้นหาเรื่องใหม่ (5 เรื่อง)", type="primary"):
        with st.spinner("AI กำลังค้นหาข้อมูลและเขียนสคริปต์..."):
            excluded_text = ", ".join(st.session_state.history) if st.session_state.history else "ไม่มี"
            prompt = f"""
คุณเป็นนักสร้างคอนเทนต์แนวเรื่องลึกลับ จิตวิทยา และเรื่องแปลกทั่วโลก
จงหาข้อมูลมาให้ 5 เรื่องใหม่
ห้ามซ้ำกับรายการชื่อเรื่องเหล่านี้เด็ดขาด: [{excluded_text}]

ตอบกลับเป็น JSON Array เท่านั้น ห้ามมี markdown หรือคำอธิบายอื่น
แต่ละเรื่องเป็น object ตามนี้:
- title: ชื่อเรื่องภาษาไทยที่ดึงดูด
- summary: สรุปสั้นๆ ว่าเรื่องเกี่ยวกับอะไร และทำไมถึงน่าสนใจ
- script: object มี 4 คีย์
  - hook: ฮุค (ประโยคทำให้สงสัย)
  - context: บริบท (3-4 ประโยคปูเรื่อง/ความเชื่อเดิม)
  - twist: แต่ (ประโยคพลิกสถานการณ์)
  - reveal: เฉลย (ประโยคอธิบายความจริงที่ต่างออกไป)
- video_keywords: object มี 4 คีย์ hook, context, twist, reveal
  แต่ละคีย์เป็น array ของคีย์เวิร์ดภาษาอังกฤษ 2-3 ชุด สำหรับค้นหาคลิป B-roll ใน YouTube / Pexels / Pixabay
  ใช้วลีสั้นที่หาภาพเจอง่าย เช่น dark hallway night, candle flickering, old photograph close up

สคริปต์รวมทุกส่วนแล้วพูดจบใน 30-60 วินาที ใช้ภาษาไทยที่เป็นธรรมชาติ
"""
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                    ),
                )
                topics = normalize_topics(extract_json(response.text))
                if len(topics) < 5:
                    raise ValueError(f"ได้มา {len(topics)} เรื่อง ต้องการ 5 เรื่อง")
                st.session_state.results = topics
                st.success("ค้นหาข้อมูลสำเร็จ!")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.session_state.results:
        st.subheader("เรื่องที่ค้นเจอ")
        results = list(st.session_state.results)
        for row_start in range(0, len(results), 2):
            cols = st.columns(2, gap="large")
            for offset, col in enumerate(cols):
                index = row_start + offset
                if index >= len(results):
                    continue
                with col:
                    render_card(results[index], ["yellow", "pink", "blue"][index % 3])

    saved_stories = st.session_state.saved
    if saved_stories:
        st.subheader("เรื่องที่เก็บไว้")
        for index, topic in enumerate(reversed(saved_stories)):
            real_index = len(saved_stories) - 1 - index
            script = normalize_script(topic.get("script"))
            with st.expander(topic.get("title", "ไม่มีชื่อ")):
                st.write(topic.get("summary", ""))
                render_script_sections(script)
                copy_script_button(
                    script_copy_text(topic.get("title", ""), script),
                    f"copy-saved-{real_index}",
                )
                render_tts_controls(f"saved-{real_index}", topic.get("title", "script"), script)
                render_broll_finder(
                    f"saved-{real_index}",
                    topic.get("title", "script"),
                    script,
                    topic.get("broll") or topic.get("video_keywords"),
                )
                if st.button("ลบออกจากคลัง", key=f"unsave-{real_index}"):
                    saved_stories.pop(real_index)
                    save_saved(saved_stories)
                    st.session_state.saved = saved_stories
                    st.rerun()
