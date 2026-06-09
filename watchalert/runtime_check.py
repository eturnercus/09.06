"""Проверки окружения перед запуском GUI."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

from watchalert.screen_capture import is_running_as_root


def check_runtime_or_exit() -> None:
    if not is_running_as_root():
        return

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "WatchAlert",
        "Не запускайте приложение через sudo!\n\n"
        "От root нет доступа к вашему экрану и ломаются системные библиотеки "
        "(ошибка gnome-screenshot / libgobject).\n\n"
        "Запустите от обычного пользователя:\n"
        "  ./WatchAlert.AppImage\n\n"
        "Права администратора для WatchAlert не нужны.",
    )
    root.destroy()
    sys.exit(1)


def preserve_user_display_env() -> None:
    """Подсказка в stderr, если нет DISPLAY/WAYLAND (часто при sudo)."""
    if is_running_as_root():
        return
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print(
            "WatchAlert: не найден DISPLAY/WAYLAND_DISPLAY. "
            "Запускайте из графической сессии, не через ssh без -X.",
            file=sys.stderr,
        )
