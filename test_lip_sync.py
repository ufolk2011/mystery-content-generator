import inspect
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import lip_sync


class LipSyncTests(unittest.TestCase):
    def test_source_has_no_model_folder_checks(self):
        source = inspect.getsource(lip_sync)
        lowered = source.lower()
        self.assertNotIn("sadtalker", lowered)
        self.assertNotIn("liveportrait", lowered)
        self.assertNotIn("wav2lip", lowered)
        self.assertNotIn("checkpoint", lowered)
        self.assertNotIn("model_dir", lowered)
        self.assertNotIn("os.environ", lowered)

    def test_rejects_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.jpg"
            audio = Path(tmp) / "a.wav"
            audio.write_bytes(b"x")
            with self.assertRaises(lip_sync.LipSyncError):
                lip_sync.make_lip_sync_clip(missing, audio, Path(tmp) / "out.mp4")

    def test_moviepy_muxes_image_and_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            image = tmp / "mascot.png"
            audio = tmp / "voice.wav"
            out = tmp / "out.mp4"
            try:
                from PIL import Image
            except ImportError:
                self.skipTest("Pillow not installed")
            Image.new("RGB", (64, 80), (40, 90, 200)).save(image)
            sample_rate = 22050
            n_samples = int(sample_rate * 0.35)
            pcm = b"".join(
                struct.pack(
                    "<h",
                    int(0.2 * math.sin(2 * math.pi * 440 * index / sample_rate) * 32767),
                )
                for index in range(n_samples)
            )
            with wave.open(str(audio), "w") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(pcm)
            result = lip_sync.make_lip_sync_clip(
                image, audio, out, fps=10, install_if_missing=False
            )
            self.assertTrue(Path(result).is_file())
            self.assertGreater(Path(result).stat().st_size, 1000)

    def test_ffmpeg_fallback_muxes_without_moviepy(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            image = tmp / "mascot.png"
            audio = tmp / "voice.wav"
            out = tmp / "out.mp4"
            try:
                from PIL import Image
            except ImportError:
                self.skipTest("Pillow not installed")
            Image.new("RGB", (64, 80), (40, 90, 200)).save(image)
            sample_rate = 22050
            n_samples = int(sample_rate * 0.35)
            pcm = b"".join(
                struct.pack(
                    "<h",
                    int(0.2 * math.sin(2 * math.pi * 440 * index / sample_rate) * 32767),
                )
                for index in range(n_samples)
            )
            with wave.open(str(audio), "w") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(pcm)
            lip_sync._mux_with_ffmpeg(image, audio, out, fps=10)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
