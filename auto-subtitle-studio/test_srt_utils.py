from srt_utils import cues_to_srt, group_words, ms_to_srt_time, offset_to_ms


def test_offset_parsing():
    assert offset_to_ms("0.100s") == 100
    assert offset_to_ms("1.5s") == 1500
    assert offset_to_ms("250ms") == 250


def test_group_two_words_and_srt():
    words = [
        {"text": "Hello", "start_ms": 100, "end_ms": 400},
        {"text": "world", "start_ms": 420, "end_ms": 800},
        {"text": "today", "start_ms": 850, "end_ms": 1100},
    ]
    cues = group_words(words, 2)
    assert len(cues) == 2
    assert cues[0]["text"] == "Hello world"
    assert cues[0]["start"] == "00:00:00,100"
    assert cues[1]["text"] == "today"
    srt = cues_to_srt(cues)
    assert "1\n00:00:00,100 --> 00:00:00,800\nHello world" in srt
    assert ms_to_srt_time(3661001) == "01:01:01,001"


def test_thai_words_join_without_spaces():
    words = [
        {"text": "สวัสดี", "start_ms": 0, "end_ms": 300},
        {"text": "ครับ", "start_ms": 310, "end_ms": 500},
    ]
    cues = group_words(words, 2)
    assert cues[0]["text"] == "สวัสดีครับ"
