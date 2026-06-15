"""Главное окно приложения WatchAlert."""

from __future__ import annotations

import json
import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from watchalert.audio import SoundPlayer
from watchalert.monitor import RegionMonitor
from watchalert.region import Region
from watchalert.capture_env import session_type
from watchalert.screen_capture import (
    active_backend_name,
    capture_help_text,
    grab_region,
    probe_async,
    probe_backends,
    reset_capture_backend,
)
from watchalert.selector import RegionSelector

CONFIG_DIR = Path.home() / ".watchalert"
CONFIG_FILE = CONFIG_DIR / "config.json"


class PreviewWindow:
    """Небольшое окно с живым превью отслеживаемой области."""

    def __init__(self, master: tk.Tk, index: int, region: Region) -> None:
        self.index = index
        self.region = region
        self.win = tk.Toplevel(master)
        self.win.title(f"Область #{index + 1}")
        self.win.geometry("240x200")
        self.win.minsize(160, 120)

        self.status_var = tk.StringVar(value="Ожидание…")
        ttk.Label(self.win, textvariable=self.status_var).pack(
            side=tk.BOTTOM, fill=tk.X, padx=6, pady=4
        )

        self.label = ttk.Label(self.win)
        self.label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._photo: ImageTk.PhotoImage | None = None

    def update_frame(self, image: Image.Image, changing: bool) -> None:
        preview = image.copy()
        try:
            preview.thumbnail((320, 240), Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(preview)
            self.label.configure(image=self._photo)
        finally:
            preview.close()
        if changing:
            self.status_var.set("Изменение…")
            self.win.configure(bg="#3d1f1f")
        else:
            self.status_var.set("Стабильно")
            self.win.configure(bg="")

    def show_error(self, message: str) -> None:
        self._photo = None
        self.label.configure(image="")
        short = message if len(message) < 120 else message[:117] + "…"
        self.status_var.set(f"Ошибка захвата: {short}")
        self.win.configure(bg="#3d1f1f")

    def close(self) -> None:
        if self.win.winfo_exists():
            self.win.destroy()


class MonitorSlot:
    def __init__(
        self,
        app: "WatchAlertApp",
        index: int,
        region: Region,
        running: bool = False,
    ) -> None:
        self.app = app
        self.index = index
        self.region = region
        self.preview = PreviewWindow(app.root, index, region)
        self.monitor = RegionMonitor(
            region=region,
            delay_seconds=app.delay_var.get(),
            on_alarm=app._play_alarm,
            on_frame=self._on_frame,
            on_error=self._on_error,
            sensitivity=app.sensitivity_var.get(),
        )
        self.list_item_id: str | None = None
        self._pending_image: Image.Image | None = None
        self._pending_changing = False
        self._preview_scheduled = False
        if running:
            self.start()

    def _on_error(self, message: str) -> None:
        self.app.root.after(0, lambda: self._show_error_safe(message))

    def _show_error_safe(self, message: str) -> None:
        if self.preview.win.winfo_exists():
            self.preview.show_error(message)

    def _on_frame(self, image: Image.Image, changing: bool) -> None:
        # Сливаем частые кадры: в очереди tk всегда только последний кадр.
        if self._pending_image is not None:
            self._pending_image.close()
        self._pending_image = image.copy()
        self._pending_changing = changing
        if not self._preview_scheduled:
            self._preview_scheduled = True
            self.app.root.after(0, self._flush_preview)

    def _flush_preview(self) -> None:
        self._preview_scheduled = False
        image = self._pending_image
        changing = self._pending_changing
        self._pending_image = None
        if image is None:
            return
        try:
            if self.preview.win.winfo_exists():
                self.preview.update_frame(image, changing)
        finally:
            image.close()

    def start(self) -> None:
        self.monitor.start()

    def stop(self) -> None:
        self.monitor.stop()

    def destroy(self) -> None:
        self.monitor.stop()
        if self._pending_image is not None:
            self._pending_image.close()
            self._pending_image = None
        self.preview.close()


class WatchAlertApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("WatchAlert — мониторинг областей экрана")
        self.root.minsize(520, 420)
        self.root.geometry("620x480")

        self.sound_player = SoundPlayer()
        self.slots: list[MonitorSlot] = []
        self.selector = RegionSelector(self.root, self._on_region_selected)
        self._monitoring = False

        self.delay_var = tk.DoubleVar(value=5.0)
        self.sensitivity_var = tk.DoubleVar(value=8.0)
        self.sound_path_var = tk.StringVar(value="")

        self.capture_status_var = tk.StringVar(value="Захват экрана: проверка…")

        self._build_ui()
        self._load_config()
        self._refresh_capture_status()
        self.root.after(300, self._start_capture_probe)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_capture_probe(self) -> None:
        probe_async(
            lambda _w, _e: self.root.after(0, self._refresh_capture_status)
        )

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        settings = ttk.LabelFrame(main, text="Настройки", padding=10)
        settings.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(settings)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Задержка перед сигналом (сек):").pack(side=tk.LEFT)
        delay_spin = ttk.Spinbox(
            row1,
            from_=1,
            to=3600,
            increment=1,
            textvariable=self.delay_var,
            width=8,
        )
        delay_spin.pack(side=tk.LEFT, padx=(8, 0))
        delay_spin.bind("<FocusOut>", lambda _e: self._apply_settings())
        delay_spin.bind("<Return>", lambda _e: self._apply_settings())

        row2 = ttk.Frame(settings)
        row2.pack(fill=tk.X, pady=6)
        ttk.Label(row2, text="Чувствительность:").pack(side=tk.LEFT)
        sens_spin = ttk.Spinbox(
            row2,
            from_=1,
            to=50,
            increment=1,
            textvariable=self.sensitivity_var,
            width=8,
        )
        sens_spin.pack(side=tk.LEFT, padx=(8, 0))
        sens_spin.bind("<FocusOut>", lambda _e: self._apply_settings())
        sens_spin.bind("<Return>", lambda _e: self._apply_settings())
        ttk.Label(
            row2,
            text="(меньше — чувствительнее)",
            foreground="#666",
        ).pack(side=tk.LEFT, padx=(8, 0))

        row3 = ttk.Frame(settings)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Звуковой файл:").pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.sound_path_var, width=42).pack(
            side=tk.LEFT, padx=(8, 4), fill=tk.X, expand=True
        )
        ttk.Button(row3, text="Обзор…", command=self._browse_sound).pack(
            side=tk.LEFT
        )
        ttk.Button(row3, text="Тест", command=self._test_sound).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        row4 = ttk.Frame(settings)
        row4.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(
            row4, textvariable=self.capture_status_var, wraplength=540
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row4, text="Проверить захват", command=self._test_capture).pack(
            side=tk.RIGHT
        )

        regions_frame = ttk.LabelFrame(main, text="Области мониторинга", padding=10)
        regions_frame.pack(fill=tk.BOTH, expand=True)

        list_wrap = ttk.Frame(regions_frame)
        list_wrap.pack(fill=tk.BOTH, expand=True)

        self.region_list = tk.Listbox(list_wrap, height=8)
        self.region_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(
            list_wrap, orient=tk.VERTICAL, command=self.region_list.yview
        )
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.region_list.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(regions_frame)
        buttons.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            buttons, text="Добавить область", command=self.selector.open
        ).pack(side=tk.LEFT)
        ttk.Button(
            buttons, text="Удалить выбранную", command=self._remove_selected
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            buttons, text="Сбросить базу", command=self._reset_baseline
        ).pack(side=tk.LEFT, padx=(6, 0))

        self.start_btn = ttk.Button(
            buttons, text="▶ Старт", command=self._toggle_monitoring
        )
        self.start_btn.pack(side=tk.RIGHT)

        footer = ttk.Label(
            main,
            text="Выделите область экрана → запустите мониторинг. "
            "Если изменение сохраняется заданное время — прозвучит сигнал.",
            wraplength=580,
            foreground="#444",
        )
        footer.pack(fill=tk.X, pady=(10, 0))

    def _browse_sound(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите звуковой файл",
            filetypes=[
                ("Аудио", "*.wav *.mp3 *.ogg *.flac"),
                ("Все файлы", "*.*"),
            ],
        )
        if path:
            self.sound_path_var.set(path)
            self.sound_player.set_sound(path)
            self._save_config()

    def _test_sound(self) -> None:
        self.sound_player.set_sound(self.sound_path_var.get() or None)
        self._play_alarm()

    def _refresh_capture_status(self) -> None:
        backend = active_backend_name()
        session = session_type() or "?"
        if backend:
            self.capture_status_var.set(
                f"Захват экрана: {backend} ({session}) — OK"
            )
        else:
            self.capture_status_var.set(
                f"Захват экрана: не найден ({session}). Нажмите «Проверить захват»."
            )

    def _test_capture(self) -> None:
        reset_capture_backend()
        working, errors = probe_backends()
        self._refresh_capture_status()
        if working:
            mons = __import__(
                "watchalert.screen_capture", fromlist=["list_monitors"]
            ).list_monitors()
            m = mons[0]
            region = Region(
                m["left"] + 10,
                m["top"] + 10,
                min(120, m["width"] // 3),
                min(90, m["height"] // 3),
            )
            try:
                img = grab_region(region)
                img.close()
            except Exception as exc:
                messagebox.showerror("WatchAlert", f"Тест не прошёл: {exc}")
                return
            messagebox.showinfo(
                "WatchAlert",
                f"Захват работает.\n\nСпособ: {working[0]}\n"
                f"Доступно: {', '.join(working)}\n\n"
                f"Сессия: {session_type() or 'неизвестна'}",
            )
        else:
            messagebox.showerror(
                "WatchAlert",
                "Не удалось захватить экран ни одним способом.\n\n"
                + "\n".join(errors[:6])
                + "\n\n"
                + capture_help_text(),
            )

    def _play_alarm(self) -> None:
        self.sound_player.set_sound(self.sound_path_var.get() or None)
        self.sound_player.play()
        self.root.after(0, self._flash_alarm)

    def _flash_alarm(self) -> None:
        original = self.root.title()
        self.root.title("⚠ WatchAlert — СИГНАЛ!")
        self.root.after(1500, lambda: self.root.title(original))

    def _apply_settings(self) -> None:
        delay = max(1.0, float(self.delay_var.get()))
        sens = max(1.0, float(self.sensitivity_var.get()))
        self.delay_var.set(delay)
        self.sensitivity_var.set(sens)
        for slot in self.slots:
            slot.monitor.update_delay(delay)
            slot.monitor.update_sensitivity(sens)
        self._save_config()

    def _on_region_selected(self, region: Region) -> None:
        index = len(self.slots)
        slot = MonitorSlot(self, index, region, running=self._monitoring)
        self.slots.append(slot)
        label = (
            f"#{index + 1}: x={region.x}, y={region.y}, "
            f"{region.width}×{region.height}"
        )
        self.region_list.insert(tk.END, label)
        self._save_config()

    def _remove_selected(self) -> None:
        selection = self.region_list.curselection()
        if not selection:
            messagebox.showinfo("WatchAlert", "Выберите область в списке.")
            return
        idx = selection[0]
        self.slots[idx].destroy()
        del self.slots[idx]
        self.region_list.delete(idx)
        self._reindex_slots()
        self._save_config()

    def _reindex_slots(self) -> None:
        self.region_list.delete(0, tk.END)
        for i, slot in enumerate(self.slots):
            slot.index = i
            slot.preview.index = i
            slot.preview.win.title(f"Область #{i + 1}")
            r = slot.region
            self.region_list.insert(
                tk.END,
                f"#{i + 1}: x={r.x}, y={r.y}, {r.width}×{r.height}",
            )

    def _reset_baseline(self) -> None:
        for slot in self.slots:
            slot.monitor.reset_baseline()

    def _toggle_monitoring(self) -> None:
        if self._monitoring:
            self._stop_monitoring()
        else:
            if not self.slots:
                messagebox.showinfo(
                    "WatchAlert", "Сначала добавьте хотя бы одну область."
                )
                return
            if not self.sound_path_var.get().strip():
                if not messagebox.askyesno(
                    "WatchAlert",
                    "Звуковой файл не выбран. Продолжить без звука?",
                ):
                    return
            self._apply_settings()
            self._start_monitoring()

    def _start_monitoring(self) -> None:
        self._monitoring = True
        for slot in self.slots:
            slot.start()
        self.start_btn.configure(text="■ Стоп")

    def _stop_monitoring(self) -> None:
        self._monitoring = False
        for slot in self.slots:
            slot.stop()
        self.start_btn.configure(text="▶ Старт")

    def _save_config(self) -> None:
        data: dict[str, Any] = {
            "delay_seconds": self.delay_var.get(),
            "sensitivity": self.sensitivity_var.get(),
            "sound_path": self.sound_path_var.get(),
            "regions": [asdict(s.region) for s in self.slots],
        }
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def _load_config(self) -> None:
        if not CONFIG_FILE.is_file():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self.delay_var.set(data.get("delay_seconds", 5.0))
        self.sensitivity_var.set(data.get("sensitivity", 8.0))
        sound = data.get("sound_path", "")
        if sound:
            self.sound_path_var.set(sound)
            self.sound_player.set_sound(sound)

        for region_data in data.get("regions", []):
            region = Region(**region_data)
            self._on_region_selected(region)

    def _on_close(self) -> None:
        self._stop_monitoring()
        for slot in self.slots:
            slot.destroy()
        self._save_config()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
