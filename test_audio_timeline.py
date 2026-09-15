import unittest

import audio_timeline


class AudioTimelineTests(unittest.TestCase):
    def test_parse_and_format_clock(self):
        self.assertEqual(audio_timeline.parse_seconds("1:05"), 65.0)
        self.assertEqual(audio_timeline.format_clock(65), "01:05")
        self.assertEqual(audio_timeline.audio_mime_type("voice.m4a"), "audio/mp4")

    def test_normalize_segments_from_object(self):
        payload = {
            "segments": [
                {
                    "start": 8,
                    "end": "0:12",
                    "th": "แต่ความจริงไม่เป็นแบบนั้น",
                    "en": "But the truth was different",
                    "keywords": ["dark hallway", "old photograph"],
                },
                {
                    "start": 0,
                    "end": 5.2,
                    "thai": "เคยได้ยินเรื่องนี้ไหม",
                    "english": "Have you heard this story",
                    "broll": "candle flickering, foggy forest",
                },
            ]
        }
        segments = audio_timeline.normalize_segments(payload)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["start"], 0)
        self.assertIn("candle flickering", segments[0]["keywords"])
        self.assertEqual(segments[1]["th"], "แต่ความจริงไม่เป็นแบบนั้น")
        self.assertEqual(audio_timeline.format_clock(segments[1]["end"]), "00:12")


if __name__ == "__main__":
    unittest.main()
