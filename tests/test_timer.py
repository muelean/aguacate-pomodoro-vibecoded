import unittest

from aguacate.timer import (
    Pomodoro, WORK, BREAK, READY, RUNNING, PAUSED, ALARM,
    EV_WORK_DONE, EV_BREAK_DONE, EV_ALARM_STOPPED,
)


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class PomodoroTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.p = Pomodoro(work_seconds=60, break_seconds=10, clock=self.clock)

    def test_starts_ready_full(self):
        self.assertEqual((self.p.phase, self.p.status), (WORK, READY))
        self.assertEqual(self.p.remaining(), 60)
        self.assertFalse(self.p.is_work_running())

    def test_click_starts_and_counts(self):
        self.p.click()
        self.assertTrue(self.p.is_work_running())
        self.clock.t += 15
        self.assertEqual(self.p.remaining(), 45)
        self.assertAlmostEqual(self.p.fraction_left(), 0.75)

    def test_pause_freezes_time(self):
        self.p.click()
        self.clock.t += 20
        self.p.click()
        self.assertEqual(self.p.status, PAUSED)
        self.clock.t += 100
        self.assertEqual(self.p.remaining(), 40)
        self.assertFalse(self.p.is_work_running())
        self.p.click()
        self.clock.t += 10
        self.assertEqual(self.p.remaining(), 30)

    def test_full_cycle(self):
        self.p.click()
        self.clock.t += 61
        self.assertEqual(self.p.tick(), EV_WORK_DONE)
        self.assertEqual(self.p.status, ALARM)
        self.assertIsNone(self.p.tick())            # no repite el evento
        self.assertEqual(self.p.click(), EV_ALARM_STOPPED)
        self.assertEqual((self.p.phase, self.p.status), (BREAK, RUNNING))
        self.clock.t += 10
        self.assertEqual(self.p.tick(), EV_BREAK_DONE)
        self.assertEqual((self.p.phase, self.p.status), (WORK, READY))
        self.assertEqual(self.p.remaining(), 60)

    def test_reset(self):
        self.p.click()
        self.clock.t += 30
        self.p.reset()
        self.assertEqual((self.p.phase, self.p.status, self.p.remaining()), (WORK, READY, 60))

    def test_set_durations_when_ready_applies_now(self):
        self.p.set_durations(work_seconds=120)
        self.assertEqual(self.p.remaining(), 120)

    def test_set_durations_when_running_keeps_current(self):
        self.p.click()
        self.clock.t += 10
        self.p.set_durations(work_seconds=120)
        self.assertEqual(self.p.remaining(), 50)


if __name__ == "__main__":
    unittest.main()
