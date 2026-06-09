"""Проверка наличия ключевых элементов графического интерфейса."""

import unittest

import tkinter as tk
from tkinter import ttk

from watchalert.app import WatchAlertApp


class TestWatchAlertGui(unittest.TestCase):
    def setUp(self) -> None:
        self.app = WatchAlertApp()
        self.app.root.update()

    def tearDown(self) -> None:
        self.app._on_close()

    def _button_texts(self) -> list[str]:
        texts: list[str] = []

        def walk(widget: tk.Misc) -> None:
            if isinstance(widget, (ttk.Button, tk.Button)):
                texts.append(str(widget.cget("text")))
            for child in widget.winfo_children():
                walk(child)

        walk(self.app.root)
        return texts

    def test_window_title(self) -> None:
        self.assertIn("WatchAlert", self.app.root.title())

    def test_settings_variables_exist(self) -> None:
        self.assertGreaterEqual(self.app.delay_var.get(), 1.0)
        self.assertGreaterEqual(self.app.sensitivity_var.get(), 1.0)
        self.assertIsInstance(self.app.sound_path_var.get(), str)

    def test_main_controls_present(self) -> None:
        texts = self._button_texts()
        self.assertIn("Добавить область", texts)
        self.assertIn("Удалить выбранную", texts)
        self.assertIn("Сбросить базу", texts)
        self.assertIn("▶ Старт", texts)
        self.assertIn("Обзор…", texts)
        self.assertIn("Тест", texts)

    def test_region_list_exists(self) -> None:
        self.assertIsInstance(self.app.region_list, tk.Listbox)

    def test_add_region_updates_list(self) -> None:
        from watchalert.region import Region

        before = self.app.region_list.size()
        self.app._on_region_selected(Region(10, 10, 100, 80))
        self.app.root.update()
        self.assertEqual(self.app.region_list.size(), before + 1)
        self.assertEqual(len(self.app.slots), before + 1)


if __name__ == "__main__":
    unittest.main()
