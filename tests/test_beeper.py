import os
import tempfile
import unittest
import wave

from aguacate.beeper import RATE, alarm_pattern, soft_note, tone, write_wav


class ToneTest(unittest.TestCase):
    def test_length(self):
        self.assertEqual(len(tone(880, 250, 0.5)), RATE // 4)

    def test_volume_scales_amplitude(self):
        loud = max(abs(s) for s in tone(880, 100, 1.0))
        quiet = max(abs(s) for s in tone(880, 100, 0.25))
        self.assertGreater(loud, 32000)
        self.assertAlmostEqual(quiet / loud, 0.25, places=2)

    def test_fades_avoid_clicks(self):
        t = tone(880, 100, 1.0)
        self.assertEqual(t[0], 0)
        self.assertLess(abs(t[-1]), 500)

    def test_zero_volume_is_silent(self):
        self.assertEqual(max(abs(s) for s in alarm_pattern(880, 250, 0.0)), 0)

    def test_soft_note_respects_volume_and_decays(self):
        n = soft_note(523, 300, 0.5)
        self.assertLessEqual(max(abs(s) for s in n), 32767 * 0.5 + 1)
        first = max(abs(s) for s in n[: len(n) // 4])
        last = max(abs(s) for s in n[-len(n) // 4:])
        self.assertLess(last, first * 0.4)          # se apaga, no corta en seco
        self.assertLess(abs(n[-1]), 200)

    def test_write_wav(self):
        path = os.path.join(tempfile.mkdtemp(), "t.wav")
        write_wav(path, alarm_pattern(523, 300, 0.4))
        with wave.open(path) as w:
            self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth()),
                             (RATE, 1, 2))
            self.assertGreater(w.getnframes(), RATE)   # > 1 s de patrón


if __name__ == "__main__":
    unittest.main()
