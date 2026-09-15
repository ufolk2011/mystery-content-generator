import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lip_sync


class LipSyncPipelineTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        for key in (
            "SADTALKER_HOME",
            "SADTALKER_SCRIPT",
            "WAV2LIP_HOME",
            "LIVEPORTRAIT_HOME",
            "LIVEPORTRAIT_SCRIPT",
            "LIPSYNC_TEMPLATE_FACE",
        ):
            os.environ.pop(key, None)
        self.workdir = Path(tempfile.mkdtemp(prefix="lipsync-test-"))

    def tearDown(self):
        self.env.stop()

    def test_require_file_missing(self):
        with self.assertRaises(lip_sync.LipSyncError):
            lip_sync.require_file(str(self.workdir / "missing.jpg"))

    def test_sadtalker_command_from_home(self):
        home = self.workdir / "SadTalker"
        script = home / "inference.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("# fake\n", encoding="utf-8")
        os.environ["SADTALKER_HOME"] = str(home)
        cmd, cwd = lip_sync.sadtalker_command("voice.wav", "face.jpg", "out")
        self.assertIn("--driven_audio", cmd)
        self.assertIn("voice.wav", cmd)
        self.assertEqual(Path(cwd), home)

    def test_live_portrait_command_flags(self):
        home = self.workdir / "LivePortrait"
        script = home / "inference.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("# fake\n", encoding="utf-8")
        os.environ["LIVEPORTRAIT_HOME"] = str(home)
        cmd, cwd = lip_sync.live_portrait_command("mascot.jpg", "drive.mp4", "out")
        self.assertEqual(cmd[cmd.index("-s") + 1], "mascot.jpg")
        self.assertEqual(cmd[cmd.index("-d") + 1], "drive.mp4")
        self.assertEqual(cmd[cmd.index("-o") + 1], "out")
        self.assertIn("--flag_crop_driving_video", cmd)
        self.assertEqual(Path(cwd), home)

    def test_pipeline_dry_run_with_driving_video(self):
        source = self.workdir / "candle_man.jpg"
        driving = self.workdir / "drive.mp4"
        source.write_bytes(b"fake-image")
        driving.write_bytes(b"fake-video")
        home = self.workdir / "LivePortrait"
        (home / "inference.py").parent.mkdir(parents=True, exist_ok=True)
        (home / "inference.py").write_text("# fake\n", encoding="utf-8")
        os.environ["LIVEPORTRAIT_HOME"] = str(home)
        plan = lip_sync.generate_lip_sync_pipeline(
            str(source),
            driving_audio_path=None,
            output_dir=str(self.workdir / "output"),
            driving_video_path=str(driving),
            dry_run=True,
        )
        self.assertEqual(len(plan["steps"]), 1)
        self.assertIn("-s", plan["steps"][0]["command"])
        self.assertTrue(str(plan["output"]).endswith("final_mascot_output.mp4"))

    def test_pipeline_requires_audio_or_driving(self):
        source = self.workdir / "face.png"
        source.write_bytes(b"x")
        with self.assertRaises(lip_sync.LipSyncError):
            lip_sync.generate_lip_sync_pipeline(str(source), output_dir=str(self.workdir / "out"))

    def test_newest_video_skips_concat(self):
        folder = self.workdir / "videos"
        folder.mkdir(parents=True, exist_ok=True)
        concat = folder / "result_concat.mp4"
        plain = folder / "result.mp4"
        concat.write_bytes(b"a")
        plain.write_bytes(b"b")
        chosen = lip_sync.newest_video(folder)
        self.assertEqual(chosen.name, "result.mp4")


class InstallLipSyncMenuTests(unittest.TestCase):
    def test_patches_studio_crop_subtitle_keys(self):
        import install_lipsync

        sample = '''
from tts import synthesize
app_page = st.sidebar.radio(
    "เมนู",
    ["studio", "crop", "subtitle"],
    format_func=lambda key: {
        "studio": "ค้นหาเรื่อง",
        "crop": "✂️ ครอปคลิป 9:16",
        "subtitle": "Auto Subtitle",
    }[key],
)
if app_page == "crop":
    render_vertical_crop_tab()
'''
        updated = install_lipsync.patch_app_text(sample)
        self.assertIn("from lip_sync import render_lip_sync_page", updated)
        self.assertIn('"lipsync"', updated)
        self.assertIn("ลิปซิงค์คาแรกเตอร์", updated)
        self.assertIn('if app_page == "lipsync":', updated)
        self.assertIn("render_lip_sync_page()", updated)

    def test_patches_thai_radio_with_scissors(self):
        import install_lipsync

        sample = '''
menu = st.sidebar.radio(
    "เมนู",
    ["ค้นหาเรื่อง", "✂️ ครอปคลิป 9:16", "Auto Subtitle"],
)
if menu == "Auto Subtitle":
    render_auto_subtitle_page()
'''
        updated = install_lipsync.patch_app_text(sample)
        self.assertIn("ลิปซิงค์คาแรกเตอร์", updated)
        self.assertIn('if menu == "ลิปซิงค์คาแรกเตอร์":', updated)


if __name__ == "__main__":
    unittest.main()
