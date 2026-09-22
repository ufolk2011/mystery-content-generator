DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

# Old IDs still stored in Streamlit session / older branches.
DEPRECATED_GEMINI_MODELS = {
    "gemini-2.5-flash": DEFAULT_GEMINI_MODEL,
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.0-flash": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
    "gemini-1.5-flash": DEFAULT_GEMINI_MODEL,
    "gemini-1.5-pro": DEFAULT_GEMINI_MODEL,
}


def resolve_gemini_model(name):
    raw = str(name or "").strip() or DEFAULT_GEMINI_MODEL
    if raw.startswith("models/"):
        raw = raw[len("models/") :]
    mapped = DEPRECATED_GEMINI_MODELS.get(raw, raw)
    if mapped in GEMINI_MODELS:
        return mapped
    return DEFAULT_GEMINI_MODEL
