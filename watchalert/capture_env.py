"""Окружение для захвата экрана (AppImage, subprocess)."""

from __future__ import annotations

import os
import subprocess
import sys

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


def session_type() -> str:
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


def clean_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _APPIMAGE_ENV_KEYS:
        env.pop(key, None)
    return env


def run_external(cmd: list[str], timeout: float = 20.0) -> None:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        timeout=timeout,
        env=clean_subprocess_env(),
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(err or f"код {result.returncode}")
