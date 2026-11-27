import unittest

from aguacate.beeper import RATE, alarm_pattern, tone


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


if __name__ == "__main__":
    unittest.main()
