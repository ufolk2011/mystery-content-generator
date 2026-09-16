import unittest

from script_utils import (
    has_script,
    looks_english,
    normalize_script,
    normalize_topics,
    script_copy_text,
)


class BilingualScriptTests(unittest.TestCase):
    def test_looks_english(self):
        self.assertTrue(looks_english("Would you trade your own skin for a fortune?"))
        self.assertFalse(looks_english("คุณจะยอมแลกผิวหนังคนจริง ๆ เพื่อความรวยไหม"))

    def test_normalize_english_labeled_text(self):
        script = normalize_script(
            "Hook: Would you trade a fortune?\nContext: Iceland.\nTwist: But wait.\nReveal: It was a replica."
        )
        self.assertEqual(script["hook"], "Would you trade a fortune?")
        self.assertEqual(script["reveal"], "It was a replica.")

    def test_normalize_topics_keeps_script_en(self):
        topics = normalize_topics(
            [
                {
                    "title": "แห่งไอซ์แลนด์",
                    "title_en": "The Icelandic Necropants",
                    "summary": "ตำนานถุงหนัง",
                    "summary_en": "A grim folklore about wealth.",
                    "script": {
                        "hook": "คุณจะยอมแลกผิวหนังคนจริง ๆ เพื่อความรวยไหม",
                        "context": "ในศตวรรษที่ 17",
                        "twist": "แต่ปัจจุบันพิพิธภัณฑ์จัดแสดง",
                        "reveal": "นักประวัติศาสตร์บอกว่าเป็นจำลอง",
                    },
                    "script_en": {
                        "hook": "Would you trade a human skin for a fortune?",
                        "context": "In 17th century Iceland",
                        "twist": "But the museum display is not what it seems",
                        "reveal": "Historians say it is a replica",
                    },
                }
            ]
        )
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["title_en"], "The Icelandic Necropants")
        self.assertTrue(has_script(topics[0]["script_en"]))
        self.assertIn("human skin", topics[0]["script_en"]["hook"])
        self.assertIn("ผิวหนัง", topics[0]["script"]["hook"])

    def test_swaps_when_english_landed_in_thai_field(self):
        topics = normalize_topics(
            [
                {
                    "title": "เรื่องทดสอบ",
                    "script": {
                        "hook": "Would you trade a human skin for a fortune?",
                        "context": "In 17th century Iceland the legend spread",
                        "twist": "But the museum display is not real",
                        "reveal": "Historians say it is a replica",
                    },
                    "script_en": {
                        "hook": "คุณจะยอมแลกผิวหนังคนจริง ๆ เพื่อความรวยไหม",
                        "context": "ในศตวรรษที่ 17",
                        "twist": "แต่ปัจจุบันพิพิธภัณฑ์จัดแสดง",
                        "reveal": "นักประวัติศาสตร์บอกว่าเป็นจำลอง",
                    },
                }
            ]
        )
        self.assertIn("ผิวหนัง", topics[0]["script"]["hook"])
        self.assertIn("human skin", topics[0]["script_en"]["hook"])

    def test_copy_text_includes_english(self):
        text = script_copy_text(
            "แห่งไอซ์แลนด์",
            {"hook": "ฮุคไทย", "context": "บริบท", "twist": "แต่", "reveal": "เฉลย"},
            "Iceland",
            {"hook": "English hook", "context": "Context", "twist": "Twist", "reveal": "Reveal"},
            "ทั้งสอง",
        )
        self.assertIn("ฮุคไทย", text)
        self.assertIn("English hook", text)
        self.assertIn("--- English ---", text)

    def test_copy_english_only(self):
        text = script_copy_text(
            "แห่งไอซ์แลนด์",
            {"hook": "ฮุคไทย", "context": "", "twist": "", "reveal": ""},
            "Iceland",
            {"hook": "English hook", "context": "", "twist": "", "reveal": ""},
            "English",
        )
        self.assertIn("English hook", text)
        self.assertNotIn("ฮุคไทย", text)


if __name__ == "__main__":
    unittest.main()
