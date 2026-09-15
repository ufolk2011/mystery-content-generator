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
        self.assertTrue(any("candle flickering" in item for item in segments[0]["keywords"]))
        self.assertIn("vintage archival photo style", segments[0]["keywords"][0])
        self.assertEqual(segments[1]["th"], "แต่ความจริงไม่เป็นแบบนั้น")
        self.assertEqual(audio_timeline.format_clock(segments[1]["end"]), "00:12")

    def test_english_copy_in_thai_field_is_detected(self):
        self.assertTrue(audio_timeline.looks_like_english("The Pollock family lost their two young daughters"))
        self.assertFalse(audio_timeline.looks_like_thai("The Pollock family lost their two young daughters"))
        payload = {
            "segments": [
                {
                    "start": 0,
                    "end": 8,
                    "th": "The Pollock family lost their two young daughters",
                    "en": "The Pollock family lost their two young daughters",
                }
            ]
        }
        segments = audio_timeline.normalize_segments(payload)
        self.assertTrue(audio_timeline.looks_like_english(segments[0]["th"]))
        self.assertTrue(audio_timeline.looks_like_english(segments[0]["en"]))

    def test_broll_style_suffix_is_appended(self):
        styled = audio_timeline.with_broll_style("twin babies family")
        self.assertTrue(styled.startswith("twin babies family, "))
        self.assertIn("vintage archival photo style", styled)
        self.assertIn("grainy old documentary look", styled)
        self.assertIn("dark moody cinematic", styled)
        self.assertIn("historical true crime aesthetic", styled)
        again = audio_timeline.with_broll_style(styled)
        self.assertEqual(styled, again)

    def test_busy_error_detection(self):
        err = RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
        self.assertTrue(audio_timeline.is_busy_error(err))
        self.assertFalse(audio_timeline.is_busy_error(RuntimeError("invalid api key")))


if __name__ == "__main__":
    unittest.main()
