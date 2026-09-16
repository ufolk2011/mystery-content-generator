import re
import uuid

SCRIPT_SECTIONS = (
    ("hook", "ฮุค", "#a78bfa"),
    ("context", "บริบท", "#38bdf8"),
    ("twist", "แต่", "#f59e0b"),
    ("reveal", "เฉลย", "#34d399"),
)

EN_SCRIPT_LABELS = {
    "hook": "Hook",
    "context": "Context",
    "twist": "Twist",
    "reveal": "Reveal",
}


def has_script(script):
    return any(str((script or {}).get(key, "")).strip() for key, _, _ in SCRIPT_SECTIONS)


def looks_english(text):
    letters = len(re.findall(r"[A-Za-z]", text or ""))
    thai = len(re.findall(r"[ก-๙]", text or ""))
    return letters >= 8 and thai < 4


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


def normalize_script(raw):
    labels = {
        "hook": ("ฮุค", "hook", "Hook", "1"),
        "context": ("บริบท", "context", "Context", "2"),
        "twist": ("แต่", "twist", "Twist", "3"),
        "reveal": ("เฉลย", "reveal", "Reveal", "4"),
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
        r"(ฮุค|บริบท|แต่|เฉลย|Hook|Context|Twist|Reveal)\s*[:：\-)]\s*(.*?)(?=(?:\n\s*(?:ฮุค|บริบท|แต่|เฉลย|Hook|Context|Twist|Reveal)\s*[:：\-)]|\Z))",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if named:
        mapping = {
            "ฮุค": "hook",
            "บริบท": "context",
            "แต่": "twist",
            "เฉลย": "reveal",
            "hook": "hook",
            "context": "context",
            "twist": "twist",
            "reveal": "reveal",
        }
        out = dict(empty)
        for label, body in named:
            out[mapping[label.lower()]] = body.strip()
        return out
    parts = re.split(
        r"(?:^|\n)\s*(?:ฮุค|บริบท|แต่|เฉลย|Hook|Context|Twist|Reveal)\s*[:：\-)]\s*",
        text,
        flags=re.IGNORECASE,
    )
    if len(parts) >= 5:
        return {
            "hook": parts[1].strip(),
            "context": parts[2].strip(),
            "twist": parts[3].strip(),
            "reveal": parts[4].strip(),
        }
    return {**empty, "hook": text}


def bilingual_fields(item):
    item = item or {}
    script_th = normalize_script(item.get("script") or item.get("script_th"))
    script_en = normalize_script(
        item.get("script_en") or item.get("script_english") or item.get("english_script")
    )
    th_blob = " ".join(script_th.values())
    en_blob = " ".join(script_en.values())
    if looks_english(th_blob) and has_script(script_en) and not looks_english(en_blob):
        script_th, script_en = script_en, script_th
    elif looks_english(th_blob) and not has_script(script_en):
        script_en = dict(script_th)
    return {
        "title": str(item.get("title") or item.get("title_th") or "").strip(),
        "title_en": str(item.get("title_en") or item.get("english_title") or "").strip(),
        "summary": str(item.get("summary") or item.get("summary_th") or "").strip(),
        "summary_en": str(item.get("summary_en") or "").strip(),
        "script": script_th,
        "script_en": script_en,
    }


def has_english_script(topic):
    script_en = normalize_script(
        (topic or {}).get("script_en") or (topic or {}).get("script_english")
    )
    return has_script(script_en) and looks_english(" ".join(script_en.values()))


def apply_english_payload(topic, payload):
    topic = dict(topic or {})
    payload = payload or {}
    nested = payload.get("script_en") or payload.get("script") or payload
    script_en = normalize_script(nested)
    title_en = str(payload.get("title_en") or payload.get("english_title") or topic.get("title_en") or "").strip()
    summary_en = str(payload.get("summary_en") or topic.get("summary_en") or "").strip()
    if has_script(script_en) and looks_english(" ".join(script_en.values())):
        topic["script_en"] = script_en
    if title_en:
        topic["title_en"] = title_en
    if summary_en:
        topic["summary_en"] = summary_en
    return topic


def english_translate_prompt(topic):
    script = normalize_script((topic or {}).get("script"))
    return f"""
Translate this Thai mystery short-form script into natural spoken English for a 30-60 second narration.
Return JSON only, no markdown:
{{
  "title_en": "catchy English title",
  "summary_en": "one or two English sentences",
  "script_en": {{
    "hook": "",
    "context": "",
    "twist": "",
    "reveal": ""
  }}
}}
Thai title: {(topic or {}).get("title") or ""}
Thai summary: {(topic or {}).get("summary") or ""}
hook: {script.get("hook", "")}
context: {script.get("context", "")}
twist: {script.get("twist", "")}
reveal: {script.get("reveal", "")}

Rules:
- script_en must be English only
- spoken, eerie, concise — not a literal word-for-word translation
- keep the same four beats
"""


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
        fields = bilingual_fields(item)
        if not fields["title"]:
            continue
        topics.append(
            {
                "id": str(uuid.uuid4()),
                **fields,
                "broll": normalize_keywords(
                    item.get("video_keywords")
                    or item.get("broll")
                    or item.get("clip_keywords")
                ),
            }
        )
    return topics[:5]


def script_copy_text(title, script, title_en="", script_en=None, lang="ทั้งสอง"):
    thai = (
        f"{title}\n\n"
        f"ฮุค: {(script or {}).get('hook', '')}\n\n"
        f"บริบท: {(script or {}).get('context', '')}\n\n"
        f"แต่: {(script or {}).get('twist', '')}\n\n"
        f"เฉลย: {(script or {}).get('reveal', '')}"
    ).strip()
    english = (
        f"{title_en or title}\n\n"
        f"Hook: {(script_en or {}).get('hook', '')}\n\n"
        f"Context: {(script_en or {}).get('context', '')}\n\n"
        f"Twist: {(script_en or {}).get('twist', '')}\n\n"
        f"Reveal: {(script_en or {}).get('reveal', '')}"
    ).strip()
    if lang == "ไทย":
        return thai
    if lang == "English":
        return english
    if has_script(script_en):
        return f"{thai}\n\n--- English ---\n\n{english}".strip()
    return thai
