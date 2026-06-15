"""Все способы захвата экрана на Linux и Windows."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PIL import Image

from watchalert.capture_env import clean_subprocess_env, run_external, session_type
from watchalert.capture_portal import portal_available, portal_screenshot_path
from watchalert.region import Region


def _crop(image: Image.Image, region: Region) -> Image.Image:
    return image.crop(
        (region.x, region.y, region.x + region.width, region.y + region.height)
    )


def _mss_grab(box: dict[str, int], backend: str) -> Image.Image:
    from mss import MSS

    with MSS(backend=backend) as sct:
        shot = sct.grab(box)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_portal(region: Region) -> Image.Image:
    path = portal_screenshot_path()
    try:
        full = Image.open(path).convert("RGB")
        try:
            return _crop(full, region)
        finally:
            full.close()
    finally:
        path.unlink(missing_ok=True)


def capture_pillow_x11(region: Region) -> Image.Image:
    from PIL import Image as PILImage

    if not PILImage.core.HAVE_XCB:
        raise RuntimeError("Pillow без XCB")
    size, data = PILImage.core.grabscreen_x11(None)
    full = PILImage.frombytes("RGB", size, data, "raw", "BGRX", size[0] * 4, 1)
    try:
        return _crop(full, region)
    finally:
        full.close()


def capture_mss_xlib(region: Region) -> Image.Image:
    return _mss_grab(region.to_mss_dict(), "xlib")


def capture_mss_default(region: Region) -> Image.Image:
    return _mss_grab(region.to_mss_dict(), "default")


def capture_grim(region: Region) -> Image.Image:
    grim = shutil.which("grim")
    if not grim:
        raise RuntimeError("grim не найден")
    geo = f"{region.x},{region.y} {region.width}x{region.height}"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external([grim, "-g", geo, path])
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def capture_scrot(region: Region) -> Image.Image:
    scrot = shutil.which("scrot")
    if not scrot:
        raise RuntimeError("scrot не найден")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external(
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


def capture_maim(region: Region) -> Image.Image:
    maim = shutil.which("maim")
    if not maim:
        raise RuntimeError("maim не найден")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external(
            [
                maim,
                "-g",
                f"{region.width}x{region.height}+{region.x}+{region.y}",
                path,
            ]
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def capture_gnome_screenshot(region: Region) -> Image.Image:
    tool = shutil.which("gnome-screenshot")
    if not tool:
        raise RuntimeError("gnome-screenshot не найден")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external([tool, "-f", path])
        full = Image.open(path).convert("RGB")
        try:
            return _crop(full, region)
        finally:
            full.close()
    finally:
        Path(path).unlink(missing_ok=True)


def capture_spectacle(region: Region) -> Image.Image:
    tool = shutil.which("spectacle")
    if not tool:
        raise RuntimeError("spectacle не найден")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external([tool, "-n", "-b", "-f", "-o", path])
        full = Image.open(path).convert("RGB")
        try:
            return _crop(full, region)
        finally:
            full.close()
    finally:
        Path(path).unlink(missing_ok=True)


def capture_import(region: Region) -> Image.Image:
    tool = shutil.which("import")
    if not tool:
        raise RuntimeError("imagemagick import не найден")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        display = clean_subprocess_env().get("DISPLAY", ":0")
        run_external(
            [
                tool,
                "-display",
                display,
                "-window",
                "root",
                "-crop",
                f"{region.width}x{region.height}+{region.x}+{region.y}",
                path,
            ]
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


def capture_ffmpeg(region: Region) -> Image.Image:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg не найден")
    display = clean_subprocess_env().get("DISPLAY", ":0")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        run_external(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "x11grab",
                "-video_size",
                f"{region.width}x{region.height}",
                "-i",
                f"{display}+{region.x},{region.y}",
                "-frames:v",
                "1",
                "-y",
                path,
            ],
            timeout=30.0,
        )
        return Image.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)


# Имя -> функция
BACKEND_FUNCS: dict[str, object] = {
    "portal": capture_portal,
    "pillow_x11": capture_pillow_x11,
    "mss_xlib": capture_mss_xlib,
    "mss_default": capture_mss_default,
    "grim": capture_grim,
    "scrot": capture_scrot,
    "maim": capture_maim,
    "gnome_screenshot": capture_gnome_screenshot,
    "spectacle": capture_spectacle,
    "import": capture_import,
    "ffmpeg": capture_ffmpeg,
}


def backend_candidates() -> list[str]:
    """Порядок перебора с учётом типа сессии."""
    forced = __import__("os").environ.get("WATCHALERT_CAPTURE", "").strip().lower()
    if forced:
        return [forced]

    wayland = session_type() == "wayland"
    order: list[str] = []

    if wayland:
        if portal_available():
            order.append("portal")
        if shutil.which("grim"):
            order.append("grim")
        if shutil.which("spectacle"):
            order.append("spectacle")
        if shutil.which("gnome-screenshot"):
            order.append("gnome_screenshot")
        order.extend(["pillow_x11", "mss_xlib", "mss_default"])
    else:
        order.extend(
            [
                "pillow_x11",
                "mss_xlib",
                "mss_default",
                "scrot",
                "maim",
                "import",
                "ffmpeg",
            ]
        )
        if portal_available():
            order.append("portal")
        if shutil.which("grim"):
            order.append("grim")
        if shutil.which("gnome-screenshot"):
            order.append("gnome_screenshot")
        if shutil.which("spectacle"):
            order.append("spectacle")

    # Уникальный порядок
    seen: set[str] = set()
    unique: list[str] = []
    for name in order:
        if name not in seen and name in BACKEND_FUNCS:
            seen.add(name)
            unique.append(name)
    return unique
