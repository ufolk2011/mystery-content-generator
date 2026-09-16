import unittest

import lip_sync
import mascot_clip


class MascotClipCompatTests(unittest.TestCase):
    def test_wrapper_points_at_moviepy_lip_sync(self):
        self.assertIs(mascot_clip.make_mascot_clip, lip_sync.make_lip_sync_clip)
        self.assertIs(mascot_clip.render_mascot_clip_page, lip_sync.render_lip_sync_page)


if __name__ == "__main__":
    unittest.main()
