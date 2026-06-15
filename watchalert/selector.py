"""Выбор области: на каждом мониторе своё окно со снимком 1:1."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from PIL import Image, ImageTk

from watchalert.region import Region
from watchalert.screen_capture import grab_monitor, list_monitors


@dataclass
class _MonitorOverlay:
    index: int
    monitor: dict[str, int]
    win: tk.Toplevel
    canvas: tk.Canvas
    photo: ImageTk.PhotoImage
    screenshot: Image.Image
    rect_id: int | None = None
    start_x: int = 0
    start_y: int = 0


class RegionSelector:
    """На каждом мониторе — своё окно со снимком 1:1. Выделите область на нужном."""

    def __init__(self, root: tk.Tk, on_selected: Callable[[Region], None]) -> None:
        self.root = root
        self.on_selected = on_selected
        self._overlays: list[_MonitorOverlay] = []
        self._restore_main = False

    def open(self) -> None:
        if self._overlays:
            self._overlays[0].win.lift()
            return

        self.root.update_idletasks()
        self._restore_main = False
        try:
            if self.root.state() != "withdrawn":
                self.root.withdraw()
                self._restore_main = True
            self.root.update()
            monitors = list_monitors()
            if not monitors:
                raise RuntimeError("Мониторы не обнаружены")
        except Exception as exc:
            if self._restore_main:
                self.root.deiconify()
            from tkinter import messagebox

            messagebox.showerror(
                "WatchAlert",
                f"Не удалось подготовить выбор области:\n{exc}",
            )
            return

        hint = (
            "Выделите область на нужном мониторе. Esc — отмена."
            if len(monitors) > 1
            else "Выделите область мышью. Esc — отмена."
        )

        for i, mon in enumerate(monitors):
            try:
                screenshot = grab_monitor(mon)
            except Exception:
                continue
            self._create_overlay(i, mon, screenshot, hint)

        if not self._overlays:
            if self._restore_main:
                self.root.deiconify()
            from tkinter import messagebox

            messagebox.showerror("WatchAlert", "Не удалось снять экран ни с одного монитора.")
            return

    def _create_overlay(
        self,
        index: int,
        monitor: dict[str, int],
        screenshot: Image.Image,
        hint: str,
    ) -> None:
        w, h = monitor["width"], monitor["height"]
        left, top = monitor["left"], monitor["top"]

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.geometry(f"{w}x{h}+{left}+{top}")
        win.configure(bg="#1a1a1a")
        win.bind("<Escape>", lambda _e: self._cancel())

        photo = ImageTk.PhotoImage(screenshot)
        canvas = tk.Canvas(
            win,
            width=w,
            height=h,
            highlightthickness=0,
            bg="#1a1a1a",
            cursor="cross",
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)

        if len(self._overlays) == 0 or index == 0:
            canvas.create_rectangle(0, 0, w, 52, fill="#000000", outline="", stipple="gray50")
            canvas.create_text(
                w // 2,
                26,
                text=hint,
                fill="white",
                font=("Segoe UI", 13, "bold"),
            )

        overlay = _MonitorOverlay(
            index=index,
            monitor=monitor,
            win=win,
            canvas=canvas,
            photo=photo,
            screenshot=screenshot,
        )
        self._overlays.append(overlay)

        canvas.bind(
            "<ButtonPress-1>",
            lambda e, o=overlay: self._on_press(o, e),
        )
        canvas.bind(
            "<B1-Motion>",
            lambda e, o=overlay: self._on_drag(o, e),
        )
        canvas.bind(
            "<ButtonRelease-1>",
            lambda e, o=overlay: self._on_release(o, e),
        )

    def _local_to_screen(self, overlay: _MonitorOverlay, x: int, y: int) -> tuple[int, int]:
        mon = overlay.monitor
        return mon["left"] + x, mon["top"] + y

    def _on_press(self, overlay: _MonitorOverlay, event: tk.Event) -> None:
        overlay.start_x = event.x
        overlay.start_y = event.y
        if overlay.rect_id is not None:
            overlay.canvas.delete(overlay.rect_id)
        overlay.rect_id = overlay.canvas.create_rectangle(
            overlay.start_x,
            overlay.start_y,
            overlay.start_x,
            overlay.start_y,
            outline="#00ff88",
            width=3,
        )

    def _on_drag(self, overlay: _MonitorOverlay, event: tk.Event) -> None:
        if overlay.rect_id is not None:
            overlay.canvas.coords(
                overlay.rect_id,
                overlay.start_x,
                overlay.start_y,
                event.x,
                event.y,
            )

    def _on_release(self, overlay: _MonitorOverlay, event: tk.Event) -> None:
        x1, y1 = overlay.start_x, overlay.start_y
        x2, y2 = event.x, event.y
        left_c = min(x1, x2)
        top_c = min(y1, y2)
        width_c = abs(x2 - x1)
        height_c = abs(y2 - y1)

        if width_c < 10 or height_c < 10:
            return

        left, top = self._local_to_screen(overlay, left_c, top_c)
        right, bottom = self._local_to_screen(
            overlay, left_c + width_c, top_c + height_c
        )
        region = Region(left, top, max(1, right - left), max(1, bottom - top))
        self._close_all()
        self.on_selected(region)

    def _cancel(self) -> None:
        self._close_all()

    def _close_all(self) -> None:
        for overlay in self._overlays:
            if overlay.win.winfo_exists():
                overlay.win.destroy()
            overlay.screenshot.close()
        self._overlays.clear()
        if self._restore_main:
            self.root.deiconify()
            self._restore_main = False
