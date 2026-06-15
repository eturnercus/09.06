"""Захват экрана: автоподбор рабочего способа на Linux/Windows."""

from __future__ import annotations

import platform
import threading

from PIL import Image, ImageStat

from watchalert.capture_backends import BACKEND_FUNCS, backend_candidates
from watchalert.capture_env import is_running_as_root, session_type
from watchalert.region import Region

_BLACK_MEAN_THRESHOLD = 4.0

_working_backends: list[str] = []
_active_backend: str | None = None
_probe_errors: list[str] = []
_probe_lock = threading.Lock()
_probe_done = False


def _image_mean_brightness(image: Image.Image) -> float:
    stat = ImageStat.Stat(image.convert("L"))
    return sum(stat.mean) / len(stat.mean)


def is_black_frame(image: Image.Image) -> bool:
    return _image_mean_brightness(image) < _BLACK_MEAN_THRESHOLD


def _try_backend(name: str, region: Region) -> Image.Image | None:
    func = BACKEND_FUNCS.get(name)
    if not func:
        return None
    image = func(region)
    if is_black_frame(image):
        image.close()
        raise RuntimeError("чёрный кадр")
    return image


def probe_backends(test_region: Region | None = None) -> tuple[list[str], list[str]]:
    """
    Проверяет все доступные способы захвата.
    Возвращает (рабочие, ошибки).
    """
    global _working_backends, _active_backend, _probe_errors, _probe_done

    if test_region is None:
        mons = list_monitors()
        m = mons[0]
        w = min(80, m["width"] // 4)
        h = min(80, m["height"] // 4)
        test_region = Region(m["left"] + 10, m["top"] + 10, max(w, 20), max(h, 20))

    working: list[str] = []
    errors: list[str] = []

    for name in backend_candidates():
        try:
            image = _try_backend(name, test_region)
            if image is not None:
                image.close()
                working.append(name)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    with _probe_lock:
        _working_backends = working
        _active_backend = working[0] if working else None
        _probe_errors = errors
        _probe_done = True

    return working, errors


def ensure_probed() -> None:
    with _probe_lock:
        done = _probe_done
    if not done:
        probe_backends()


def probe_async(callback: object | None = None) -> None:
    def _run() -> None:
        working, errors = probe_backends()
        if callback:
            callback(working, errors)

    threading.Thread(target=_run, daemon=True).start()


def active_backend_name() -> str | None:
    with _probe_lock:
        return _active_backend


def working_backends() -> list[str]:
    with _probe_lock:
        return list(_working_backends)


def probe_error_summary() -> str:
    with _probe_lock:
        return "; ".join(_probe_errors[:5])


def recommended_poll_interval() -> float:
    name = active_backend_name() or ""
    if name in ("portal", "gnome_screenshot", "spectacle"):
        return 2.0
    if name in ("ffmpeg", "import"):
        return 1.0
    return 0.4


def grab_region(region: Region) -> Image.Image:
    global _active_backend

    ensure_probed()

    with _probe_lock:
        backends = list(_working_backends) if _working_backends else backend_candidates()
        preferred = _active_backend

    if preferred and preferred in backends:
        order = [preferred] + [b for b in backends if b != preferred]
    else:
        order = backends

    errors: list[str] = []
    for name in order:
        try:
            image = _try_backend(name, region)
            if image is not None:
                with _probe_lock:
                    _active_backend = name
                return image
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    hint = capture_help_text()
    detail = "; ".join(errors[:5]) or probe_error_summary()
    raise RuntimeError(f"Захват не удался ({detail}). {hint}")


def capture_help_text() -> str:
    if is_running_as_root():
        return "Не используйте sudo. Запуск: ./WatchAlert.AppImage"

    if platform.system() != "Linux":
        return ""

    if session_type() == "wayland":
        return (
            "Wayland: нужен xdg-desktop-portal (обычно уже есть). "
            "Дополнительно: sudo apt install grim slop. "
            "Или войдите в сессию «Ubuntu on Xorg». Без sudo."
        )
    return (
        "X11: sudo apt install scrot imagemagick. "
        "Или WATCHALERT_CAPTURE=pillow_x11. Без sudo."
    )


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
        import re
        import subprocess

        from watchalert.capture_env import clean_subprocess_env

        out = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=5,
            env=clean_subprocess_env(),
        )
        mons: list[dict[str, int]] = []
        for line in out.stdout.splitlines():
            if " connected" not in line:
                continue
            match = re.search(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", line)
            if match:
                w, h, x, y = match.groups()
                mons.append(
                    {
                        "left": int(x),
                        "top": int(y),
                        "width": int(w),
                        "height": int(h),
                    }
                )
        if mons:
            return mons
    except Exception:
        pass

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


def reset_capture_backend() -> None:
    global _working_backends, _active_backend, _probe_errors, _probe_done
    with _probe_lock:
        _working_backends = []
        _active_backend = None
        _probe_errors = []
        _probe_done = False


# Совместимость
linux_capture_help = capture_help_text
is_appimage = __import__(
    "watchalert.capture_env", fromlist=["is_appimage"]
).is_appimage
