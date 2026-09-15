import tempfile
import unittest
from pathlib import Path

import numpy as np

import mascot_clip


class MascotClipTests(unittest.TestCase):
    def test_rms_envelope_follows_loud_region(self):
        samples = np.zeros(22050, dtype=np.float32)
        samples[11000:13200] = 0.9
        env = mascot_clip.rms_envelope(samples, 22050, 25)
        self.assertGreater(env.max(), 0.4)
        self.assertGreater(int(env.argmax()), 8)

    def test_fit_on_canvas_keeps_frame_size(self):
        image = np.zeros((40, 30, 3), dtype=np.uint8)
        image[:] = (10, 20, 30)
        frame = mascot_clip.fit_on_canvas(image, 80, 120, scale=1.1, offset_x=2, offset_y=-3)
        self.assertEqual(frame.shape, (120, 80, 3))

    def test_rejects_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.jpg"
            audio = Path(tmp) / "a.wav"
            audio.write_bytes(b"x")
            with self.assertRaises(mascot_clip.MascotClipError):
                mascot_clip.make_mascot_clip(missing, audio, Path(tmp) / "out.mp4")


if __name__ == "__main__":
    unittest.main()
