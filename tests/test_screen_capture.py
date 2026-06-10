"""Тесты захвата экрана."""

import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from watchalert.region import Region
from watchalert.screen_capture import (
    grab_region,
    is_black_frame,
    probe_backends,
    reset_capture_backend,
)


class TestBlackFrameDetection(unittest.TestCase):
    def test_black_image_detected(self) -> None:
        img = Image.new("RGB", (50, 50), (0, 0, 0))
        try:
            self.assertTrue(is_black_frame(img))
        finally:
            img.close()

    def test_normal_image_not_black(self) -> None:
        img = Image.new("RGB", (50, 50), (120, 130, 140))
        try:
            self.assertFalse(is_black_frame(img))
        finally:
            img.close()


class TestGrabRegionFallback(unittest.TestCase):
    def setUp(self) -> None:
        reset_capture_backend()

    def tearDown(self) -> None:
        reset_capture_backend()

    @patch("watchalert.screen_capture._try_backend")
    @patch("watchalert.screen_capture.ensure_probed")
    def test_uses_working_backend(
        self, _probe: MagicMock, try_mock: MagicMock
    ) -> None:
        good = Image.new("RGB", (10, 10), (200, 100, 50))
        try_mock.return_value = good
        with patch("watchalert.screen_capture._working_backends", ["pillow_x11"]):
            with patch("watchalert.screen_capture._active_backend", "pillow_x11"):
                img = grab_region(Region(0, 0, 10, 10))
                self.assertIs(img, good)

    @patch("watchalert.screen_capture.backend_candidates", return_value=["mss_xlib"])
    @patch(
        "watchalert.screen_capture._try_backend",
        side_effect=RuntimeError("чёрный кадр"),
    )
    def test_probe_skips_black(self, _try: MagicMock, _cand: MagicMock) -> None:
        working, errors = probe_backends(Region(0, 0, 5, 5))
        self.assertEqual(working, [])
        self.assertTrue(errors)


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
