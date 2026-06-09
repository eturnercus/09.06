"""Логика захвата экрана и обнаружения устойчивых изменений."""

from __future__ import annotations

import threading
import time
from typing import Callable

from PIL import Image, ImageChops, ImageStat

from watchalert.region import Region
from watchalert.screen_capture import grab_region


def images_differ(
    a: Image.Image,
    b: Image.Image,
    threshold: float = 8.0,
) -> bool:
    """True, если изображения заметно отличаются."""
    if a.size != b.size:
        return True
    # Уменьшаем для быстрого сравнения — промежуточные кадры сразу освобождаем.
    small_a = a.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    small_b = b.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    try:
        diff = ImageChops.difference(small_a, small_b)
        stat = ImageStat.Stat(diff)
        mean_diff = sum(stat.mean) / len(stat.mean)
        return mean_diff >= threshold
    finally:
        small_a.close()
        small_b.close()
        if "diff" in locals():
            diff.close()


class ChangeTracker:
    """Состояние детектора: один сигнал на каждое новое устойчивое изменение."""

    def __init__(self, delay_seconds: float, sensitivity: float = 8.0) -> None:
        self.delay_seconds = delay_seconds
        self.sensitivity = sensitivity
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
            self._reference, frame, threshold=self.sensitivity
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
        poll_interval: float = 0.4,
        sensitivity: float = 8.0,
    ) -> None:
        self.region = region
        self.delay_seconds = delay_seconds
        self.on_alarm = on_alarm
        self.on_frame = on_frame
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

    def update_sensitivity(self, sensitivity: float) -> None:
        self.sensitivity = sensitivity
        self._tracker.sensitivity = sensitivity

    def reset_baseline(self) -> None:
        self._tracker.reset_baseline()

    def _capture(self) -> Image.Image:
        return grab_region(self.region)

    def _loop(self) -> None:
        errors = 0
        while not self._stop.is_set():
            frame: Image.Image | None = None
            try:
                frame = self._capture()
                now = time.monotonic()
                if self._tracker.process_frame(frame, now):
                    self.on_alarm()
                if self.on_frame:
                    self.on_frame(frame, self._tracker.is_changing)
                errors = 0
            except Exception:
                errors += 1
                time.sleep(min(self.poll_interval * errors, 5.0))
            finally:
                if frame is not None:
                    frame.close()
            time.sleep(self.poll_interval)
