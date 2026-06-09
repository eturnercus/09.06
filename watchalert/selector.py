"""Выбор области экрана поверх снимка экрана (без чёрного оверлея)."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from PIL import Image, ImageTk

from watchalert.region import Region
from watchalert.screen_capture import grab_virtual_screen


class RegionSelector:
    """Полноэкранный выбор области: фон — замороженный скриншот."""

    def __init__(self, root: tk.Tk, on_selected: Callable[[Region], None]) -> None:
        self.root = root
        self.on_selected = on_selected
        self.win: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self.start_x = 0
        self.start_y = 0
        self.rect_id: int | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._screenshot: Image.Image | None = None
        self._monitor: dict[str, int] | None = None
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._display_w = 0
        self._display_h = 0

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        # Прячем главное окно, чтобы оно не попало в снимок.
        self.root.update_idletasks()
        was_withdrawn = False
        try:
            if self.root.state() != "withdrawn":
                self.root.withdraw()
                was_withdrawn = True
            self.root.update()
            screenshot, monitor = grab_virtual_screen()
        except Exception as exc:
            if was_withdrawn:
                self.root.deiconify()
            from tkinter import messagebox

            messagebox.showerror(
                "WatchAlert",
                f"Не удалось снять экран для выбора области:\n{exc}",
            )
            return

        self._screenshot = screenshot
        self._monitor = monitor

        self.win = tk.Toplevel(self.root)
        self.win.title("Выберите область")
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1a1a1a")
        self.win.bind("<Escape>", lambda _e: self._cancel(was_withdrawn))

        self._display_w = self.win.winfo_screenwidth()
        self._display_h = self.win.winfo_screenheight()
        self._scale_x = screenshot.width / max(self._display_w, 1)
        self._scale_y = screenshot.height / max(self._display_h, 1)

        display_img = screenshot.copy()
        if (display_img.width, display_img.height) != (self._display_w, self._display_h):
            display_img = display_img.resize(
                (self._display_w, self._display_h), Image.Resampling.BILINEAR
            )
        self._photo = ImageTk.PhotoImage(display_img)
        display_img.close()

        self.canvas = tk.Canvas(
            self.win,
            width=self._display_w,
            height=self._display_h,
            highlightthickness=0,
            bg="#1a1a1a",
            cursor="cross",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW)

        # Подсказка на тёмной плашке (без прозрачности — работает везде).
        self.canvas.create_rectangle(
            0, 0, self._display_w, 56, fill="#000000", outline="", stipple="gray50"
        )
        self.canvas.create_text(
            self._display_w // 2,
            28,
            text="Выделите область мышью. Esc — отмена.",
            fill="white",
            font=("Segoe UI", 14, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self._on_release(e, was_withdrawn))

    def _canvas_to_screen(self, x: int, y: int) -> tuple[int, int]:
        mon = self._monitor or {"left": 0, "top": 0}
        sx = int(x * self._scale_x) + mon["left"]
        sy = int(y * self._scale_y) + mon["top"]
        return sx, sy

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
            width=3,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self.canvas and self.rect_id is not None:
            self.canvas.coords(
                self.rect_id, self.start_x, self.start_y, event.x, event.y
            )

    def _on_release(self, event: tk.Event, restore_main: bool) -> None:
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left_c = min(x1, x2)
        top_c = min(y1, y2)
        width_c = abs(x2 - x1)
        height_c = abs(y2 - y1)

        if width_c < 10 or height_c < 10:
            return

        left, top = self._canvas_to_screen(left_c, top_c)
        right, bottom = self._canvas_to_screen(left_c + width_c, top_c + height_c)
        region = Region(left, top, max(1, right - left), max(1, bottom - top))
        self._close(restore_main)
        self.on_selected(region)

    def _cancel(self, restore_main: bool) -> None:
        self._close(restore_main)

    def _close(self, restore_main: bool = True) -> None:
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = None
        self.canvas = None
        self.rect_id = None
        self._photo = None
        if self._screenshot is not None:
            self._screenshot.close()
            self._screenshot = None
        if restore_main:
            self.root.deiconify()
