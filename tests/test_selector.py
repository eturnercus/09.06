"""Тесты выбора области: координаты и отсутствие чёрного оверлея."""

import unittest
from unittest.mock import MagicMock, patch

import tkinter as tk
from PIL import Image

from watchalert.region import Region
from watchalert.selector import RegionSelector


class TestRegionSelector(unittest.TestCase):
    def test_canvas_to_screen_with_scale(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            sel = RegionSelector(root, lambda _r: None)
            sel._monitor = {"left": 100, "top": 50, "width": 3840, "height": 2160}
            sel._scale_x = 2.0
            sel._scale_y = 2.0
            sx, sy = sel._canvas_to_screen(10, 20)
            self.assertEqual(sx, 120)
            self.assertEqual(sy, 90)
        finally:
            root.destroy()

    @patch("watchalert.selector.grab_virtual_screen")
    def test_open_uses_screenshot_not_alpha_overlay(self, grab_mock: MagicMock) -> None:
        img = Image.new("RGB", (100, 80), (255, 0, 0))
        grab_mock.return_value = (img, {"left": 0, "top": 0, "width": 100, "height": 80})

        root = tk.Tk()
        root.geometry("200x200")
        selected: list[Region] = []

        try:
            sel = RegionSelector(root, selected.append)
            sel.open()
            root.update()

            self.assertIsNotNone(sel.win)
            self.assertIsNotNone(sel._photo)
            # Не используем -alpha (источник чёрного экрана на Windows).
            alpha = sel.win.attributes("-alpha")
            self.assertNotEqual(alpha, 0.25)

            sel._on_press(type("E", (), {"x": 10, "y": 10})())
            sel._on_release(
                type("E", (), {"x": 60, "y": 50})(),
                restore_main=True,
            )
            root.update()
            self.assertEqual(len(selected), 1)
            self.assertGreater(selected[0].width, 0)
        finally:
            if sel.win and sel.win.winfo_exists():
                sel.win.destroy()
            root.destroy()
            img.close()


if __name__ == "__main__":
    unittest.main()
