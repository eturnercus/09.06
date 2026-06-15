"""Проверка стабильности при длительной обработке кадров (без утечки памяти)."""

import unittest

from PIL import Image

from watchalert.monitor import ChangeTracker, images_differ


def solid(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (120, 90), color)


class TestLongRunStability(unittest.TestCase):
    def test_many_frames_constant_memory_pattern(self) -> None:
        """Тысячи кадров без накопления — только один эталон в трекере."""
        tracker = ChangeTracker(delay_seconds=2.0, sensitivity="medium")
        base = solid((10, 10, 10))
        alarms = 0
        t = 0.0
        try:
            for i in range(3000):
                frame = base.copy()
                try:
                    if tracker.process_frame(frame, t):
                        alarms += 1
                finally:
                    frame.close()
                t += 0.4
            self.assertEqual(alarms, 0)
            self.assertIsNotNone(tracker._reference)
        finally:
            base.close()
            tracker.reset_baseline()

    def test_images_differ_does_not_accumulate(self) -> None:
        a = solid((1, 2, 3))
        b = solid((4, 5, 6))
        try:
            for _ in range(5000):
                images_differ(a, b)
        finally:
            a.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
