import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave


SCRIPT = Path(__file__).resolve().parents[1] / "video/scripts/make-audio.py"
SPEC = importlib.util.spec_from_file_location("video_audio", SCRIPT)
audio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audio)


class VideoAudioTests(unittest.TestCase):
    def test_production_settings_match_the_video(self):
        self.assertEqual(audio.RATE, 24000)
        self.assertEqual(audio.DURATION, 52)

    def test_score_is_deterministic_stereo_pcm_and_creates_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "nested/first.wav"
            second = Path(directory) / "second.wav"
            with patch.object(audio, "RATE", 800), patch.object(audio, "DURATION", 2):
                audio.make_audio(first)
                audio.make_audio(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with wave.open(str(first), "rb") as score:
                self.assertEqual(score.getnchannels(), 2)
                self.assertEqual(score.getsampwidth(), 2)
                self.assertEqual(score.getframerate(), 800)
                self.assertEqual(score.getnframes(), 1600)
                self.assertEqual(score.getcomptype(), "NONE")

    def test_score_contains_unclipped_audio_with_stereo_variation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "score.wav"
            with patch.object(audio, "RATE", 800), patch.object(audio, "DURATION", 2):
                audio.make_audio(target)
            with wave.open(str(target), "rb") as score:
                samples = list(struct.iter_unpack("<hh", score.readframes(1600)))
            peak = max(abs(value) for pair in samples for value in pair)
            self.assertGreater(peak, 100)
            self.assertLess(peak, 32767)
            self.assertEqual(samples[0], (0, 0))
            self.assertTrue(any(left != right for left, right in samples))


if __name__ == "__main__":
    unittest.main()
