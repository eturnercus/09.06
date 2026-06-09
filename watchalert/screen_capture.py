"""Захват экрана с автовыбором рабочего backend на Linux."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageStat

from watchalert.region import Region

_BLACK_MEAN_THRESHOLD = 4.0
_working_backend: str | None = None

# Переменные AppImage ломают системные gnome-screenshot/scrot (конфликт glib).
_APPIMAGE_ENV_KEYS = (
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "APPIMAGE",
    "APPIMAGE_EXTRACT_AND_RUN",
    "ARGV0",
    "APPDIR",
    "GSETTINGS_SCHEMA_DIR",
    "XDG_DATA_DIRS",
    "QT_PLUGIN_PATH",
    "GTK_PATH",
    "GI_TYPELIB_PATH",
    "PERLLIB",
)


def _session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def is_appimage() -> bool:
    return bool(os.environ.get("APPIMAGE")) or getattr(sys, "frozen", False)


def is_running_as_root() -> bool:
    if os.name != "posix":
        return False
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def _clean_subprocess_env() -> dict[str, str]:
    """Окружение для вызова системных утилит без библиотек AppImage."""
    env = os.environ.copy()
    for key in _APPIMAGE_ENV_KEYS:
        env.pop(key, None)
    return env


def _run_external(cmd: list[str], timeout: float = 15.0) -> None:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        timeout=timeout,
        env=_clean_subprocess_env(),
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(err or f"код {result.returncode}")


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


def _grim_region(region: Region) -> Image.Image:
    grim = shutil.which("grim")
    if not grim:
        raise RuntimeError("grim не установлен")
    geo = f"{region.x},{region.y} {region.width}x{region.height}"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        _run_external([grim, "-g", geo, path])
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def _scrot_region(region: Region) -> Image.Image:
    scrot = shutil.which("scrot")
    if not scrot:
        raise RuntimeError("scrot не установлен")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        _run_external(
            [
                scrot,
                "-a",
                f"{region.x},{region.y},{region.width},{region.height}",
                path,
            ]
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def _gnome_screenshot_region(region: Region) -> Image.Image:
    """Полный экран через gnome-screenshot (чистое окружение), затем обрезка."""
    tool = shutil.which("gnome-screenshot")
    if not tool:
        raise RuntimeError("gnome-screenshot не установлен")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        _run_external([tool, "-f", path])
        full = Image.open(path).convert("RGB")
        try:
            return full.crop(
                (
                    region.x,
                    region.y,
                    region.x + region.width,
                    region.y + region.height,
                )
            )
        finally:
            full.close()
    finally:
        Path(path).unlink(missing_ok=True)


def _capture_with_backend(name: str, region: Region) -> Image.Image:
    box = region.to_mss_dict()
    if name == "mss_xlib":
        return _mss_grab(box, "xlib")
    if name == "mss_default":
        return _mss_grab(box, "default")
    if name == "grim":
        return _grim_region(region)
    if name == "scrot":
        return _scrot_region(region)
    if name == "gnome_screenshot":
        return _gnome_screenshot_region(region)
    if name == "imagegrab":
        # Только по явному WATCHALERT_CAPTURE=imagegrab — внутри зовёт gnome-screenshot
        # с испорченным LD_LIBRARY_PATH из AppImage.
        from PIL import ImageGrab

        bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
        return ImageGrab.grab(bbox=bbox).convert("RGB")
    if name == "mss":
        return _mss_grab(box, "default")
    raise ValueError(name)


def _linux_backends() -> list[str]:
    forced = os.environ.get("WATCHALERT_CAPTURE", "").strip().lower()
    if forced:
        return [forced]

    order: list[str] = []

    if _session_type() == "wayland":
        if shutil.which("grim"):
            order.append("grim")
        if shutil.which("gnome-screenshot"):
            order.append("gnome_screenshot")
        order.extend(["mss_xlib", "mss_default"])
        if shutil.which("scrot"):
            order.append("scrot")
    else:
        order.extend(["mss_xlib", "mss_default"])
        if shutil.which("scrot"):
            order.append("scrot")
        if shutil.which("grim"):
            order.append("grim")
        if shutil.which("gnome-screenshot"):
            order.append("gnome_screenshot")

    # imagegrab намеренно не в списке по умолчанию (ломается в AppImage).
    return order


def _all_backends() -> list[str]:
    if platform.system() == "Linux":
        return _linux_backends()
    return ["mss_default"]


def grab_region(region: Region) -> Image.Image:
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
    if is_running_as_root():
        return "Не запускайте через sudo — запустите от своего пользователя: ./WatchAlert.AppImage"
    session = _session_type() or "неизвестна"
    if session == "wayland":
        return (
            "Wayland: sudo apt install grim. "
            "Или войдите в сессию Ubuntu on Xorg. Не используйте sudo."
        )
    return "X11: sudo apt install scrot. Не используйте sudo для запуска приложения."


def list_monitors() -> list[dict[str, int]]:
    for backend in ("xlib", "default"):
        try:
            from mss import MSS

            with MSS(backend=backend) as sct:
                mons = [dict(m) for m in sct.monitors[1:]]
                if mons:
                    return mons
        except Exception:
            continue

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
    global _working_backend
    _working_backend = None
