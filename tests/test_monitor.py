"""Тесты логики: сигнал при устойчивом изменении, без повтора без нового изменения."""

import unittest

from PIL import Image

from watchalert.monitor import ChangeTracker, images_differ


def solid(color: tuple[int, int, int], size: tuple[int, int] = (80, 60)) -> Image.Image:
    return Image.new("RGB", size, color)


class TestImagesDiffer(unittest.TestCase):
    def test_identical_images(self) -> None:
        a = solid((10, 20, 30))
        self.assertFalse(images_differ(a, a.copy()))

    def test_different_images(self) -> None:
        self.assertTrue(images_differ(solid((255, 0, 0)), solid((0, 0, 255))))


class TestChangeTracker(unittest.TestCase):
    def setUp(self) -> None:
        self.delay = 2.0
        self.tracker = ChangeTracker(delay_seconds=self.delay, sensitivity="medium")
        self.t0 = 1000.0
        self.baseline = solid((0, 0, 0))
        self.changed = solid((255, 255, 255))

    def test_first_frame_sets_baseline_no_alarm(self) -> None:
        self.assertFalse(self.tracker.process_frame(self.baseline, self.t0))

    def test_persistent_change_triggers_alarm_once(self) -> None:
        self.assertFalse(self.tracker.process_frame(self.baseline, self.t0))
        self.assertFalse(self.tracker.process_frame(self.changed, self.t0 + 0.5))
        self.assertFalse(self.tracker.process_frame(self.changed, self.t0 + 1.0))
        self.assertTrue(
            self.tracker.process_frame(self.changed, self.t0 + 0.5 + self.delay)
        )

    def test_no_repeat_alarm_while_unchanged_after_signal(self) -> None:
        self.tracker.process_frame(self.baseline, self.t0)
        self.tracker.process_frame(self.changed, self.t0 + 0.5)
        self.assertTrue(
            self.tracker.process_frame(self.changed, self.t0 + 0.5 + self.delay)
        )

        for offset in range(1, 20):
            t = self.t0 + self.delay + 5 + offset
            self.assertFalse(
                self.tracker.process_frame(self.changed, t),
                f"unexpected alarm at t={t}",
            )

    def test_short_change_does_not_alarm(self) -> None:
        self.tracker.process_frame(self.baseline, self.t0)
        self.tracker.process_frame(self.changed, self.t0 + 0.5)
        self.assertFalse(self.tracker.process_frame(self.baseline, self.t0 + 1.0))
        self.assertFalse(self.tracker.process_frame(self.baseline, self.t0 + 10))

    def test_second_change_triggers_new_alarm(self) -> None:
        self.tracker.process_frame(self.baseline, self.t0)
        self.tracker.process_frame(self.changed, self.t0 + 0.5)
        self.assertTrue(
            self.tracker.process_frame(self.changed, self.t0 + 0.5 + self.delay)
        )

        another = solid((0, 255, 0))
        t1 = self.t0 + 0.5 + self.delay + 1
        self.assertFalse(self.tracker.process_frame(another, t1))
        self.assertTrue(self.tracker.process_frame(another, t1 + self.delay))

    def test_is_changing_flag(self) -> None:
        self.tracker.process_frame(self.baseline, self.t0)
        self.assertFalse(self.tracker.is_changing)
        self.tracker.process_frame(self.changed, self.t0 + 0.1)
        self.assertTrue(self.tracker.is_changing)
        self.tracker.process_frame(self.baseline, self.t0 + 0.2)
        self.assertFalse(self.tracker.is_changing)


if __name__ == "__main__":
    unittest.main()
