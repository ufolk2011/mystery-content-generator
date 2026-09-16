import unittest

from script_utils import (
    apply_english_payload,
    bilingual_fields,
    has_english_script,
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

    def test_copy_thai_only(self):
        text = script_copy_text(
            "แห่งไอซ์แลนด์",
            {"hook": "ฮุคไทย", "context": "บริบท", "twist": "แต่", "reveal": "เฉลย"},
            "Iceland",
            {"hook": "English hook", "context": "Context", "twist": "Twist", "reveal": "Reveal"},
            "ไทย",
        )
        self.assertIn("ฮุคไทย", text)
        self.assertNotIn("English hook", text)
        self.assertNotIn("--- English ---", text)

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
        self.assertNotIn("--- English ---", text)

    def test_apply_english_payload(self):
        topic = apply_english_payload(
            {"title": "แห่งไอซ์แลนด์", "script": {"hook": "ฮุคไทย"}},
            {
                "title_en": "The Icelandic Necropants",
                "summary_en": "A grim folklore tale.",
                "script_en": {
                    "hook": "Would you trade a human skin for a fortune?",
                    "context": "In 17th century Iceland the legend spread quietly",
                    "twist": "But the museum piece is not original",
                    "reveal": "Historians say it is a replica",
                },
            },
        )
        self.assertTrue(has_english_script(topic))
        self.assertEqual(topic["title_en"], "The Icelandic Necropants")

    def test_saved_thai_story_has_no_english_until_translated(self):
        topic = bilingual_fields(
            {
                "title": "เงาหลอนแห่งเทือกเขาบร็อคเคน",
                "script": {
                    "hook": "ถ้าคุณเดินขึ้นเขาคนเดียวกลางหมอก",
                    "context": "บนยอดเขาบร็อคเคน",
                    "twist": "แต่เมื่อมีคนใจกล้าเดินเข้าไป",
                    "reveal": "แท้จริงแล้วมันคือปรากฏการณ์ทางแสง",
                },
            }
        )
        self.assertFalse(has_english_script(topic))


if __name__ == "__main__":
    unittest.main()
