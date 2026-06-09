"""Логика захвата экрана и обнаружения устойчивых изменений."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import mss
from PIL import Image, ImageChops, ImageStat


@dataclass
class Region:
    x: int
    y: int
    width: int
    height: int

    def to_mss_dict(self) -> dict[str, int]:
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }


def images_differ(
    a: Image.Image,
    b: Image.Image,
    threshold: float = 8.0,
) -> bool:
    """True, если изображения заметно отличаются."""
    if a.size != b.size:
        return True
    # Уменьшаем для быстрого сравнения — достаточно для детекции изменений
    small_a = a.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    small_b = b.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    diff = ImageChops.difference(small_a, small_b)
    stat = ImageStat.Stat(diff)
    mean_diff = sum(stat.mean) / len(stat.mean)
    return mean_diff >= threshold


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

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._running = False
        self._change_since: float | None = None
        self._reference: Image.Image | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._change_since = None
        self._reference = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._running = True

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        self._running = False
        self._change_since = None

    def update_delay(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds

    def update_sensitivity(self, sensitivity: float) -> None:
        self.sensitivity = sensitivity

    def reset_baseline(self) -> None:
        self._reference = None
        self._change_since = None

    def _capture(self, sct: mss.mss) -> Image.Image:
        shot = sct.grab(self.region.to_mss_dict())
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def _loop(self) -> None:
        with mss.mss() as sct:
            while not self._stop.is_set():
                try:
                    frame = self._capture(sct)
                except Exception:
                    time.sleep(self.poll_interval)
                    continue

                if self._reference is None:
                    self._reference = frame.copy()
                    if self.on_frame:
                        self.on_frame(frame, False)
                    time.sleep(self.poll_interval)
                    continue

                changed = images_differ(
                    self._reference, frame, threshold=self.sensitivity
                )
                now = time.monotonic()

                if changed:
                    if self._change_since is None:
                        self._change_since = now
                    elif now - self._change_since >= self.delay_seconds:
                        self.on_alarm()
                        self._reference = frame.copy()
                        self._change_since = None
                else:
                    self._change_since = None

                if self.on_frame:
                    self.on_frame(frame, self._change_since is not None)

                time.sleep(self.poll_interval)
