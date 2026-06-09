"""Полноэкранный выбор прямоугольной области."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from watchalert.monitor import Region


class RegionSelector:
    """Полупрозрачное окно для выделения области экрана мышью."""

    def __init__(self, root: tk.Tk, on_selected: Callable[[Region], None]) -> None:
        self.root = root
        self.on_selected = on_selected
        self.win: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self.start_x = 0
        self.start_y = 0
        self.rect_id: int | None = None

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        self.win = tk.Toplevel(self.root)
        self.win.title("Выберите область")
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.25)
        self.win.configure(bg="black")
        self.win.bind("<Escape>", lambda _e: self._cancel())

        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.win,
            width=screen_w,
            height=screen_h,
            highlightthickness=0,
            bg="black",
            cursor="cross",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        hint = self.canvas.create_text(
            screen_w // 2,
            40,
            text="Зажмите левую кнопку мыши и выделите область. Esc — отмена.",
            fill="white",
            font=("Segoe UI", 14, "bold"),
        )
        self.canvas.tag_raise(hint)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _on_press(self, event: tk.Event) -> None:
        if not self.canvas:
            return
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="#00ff88",
            width=2,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self.canvas and self.rect_id is not None:
            self.canvas.coords(
                self.rect_id, self.start_x, self.start_y, event.x, event.y
            )

    def _on_release(self, event: tk.Event) -> None:
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        if width < 10 or height < 10:
            return

        region = Region(left, top, width, height)
        self._close()
        self.on_selected(region)

    def _cancel(self) -> None:
        self._close()

    def _close(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = None
        self.canvas = None
        self.rect_id = None
