"""Логика захвата экрана и обнаружения устойчивых изменений."""

from __future__ import annotations

import threading
import time
from typing import Callable

from PIL import Image, ImageChops

from watchalert.brand import verify_brand
from watchalert.region import Region
from watchalert.screen_capture import grab_region, recommended_poll_interval
from watchalert.sensitivity import get_sensitivity_config, normalize_sensitivity


def _image_diff_stats(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    small_a = a.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    small_b = b.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    try:
        diff = ImageChops.difference(small_a, small_b)
        pixels = list(diff.getdata())
        if not pixels:
            return 0.0, 0.0
        diff_sum = 0.0
        changed = 0
        pixel_threshold = 18.0
        for r, g, b in pixels:
            d = (r + g + b) / 3.0
            diff_sum += d
            if d >= pixel_threshold:
                changed += 1
        count = len(pixels)
        return diff_sum / count, changed / count
    finally:
        small_a.close()
        small_b.close()
        if "diff" in locals():
            diff.close()


def images_differ(
    a: Image.Image,
    b: Image.Image,
    sensitivity: str | float = "medium",
) -> bool:
    """True, если изображения заметно отличаются."""
    if a.size != b.size:
        return True
    cfg = get_sensitivity_config(sensitivity)
    mean_diff, changed_ratio = _image_diff_stats(a, b)
    if mean_diff < cfg["threshold"]:
        return False
    if cfg["min_changed_ratio"] <= 0:
        return True
    return changed_ratio >= cfg["min_changed_ratio"]


class ChangeTracker:
    """Состояние детектора: один сигнал на каждое новое устойчивое изменение."""

    def __init__(self, delay_seconds: float, sensitivity: str | float = "medium") -> None:
        self.delay_seconds = delay_seconds
        self.sensitivity = normalize_sensitivity(sensitivity)
        self._reference: Image.Image | None = None
        self._change_since: float | None = None

    def process_frame(self, frame: Image.Image, now: float) -> bool:
        """
        Обрабатывает кадр. Возвращает True, если нужно воспроизвести сигнал.

        - Первый кадр запоминается как эталон, сигнала нет.
        - При отличии от эталона запускается таймер.
        - Если отличие исчезает до истечения задержки — таймер сбрасывается.
        - После сигнала эталон обновляется: без нового изменения повтора нет.
        - Новое изменение относительно обновлённого эталона снова даёт сигнал.
        """
        if self._reference is None:
            self._reference = frame.copy()
            self._change_since = None
            return False

        # Старый кадр заменяется — на диск ничего не пишется, память освобождается GC.

        changed = images_differ(
            self._reference, frame, sensitivity=self.sensitivity
        )

        if changed:
            if self._change_since is None:
                self._change_since = now
            elif now - self._change_since >= self.delay_seconds:
                self._reference.close()
                self._reference = frame.copy()
                self._change_since = None
                return True
        else:
            self._change_since = None

        return False

    @property
    def is_changing(self) -> bool:
        return self._change_since is not None

    def reset_baseline(self) -> None:
        if self._reference is not None:
            self._reference.close()
        self._reference = None
        self._change_since = None


class RegionMonitor:
    """Фоновый монитор одной области экрана."""

    def __init__(
        self,
        region: Region,
        delay_seconds: float,
        on_alarm: Callable[[], None],
        on_frame: Callable[[Image.Image, bool], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        poll_interval: float = 0.4,
        sensitivity: str | float = "medium",
    ) -> None:
        self.region = region
        self.delay_seconds = delay_seconds
        self.on_alarm = on_alarm
        self.on_frame = on_frame
        self.on_error = on_error
        self.poll_interval = poll_interval
        self.sensitivity = sensitivity
        self._tracker = ChangeTracker(delay_seconds, sensitivity)

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._tracker.reset_baseline()
        self.poll_interval = recommended_poll_interval()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._running = True

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        self._running = False

    def update_delay(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds
        self._tracker.delay_seconds = delay_seconds

    def update_sensitivity(self, sensitivity: str | float) -> None:
        self.sensitivity = normalize_sensitivity(sensitivity)
        self._tracker.sensitivity = self.sensitivity

    def reset_baseline(self) -> None:
        self._tracker.reset_baseline()

    def _capture(self) -> Image.Image:
        return grab_region(self.region)

    def _loop(self) -> None:
        errors = 0
        while not self._stop.is_set():
            verify_brand()
            frame: Image.Image | None = None
            try:
                frame = self._capture()
                now = time.monotonic()
                if self._tracker.process_frame(frame, now):
                    self.on_alarm()
                if self.on_frame:
                    self.on_frame(frame, self._tracker.is_changing)
                errors = 0
            except Exception as exc:
                errors += 1
                if self.on_error:
                    self.on_error(str(exc))
                time.sleep(min(self.poll_interval * errors, 5.0))
            finally:
                if frame is not None:
                    frame.close()
            time.sleep(self.poll_interval)
