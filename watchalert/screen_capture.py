"""Захват экрана: mss с запасным вариантом через ImageGrab."""

from __future__ import annotations

from typing import Any

from PIL import Image

from watchalert.region import Region


def virtual_monitor() -> dict[str, int]:
    """Виртуальный экран (все мониторы) в координатах mss."""
    import mss

    with mss.mss() as sct:
        return dict(sct.monitors[0])


def grab_virtual_screen() -> tuple[Image.Image, dict[str, int]]:
    """Снимок всего экрана и границы виртуального монитора."""
    import mss

    with mss.mss() as sct:
        mon = sct.monitors[0]
        shot = sct.grab(mon)
        image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        return image, dict(mon)


def grab_region(region: Region) -> Image.Image:
    """Захват прямоугольной области экрана."""
    try:
        import mss

        with mss.mss() as sct:
            shot = sct.grab(region.to_mss_dict())
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    except Exception:
        from PIL import ImageGrab

        bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
        img = ImageGrab.grab(bbox=bbox)
        return img.convert("RGB")
