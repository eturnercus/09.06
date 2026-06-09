"""Захват экрана с автовыбором рабочего backend на Linux."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageStat

from watchalert.region import Region

# Средняя яркость ниже порога = «чёрный» кадр (типичный сбой mss на Linux).
_BLACK_MEAN_THRESHOLD = 4.0

# Кэш: какой способ захвата сработал в этой сессии.
_working_backend: str | None = None


def _session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def _image_mean_brightness(image: Image.Image) -> float:
    stat = ImageStat.Stat(image.convert("L"))
    return sum(stat.mean) / len(stat.mean)


def _is_black_frame(image: Image.Image) -> bool:
    return _image_mean_brightness(image) < _BLACK_MEAN_THRESHOLD


def _mss_grab(box: dict[str, int], backend: str) -> Image.Image:
    from mss import MSS

    with MSS(backend=backend) as sct:
        shot = sct.grab(box)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _imagegrab_region(region: Region) -> Image.Image:
    from PIL import ImageGrab

    bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
    return ImageGrab.grab(bbox=bbox).convert("RGB")


def _grim_region(region: Region) -> Image.Image:
    if not shutil.which("grim"):
        raise RuntimeError("grim не установлен")
    geo = f"{region.x},{region.y} {region.width}x{region.height}"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        subprocess.run(
            ["grim", "-g", geo, path],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def _scrot_region(region: Region) -> Image.Image:
    if not shutil.which("scrot"):
        raise RuntimeError("scrot не установлен")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        subprocess.run(
            [
                "scrot",
                "-a",
                f"{region.x},{region.y},{region.width},{region.height}",
                path,
            ],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def _capture_with_backend(name: str, region: Region) -> Image.Image:
    box = region.to_mss_dict()
    if name == "mss_xlib":
        return _mss_grab(box, "xlib")
    if name == "mss_default":
        return _mss_grab(box, "default")
    if name == "imagegrab":
        return _imagegrab_region(region)
    if name == "grim":
        return _grim_region(region)
    if name == "scrot":
        return _scrot_region(region)
    if name == "mss":
        return _mss_grab(box, "default")
    raise ValueError(name)


def _linux_backends() -> list[str]:
    order: list[str] = []
    forced = os.environ.get("WATCHALERT_CAPTURE", "").strip().lower()
    if forced:
        return [forced]

    if _session_type() == "wayland":
        if shutil.which("grim"):
            order.append("grim")
        order.extend(["imagegrab", "scrot", "mss_xlib", "mss_default"])
    else:
        # X11: xlib и ImageGrab чаще работают, чем xcb-бекенд mss по умолчанию.
        order.extend(["mss_xlib", "imagegrab", "scrot", "mss_default"])
        if shutil.which("grim"):
            order.append("grim")
    return order


def _all_backends() -> list[str]:
    if platform.system() == "Linux":
        return _linux_backends()
    return ["mss_default", "imagegrab"]


def grab_region(region: Region) -> Image.Image:
    """Захват области; перебирает backend'ы, отбрасывает чёрные кадры."""
    global _working_backend

    backends = _all_backends()
    if _working_backend and _working_backend in backends:
        backends = [_working_backend] + [b for b in backends if b != _working_backend]

    errors: list[str] = []
    for name in backends:
        try:
            image = _capture_with_backend(name, region)
            if _is_black_frame(image):
                errors.append(f"{name}: чёрный кадр")
                image.close()
                continue
            _working_backend = name
            return image
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    hint = linux_capture_help()
    detail = "; ".join(errors[:4])
    raise RuntimeError(f"Захват экрана не удался ({detail}). {hint}")


def linux_capture_help() -> str:
    session = _session_type() or "неизвестна"
    if session == "wayland":
        return (
            "Wayland: установите grim (wlroots/Hyprland/Sway) или запустите сессию X11. "
            "На GNOME: sudo apt install grim или используйте Xorg при входе."
        )
    return (
        "X11: sudo apt install scrot imagemagick или задайте WATCHALERT_CAPTURE=mss_xlib|imagegrab."
    )


def list_monitors() -> list[dict[str, int]]:
    """Физические мониторы."""
    for backend in ("xlib", "default"):
        try:
            from mss import MSS

            with MSS(backend=backend) as sct:
                mons = [dict(m) for m in sct.monitors[1:]]
                if mons:
                    return mons
        except Exception:
            continue

    # Запасной вариант: один монитор по размеру из tk (после import в selector).
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return [{"left": 0, "top": 0, "width": w, "height": h}]
    except Exception:
        return [{"left": 0, "top": 0, "width": 1920, "height": 1080}]


def grab_monitor(monitor: dict[str, int]) -> Image.Image:
    region = Region(
        monitor["left"],
        monitor["top"],
        monitor["width"],
        monitor["height"],
    )
    return grab_region(region)


def virtual_monitor() -> dict[str, int]:
    for backend in ("xlib", "default"):
        try:
            from mss import MSS

            with MSS(backend=backend) as sct:
                return dict(sct.monitors[0])
        except Exception:
            continue
    mons = list_monitors()
    if not mons:
        return {"left": 0, "top": 0, "width": 1920, "height": 1080}
    if len(mons) == 1:
        return mons[0]
    left = min(m["left"] for m in mons)
    top = min(m["top"] for m in mons)
    right = max(m["left"] + m["width"] for m in mons)
    bottom = max(m["top"] + m["height"] for m in mons)
    return {"left": left, "top": top, "width": right - left, "height": bottom - top}


def grab_virtual_screen() -> tuple[Image.Image, dict[str, int]]:
    mon = virtual_monitor()
    region = Region(mon["left"], mon["top"], mon["width"], mon["height"])
    return grab_region(region), mon


def reset_capture_backend() -> None:
    """Сброс кэша (для тестов)."""
    global _working_backend
    _working_backend = None
