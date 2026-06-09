"""Тесты захвата экрана на Linux."""

import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from watchalert.region import Region
from watchalert.screen_capture import (
    _is_black_frame,
    grab_region,
    reset_capture_backend,
)


class TestBlackFrameDetection(unittest.TestCase):
    def test_black_image_detected(self) -> None:
        img = Image.new("RGB", (50, 50), (0, 0, 0))
        try:
            self.assertTrue(_is_black_frame(img))
        finally:
            img.close()

    def test_normal_image_not_black(self) -> None:
        img = Image.new("RGB", (50, 50), (120, 130, 140))
        try:
            self.assertFalse(_is_black_frame(img))
        finally:
            img.close()


class TestGrabRegionFallback(unittest.TestCase):
    def setUp(self) -> None:
        reset_capture_backend()

    def tearDown(self) -> None:
        reset_capture_backend()

    @patch("watchalert.screen_capture._capture_with_backend")
    def test_skips_black_tries_next_backend(self, capture_mock: MagicMock) -> None:
        black = Image.new("RGB", (10, 10), (0, 0, 0))
        good = Image.new("RGB", (10, 10), (200, 100, 50))
        capture_mock.side_effect = [black, good]
        region = Region(0, 0, 10, 10)
        try:
            img = grab_region(region)
            self.assertIs(img, good)
            self.assertEqual(capture_mock.call_count, 2)
        finally:
            good.close()

    @patch("watchalert.screen_capture._all_backends", return_value=["mss_xlib"])
    @patch("watchalert.screen_capture._capture_with_backend")
    def test_all_black_raises(self, capture_mock: MagicMock, _backends: MagicMock) -> None:
        black = Image.new("RGB", (5, 5), (0, 0, 0))
        capture_mock.return_value = black
        with self.assertRaises(RuntimeError):
            grab_region(Region(0, 0, 5, 5))
        black.close()


class TestListMonitors(unittest.TestCase):
    @patch("mss.MSS")
    def test_list_monitors_skips_virtual(self, mss_cls: MagicMock) -> None:
        from watchalert.screen_capture import list_monitors

        inst = mss_cls.return_value.__enter__.return_value
        inst.monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]
        monitors = list_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[1]["left"], 1920)


if __name__ == "__main__":
    unittest.main()
