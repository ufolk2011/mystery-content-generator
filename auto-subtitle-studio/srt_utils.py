import re
from datetime import timedelta

THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
OFFSET_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)(s|ms|m)?\s*$", re.IGNORECASE)


def offset_to_ms(value):
    if value is None or value == "":
        return 0
    if isinstance(value, timedelta):
        return max(0, int(value.total_seconds() * 1000))
    if isinstance(value, (int, float)):
        # SDK sometimes yields seconds as a float.
        if isinstance(value, float) and value < 10_000:
            return max(0, int(round(value * 1000)))
        return max(0, int(value))
    if hasattr(value, "total_seconds"):
        try:
            return max(0, int(value.total_seconds() * 1000))
        except TypeError:
            pass
    seconds = getattr(value, "seconds", None)
    if seconds is not None:
        nanos = getattr(value, "nanoseconds", None)
        if nanos is None:
            nanos = getattr(value, "nanos", 0) or 0
        return max(0, int(seconds * 1000 + nanos / 1_000_000))
    text = str(value).strip()
    match = OFFSET_RE.match(text)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = (match.group(2) or "s").lower()
    if unit == "ms":
        return max(0, int(round(amount)))
    if unit == "m":
        return max(0, int(round(amount * 60_000)))
    return max(0, int(round(amount * 1000)))


def ms_to_srt_time(ms):
    ms = max(0, int(ms))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def join_word_texts(texts):
    cleaned = [str(part).strip() for part in texts if str(part).strip()]
    if not cleaned:
        return ""
    if all(THAI_RE.search(part) and " " not in part for part in cleaned):
        return "".join(cleaned)
    return " ".join(cleaned)


def group_words(words, words_per_line):
    count = max(1, min(4, int(words_per_line or 1)))
    cues = []
    for index in range(0, len(words), count):
        chunk = words[index : index + count]
        start_ms = chunk[0]["start_ms"]
        end_ms = max(chunk[-1]["end_ms"], start_ms + 40)
        cues.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "start": ms_to_srt_time(start_ms),
                "end": ms_to_srt_time(end_ms),
                "text": join_word_texts(item["text"] for item in chunk),
            }
        )
    return cues


def cues_to_srt(cues):
    blocks = []
    for index, cue in enumerate(cues, start=1):
        start = cue.get("start") or ms_to_srt_time(cue.get("start_ms", 0))
        end = cue.get("end") or ms_to_srt_time(cue.get("end_ms", 0))
        text = str(cue.get("text") or "").strip()
        if not text:
            continue
        blocks.append(f"{index}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def parse_srt_time(value):
    text = str(value or "").strip().replace(".", ",")
    match = re.match(r"^(\d{1,2}):(\d{2}):(\d{2}),(\d{1,3})$", text)
    if not match:
        return 0
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    millis = int(str(millis).ljust(3, "0")[:3])
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
