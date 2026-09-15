import unittest

import studio_update


OLD_APP = '''
menu = st.sidebar.radio(
    "เมนู",
    ["ค้นหาเรื่อง", "✂️ ครอปคลิป 9:16", "Auto Subtitle", "ลิปซิงค์"],
    key="menu",
)

if menu in ("ลิปซิงค์", "สร้างคลิปมาสคอต"):
    render_lip_sync_page()
    st.stop()

with tab2:
    st.subheader("อัปโหลด")
    st.info("เลือกเรื่องจากแท็บ 1 หรือเรื่องที่เก็บไว้ แล้วแตกฉากหาคลิปประกอบได้ด้านล่าง")
'''


class StudioUpdateTests(unittest.TestCase):
    def test_patches_radio_route_and_tab2(self):
        patched, changed = studio_update.patch_app_text(OLD_APP)
        self.assertTrue(changed)
        self.assertIn('"ไทม์ไลน์เสียง"', patched)
        self.assertIn("render_audio_timeline_page(embed=True)", patched)
        self.assertIn('if menu in ("ไทม์ไลน์เสียง", "ไทม์ไลน์"):', patched)

    def test_patch_is_idempotent(self):
        once, _ = studio_update.patch_app_text(OLD_APP)
        twice, changed = studio_update.patch_app_text(once)
        self.assertFalse(changed)
        self.assertEqual(once.count("ไทม์ไลน์เสียง"), twice.count("ไทม์ไลน์เสียง"))


if __name__ == "__main__":
    unittest.main()
