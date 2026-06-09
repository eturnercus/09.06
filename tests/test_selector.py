"""Тесты выбора области на нескольких мониторах."""

import unittest
from unittest.mock import MagicMock, patch

import tkinter as tk
from PIL import Image, ImageTk

from watchalert.region import Region
from watchalert.selector import RegionSelector


class TestRegionSelector(unittest.TestCase):
    def test_local_to_screen_1to1(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            sel = RegionSelector(root, lambda _r: None)
            from watchalert.selector import _MonitorOverlay

            mon = {"left": 1920, "top": 0, "width": 1920, "height": 1080}
            overlay = _MonitorOverlay(
                index=1,
                monitor=mon,
                win=root,
                canvas=tk.Canvas(root),
                photo=ImageTk.PhotoImage(Image.new("RGB", (10, 10))),
                screenshot=Image.new("RGB", (10, 10)),
            )
            sx, sy = sel._local_to_screen(overlay, 100, 50)
            self.assertEqual(sx, 2020)
            self.assertEqual(sy, 50)
            overlay.screenshot.close()
        finally:
            root.destroy()


class TestScreenCapture(unittest.TestCase):
    @patch("watchalert.screen_capture.mss.mss")
    def test_list_monitors_skips_virtual(self, mss_mock: MagicMock) -> None:
        from watchalert.screen_capture import list_monitors

        inst = mss_mock.return_value.__enter__.return_value
        inst.monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]
        monitors = list_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[1]["left"], 1920)


class TestRegionSelectorUI(unittest.TestCase):
    @patch("watchalert.selector.grab_monitor")
    @patch("watchalert.selector.list_monitors")
    def test_one_overlay_per_monitor(
        self, list_mock: MagicMock, grab_mock: MagicMock
    ) -> None:
        list_mock.return_value = [
            {"left": 0, "top": 0, "width": 800, "height": 600},
            {"left": 800, "top": 0, "width": 800, "height": 600},
        ]
        img1 = Image.new("RGB", (800, 600), (255, 0, 0))
        img2 = Image.new("RGB", (800, 600), (0, 0, 255))
        grab_mock.side_effect = [img1, img2]

        root = tk.Tk()
        root.geometry("200x200")
        selected: list[Region] = []

        try:
            sel = RegionSelector(root, selected.append)
            sel.open()
            root.update()
            self.assertEqual(len(sel._overlays), 2)
            self.assertEqual(grab_mock.call_count, 2)

            ov = sel._overlays[1]
            ov.start_x, ov.start_y = 10, 10
            sel._on_release(ov, type("E", (), {"x": 110, "y": 90})())
            root.update()

            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0].x, 810)
            self.assertEqual(selected[0].y, 10)
            self.assertEqual(selected[0].width, 100)
            self.assertEqual(selected[0].height, 80)
        finally:
            sel._close_all()
            root.destroy()
            img1.close()
            img2.close()


if __name__ == "__main__":
    unittest.main()
